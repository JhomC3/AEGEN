import logging

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.core.routing_models import IntentType

logger = logging.getLogger(__name__)


class SpecialistMapper:
    """
    Mapeador de intents a especialistas disponibles.

    Maneja lógica de mapeo entre clasificación de intents
    y especialistas reales del sistema.
    """

    # Mapeo preferido por intent
    INTENT_TO_SPECIALISTS = {
        IntentType.FILE_ANALYSIS: ["chat_specialist"],
        IntentType.PLANNING: ["chat_specialist"],
        IntentType.SEARCH: ["chat_specialist"],
        IntentType.CHAT: ["chat_specialist"],
        IntentType.HELP: ["chat_specialist"],
        IntentType.VULNERABILITY: ["cbt_specialist"],
        IntentType.TOPIC_SHIFT: ["chat_specialist"],
    }

    def map_intent_to_specialist(
        self, intent: IntentType, cache: SpecialistCache
    ) -> str:
        """
        Mapea intent a especialista disponible en el sistema.

        Args:
            intent: Intent clasificado
            cache: Cache con especialistas disponibles

        Returns:
            str: Nombre del especialista más apropiado
        """
        available_specialists = list(cache.get_tool_to_specialist_map().values())
        preferred_specialists = self.INTENT_TO_SPECIALISTS.get(
            intent, ["chat_specialist"]
        )

        # Buscar primer especialista disponible en orden de preferencia
        for preferred in preferred_specialists:
            if preferred in available_specialists:
                return preferred
            else:
                # Log cuando preferido no está disponible
                logger.debug(
                    f"Especialista preferido '{preferred}' para intent '{intent.value}' "
                    f"no disponible. Probando siguiente opción."
                )

        logger.warning(
            f"Ningún especialista preferido disponible para intent '{intent.value}'. "
            f"Usando fallback: chat_specialist"
        )
        # Fallback seguro siempre disponible
        return "chat_specialist"
