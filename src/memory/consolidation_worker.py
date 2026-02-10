import json
import logging
import re
import time
from datetime import datetime
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.dependencies import get_sqlite_store
from src.core.engine import llm
from src.core.profile_manager import user_profile_manager
from src.memory.ingestion_pipeline import IngestionPipeline

logger = logging.getLogger(__name__)


class ConsolidationManager:
    """
    Gestiona la consolidación de memoria: Buffer -> Resumen -> Perfil -> Nube.
    Trigger: N >= 20 mensajes O > 6 horas de inactividad.
    """

    def __init__(self):
        self.llm = llm

        # Prompt para detectar evolución del usuario
        self.evolution_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Eres un Psicólogo Evolutivo y Analista de Personalidad. Tu objetivo es detectar cambios significativos "
                    "en el perfil del usuario basándote en su última sesión de chat.\n"
                    "Busca:\n"
                    "1. Evolución de vida: Nuevos valores, metas alcanzadas, hitos (milestones).\n"
                    "2. Adaptación de MAGI: ¿Cómo prefiere el usuario que le hablen? (estilo, nivel de humor, formalidad).\n"
                    "3. Preferencias aprendidas: Cosas que le gustan o disgustan específicamente.\n"
                    "\n"
                    "Responde estrictamente en JSON con los campos:\n"
                    "- 'new_values': [lista]\n"
                    "- 'new_goals': [lista]\n"
                    "- 'milestone_detected': 'string' o null\n"
                    "- 'personality_adaptation': {{\n"
                    "    'preferred_style': 'casual'|'formal'|'tecnico'|'empatico',\n"
                    "    'humor_tolerance_delta': float (-0.1 a 0.1),\n"
                    "    'formality_level_delta': float (-0.1 a 0.1),\n"
                    "    'new_preferences': [lista]\n"
                    "}}\n"
                ),
            ),
            (
                "user",
                "PERFIL ACTUAL:\n{current_profile}\n\nRESUMEN DE SESIÓN:\n{session_summary}\n\nDetecta evolución:",
            ),
        ])

    async def should_consolidate(self, chat_id: str, message_count: int) -> bool:
        """
        4.2: Verifica si se cumplen las condiciones de consolidación.
        """
        # Regla 1: Más de 20 mensajes
        if message_count >= 20:
            return True

        # Regla 2: Más de 6 horas de inactividad
        from src.memory.long_term_memory import long_term_memory

        buffer = await long_term_memory.get_buffer()
        last_activity = await buffer.get_last_activity(chat_id)

        if last_activity > 0:
            elapsed = time.time() - last_activity
            if elapsed > 21600:  # 6 horas en segundos
                return True

        return False

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extrae un objeto JSON de un bloque de texto usando regex."""
        try:
            # Buscar el primer '{' y el último '}'
            match = re.search(r"(\{[\s\S]*\})", text)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)  # Fallback a loads directo
        except Exception as e:
            logger.error(f"Error extrayendo JSON: {e}")
            raise

    async def consolidate_session(self, chat_id: str):
        """
        4.3, 4.4, 4.5: Proceso completo de consolidación.
        """
        logger.info(f"Iniciando consolidación de sesión para {chat_id}")

        from src.memory.fact_extractor import fact_extractor
        from src.memory.knowledge_base import knowledge_base_manager
        from src.memory.long_term_memory import long_term_memory

        data = await long_term_memory.get_summary(chat_id)
        raw_buffer = data["buffer"]

        if not raw_buffer:
            return

        # 1. Generar resumen y actualizar memoria episódica
        await long_term_memory.update_memory(chat_id)

        # 2. EXTRAER HECHOS ESTRUCTURADOS (Hybrid Memory)
        try:
            current_knowledge = await knowledge_base_manager.load_knowledge(chat_id)

            # Convertir buffer a texto para el extractor
            conversation_text = "\n".join([
                f"{m['role']}: {m['content']}" for m in raw_buffer
            ])

            updated_knowledge = await fact_extractor.extract_facts(
                conversation_text, current_knowledge
            )
            await knowledge_base_manager.save_knowledge(chat_id, updated_knowledge)
            logger.info(f"Hechos estructurados actualizados para {chat_id}")

            # Sincronización explícita KB -> Profile
            await self._sync_user_name_to_profile(chat_id, updated_knowledge)

        except Exception as e:
            logger.error(
                f"Error extrayendo hechos durante consolidación para {chat_id}: {e}"
            )

        # 3. 4.4: Detectar evolución y actualizar perfil
        # Obtenemos el nuevo resumen consolidado
        new_data = await long_term_memory.get_summary(chat_id)
        summary = new_data["summary"]
        profile = await user_profile_manager.load_profile(chat_id)

        try:
            chain = self.evolution_prompt | self.llm
            response = await chain.ainvoke({
                "current_profile": json.dumps(profile, ensure_ascii=False),
                "session_summary": summary,
            })

            evolution_data = self._extract_json(str(response.content).strip())
            await self._apply_evolution(chat_id, profile, evolution_data)

        except Exception as e:
            logger.error(f"Error detectando evolución para {chat_id}: {e}")

        # 4. 4.5: Almacenar Log de Sesión en SQLite (Local-First)
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_content = {
                "chat_id": chat_id,
                "timestamp": timestamp,
                "summary": summary,
                "raw_messages_count": len(raw_buffer),
                "type": "session_log",
            }

            store = get_sqlite_store()
            pipeline = IngestionPipeline(store)

            await pipeline.process_text(
                chat_id=chat_id,
                text=json.dumps(log_content, ensure_ascii=False),
                memory_type="document",
                metadata={"filename": f"session_{timestamp}.json", "type": "log"},
            )
            logger.info(f"Log de sesión guardado en SQLite para {chat_id}")

            # 5. Trigger Cloud Backup (Fase 7)
            import asyncio

            from src.memory.backup import CloudBackupManager

            backup_mgr = CloudBackupManager(store)
            # Ejecutar en segundo plano para no bloquear la respuesta
            asyncio.create_task(backup_mgr.create_backup())

        except Exception as e:
            logger.warning(
                f"Error guardando log de sesión en SQLite para {chat_id}: {e}"
            )

    async def _sync_user_name_to_profile(
        self, chat_id: str, knowledge: dict[str, Any]
    ) -> None:
        """
        Sincroniza el nombre detectado en la Knowledge Base con el Perfil.
        Si FactExtractor encontró un 'user_name' explícito, este sobrescribe cualquier dato previo.
        """
        detected_name = knowledge.get("user_name")
        if not detected_name:
            return

        try:
            profile = await user_profile_manager.load_profile(chat_id)
            current_profile_name = profile.get("identity", {}).get("name")

            if detected_name != current_profile_name:
                logger.info(
                    f"Sync Identity: Updating profile name from '{current_profile_name}' to '{detected_name}'"
                )
                profile["identity"]["name"] = detected_name
                await user_profile_manager.save_profile(chat_id, profile)
        except Exception as e:
            logger.error(f"Error syncing user name to profile for {chat_id}: {e}")

    async def _apply_evolution(
        self, chat_id: str, profile: dict[str, Any], evo: dict[str, Any]
    ):
        """Aplica los cambios detectados al perfil."""
        updated = False

        if evo.get("milestone_detected"):
            await user_profile_manager.add_evolution_entry(
                chat_id, evo["milestone_detected"]
            )
            updated = True

        # Actualizar valores/metas si hay novedades
        if evo.get("new_values"):
            profile["values_and_goals"]["core_values"].extend(evo["new_values"])
            profile["values_and_goals"]["core_values"] = list(
                set(profile["values_and_goals"]["core_values"])
            )
            updated = True

        # --- Adaptación de Personalidad ---
        if "personality_adaptation" in evo:
            pa_evo = evo["personality_adaptation"]
            pa = profile.get("personality_adaptation", {})

            # Estilo preferido
            if pa_evo.get("preferred_style"):
                pa["preferred_style"] = pa_evo["preferred_style"]
                updated = True

            # Ajuste de niveles (clamping entre 0 y 1)
            pa["humor_tolerance"] = max(
                0.0,
                min(
                    1.0,
                    pa.get("humor_tolerance", 0.7)
                    + pa_evo.get("humor_tolerance_delta", 0.0),
                ),
            )
            pa["formality_level"] = max(
                0.0,
                min(
                    1.0,
                    pa.get("formality_level", 0.3)
                    + pa_evo.get("formality_level_delta", 0.0),
                ),
            )

            # Nuevas preferencias
            if pa_evo.get("new_preferences"):
                pa["learned_preferences"] = list(
                    set(pa.get("learned_preferences", []) + pa_evo["new_preferences"])
                )
                updated = True

            profile["personality_adaptation"] = pa

        if updated:
            await user_profile_manager.save_profile(chat_id, profile)
            logger.info(f"Perfil evolucionado (y personalidad adaptada) para {chat_id}")


# Singleton
consolidation_manager = ConsolidationManager()
