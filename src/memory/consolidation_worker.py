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
                    "Eres un Psicólogo Evolutivo y Analista de Datos. Tu objetivo es detectar cambios significativos "
                    "en el perfil del usuario basándote en su última sesión de chat.\n"
                    "Busca: Nuevos valores, metas alcanzadas, cambios de humor recurrentes, nuevos temas de interés, "
                    "o hitos (milestones) en su camino.\n"
                    "Responde en JSON con los campos: 'new_values', 'new_goals', 'mood_shift', 'milestone_detected'."
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

        if updated:
            await user_profile_manager.save_profile(chat_id, profile)
            logger.info(f"Perfil evolucionado para {chat_id}")


# Singleton
consolidation_manager = ConsolidationManager()
