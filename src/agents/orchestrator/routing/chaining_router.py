# src/agents/orchestrator/routing/chaining_router.py
"""
ChainingRouter implementation.

Responsabilidad única: lógica de chaining entre especialistas.
Extraído del MasterOrchestrator para cumplir SRP y hacer configurable las reglas.
"""

import logging
from typing import Any

from src.agents.orchestrator.strategies import RoutingStrategy
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)


class ConfigurableChainRouter(RoutingStrategy):
    """
    Router para chaining configurable entre especialistas.

    Responsabilidades:
    - Determinación de siguiente especialista en chains
    - Aplicación de reglas de chaining configurables
    - Manejo de historial de especialistas
    - Decisión de finalización de chains
    """

    def __init__(self, chaining_config: dict[str, Any]):
        """
        Initialize router con configuración de chaining.

        Args:
            chaining_config: Configuración de reglas de chaining
        """
        self._config = chaining_config
        self._chain_rules = chaining_config.get("chain_rules", {})
        self._fallback_action = chaining_config.get("fallback_action", "__end__")

    async def route(self, state: GraphStateV2) -> str:
        """
        Determina el siguiente paso en el chain de especialistas.

        Args:
            state: Estado del grafo con payload y historial

        Returns:
            str: Nombre del siguiente especialista o "__end__"
        """
        # Actualizar estado con información del especialista actual
        self._update_specialist_history(state)

        # Aplicar reglas de chaining
        return self._apply_chaining_rules(state)

    def _update_specialist_history(self, state: GraphStateV2) -> None:
        """
        Actualiza el historial de especialistas en el estado.

        Args:
            state: Estado del grafo a actualizar
        """
        current_payload = state.get("payload", {})
        last_specialist = current_payload.get("last_specialist")
        next_action = current_payload.get("next_action")

        logger.info(
            f"Chain router: analizando estado desde {last_specialist}, "
            f"next_action: {next_action}"
        )

        # Inferir especialista actual si no está explícito
        if not last_specialist:
            last_specialist = self._infer_current_specialist(state)

        # Actualizar historial
        specialists_history = current_payload.get("specialists_history", [])
        if last_specialist and last_specialist not in specialists_history:
            specialists_history.append(last_specialist)

        # Actualizar payload
        state["payload"] = {
            **current_payload,
            "specialists_history": specialists_history,
            "last_specialist": last_specialist,
        }

        logger.info(f"Chain router: historial actualizado: {specialists_history}")

    def _infer_current_specialist(self, state: GraphStateV2) -> str:
        """
        Infiere el especialista actual basado en el evento.

        Args:
            state: Estado del grafo

        Returns:
            str: Nombre del especialista inferido
        """
        event = state.get("event")
        if event and hasattr(event, "event_type") and event.event_type == "audio":
            return "transcription_agent"
        return "unknown"

    def _apply_chaining_rules(self, state: GraphStateV2) -> str:
        """
        Aplica las reglas de chaining configuradas.

        Args:
            state: Estado del grafo

        Returns:
            str: Siguiente nodo según las reglas
        """
        # Verificar errores primero
        if state.get("error_message"):
            logger.error("Error en estado, finalizando chain")
            return "__end__"

        payload = state.get("payload", {})
        last_specialist = payload.get("last_specialist")
        next_action = payload.get("next_action")
        specialists_history = payload.get("specialists_history", [])

        logger.info(
            f"Aplicando reglas: last={last_specialist}, "
            f"action={next_action}, history={specialists_history}"
        )

        # Aplicar reglas específicas por especialista
        if last_specialist in self._chain_rules:
            rule = self._chain_rules[last_specialist]
            next_specialist = rule.get("next_specialist")

            logger.info(
                f"Chain: Regla encontrada para {last_specialist} → {next_specialist}"
            )

            # Verificar condiciones de la regla
            if self._rule_conditions_met(rule, payload, specialists_history):
                logger.info(f"Chain: {last_specialist} → {next_specialist}")
                return next_specialist
            else:
                logger.warning(
                    f"Chain: Condiciones no cumplidas para {last_specialist}"
                )
        else:
            logger.warning(
                f"Chain: Sin regla para especialista '{last_specialist}'. Reglas disponibles: {list(self._chain_rules.keys())}"
            )

        # Reglas especiales para acciones
        if next_action == "respond_to_user":
            logger.info("Chain: Acción respond_to_user → END")
            return "__end__"

        # Fallback por defecto
        logger.info(
            f"Chain: Sin regla específica, usando fallback: {self._fallback_action}"
        )
        return self._fallback_action

    def _rule_conditions_met(
        self, rule: dict[str, Any], payload: dict[str, Any], specialists_history: list
    ) -> bool:
        """
        Verifica si las condiciones de una regla se cumplen.

        Args:
            rule: Regla de chaining a verificar
            payload: Payload actual del estado
            specialists_history: Historial de especialistas

        Returns:
            bool: True si las condiciones se cumplen
        """
        # Verificar que el especialista destino no esté ya en el historial
        next_specialist = rule.get("next_specialist")
        if next_specialist in specialists_history:
            logger.warning(
                f"Chain condition FAIL: Especialista {next_specialist} ya ejecutado en history {specialists_history}"
            )
            return False

        logger.info(
            f"Chain condition OK: Especialista {next_specialist} no está en history {specialists_history}"
        )

        # Verificar condiciones adicionales si existen
        conditions = rule.get("conditions", {})

        # Ejemplo: verificar payload específico
        required_payload = conditions.get("required_payload")
        if required_payload:
            for key, expected_value in required_payload.items():
                if payload.get(key) != expected_value:
                    return False

        return True
