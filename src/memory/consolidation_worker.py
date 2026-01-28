import json
import logging
import time
from datetime import datetime
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.engine import llm
from src.core.profile_manager import user_profile_manager
from src.tools.google_file_search import file_search_tool

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
                    "- 'personality_adaptation': {\n"
                    "    'preferred_style': 'casual'|'formal'|'tecnico'|'empatico',\n"
                    "    'humor_tolerance_delta': float (-0.1 a 0.1),\n"
                    "    'formality_level_delta': float (-0.1 a 0.1),\n"
                    "    'new_preferences': [lista]\n"
                    "}"
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

    async def consolidate_session(self, chat_id: str):
        """
        4.3, 4.4, 4.5: Proceso completo de consolidación.
        """
        logger.info(f"Iniciando consolidación de sesión para {chat_id}")

        from src.memory.long_term_memory import long_term_memory

        data = await long_term_memory.get_summary(chat_id)
        raw_buffer = data["buffer"]

        if not raw_buffer:
            return

        # 1. Generar resumen y actualizar memoria (Ya lo hace long_term_memory.update_memory)
        # Pero aquí lo haremos de forma más integral para el perfil evolutivo.
        await long_term_memory.update_memory(chat_id)

        # 2. 4.4: Detectar evolución y actualizar perfil
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

            evolution_data = json.loads(str(response.content).strip())
            await self._apply_evolution(chat_id, profile, evolution_data)

        except Exception as e:
            logger.error(f"Error detectando evolución para {chat_id}: {e}")

        # 3. 4.5: Subir Log de Sesión a la Nube
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_content = {
                "chat_id": chat_id,
                "timestamp": timestamp,
                "summary": summary,
                "raw_messages_count": len(raw_buffer),
            }
            await file_search_tool.upload_from_string(
                content=json.dumps(log_content, ensure_ascii=False),
                filename=f"sessions/session_{timestamp}.json",
                chat_id=chat_id,
                mime_type="application/json",
            )
        except Exception as e:
            logger.warning(f"Error subiendo log de sesión para {chat_id}: {e}")

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
