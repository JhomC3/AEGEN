# src/agents/modular/example_agent.py
"""
Ejemplo de implementación de BaseModularAgent siguiendo filosofía del proyecto.
Demuestra cómo implementar un agente simple, async y con single responsibility.
"""

import logging
from typing import Any

from src.core.interfaces.modular_agent import ModularAgentBase
from src.core.schemas import AgentCapability, AgentContext, AgentResult

logger = logging.getLogger(__name__)


class ExampleModularAgent(ModularAgentBase):
    """Agente de ejemplo que valida input de usuarios."""

    def __init__(self):
        super().__init__(
            name="example_validator_agent", capabilities=[AgentCapability.VALIDATION]
        )

    async def execute(self, input_data: Any, context: AgentContext) -> AgentResult:
        """Valida input_data de manera async."""
        try:
            logger.info(f"ExampleAgent validating input for user {context.user_id}")

            # Validación simple - single responsibility
            if not input_data:
                return self._create_error_result(
                    "Input data is empty", "No data provided for validation"
                )

            # Simulación async I/O (obligatorio por filosofía)
            # En implementación real sería: await validate_with_external_service()
            await self._async_validation(input_data)

            return self._create_success_result(
                data={"validated": True, "input_type": type(input_data).__name__},
                message="Input validation completed successfully",
            )

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return self._create_error_result("Validation failed", str(e))

    async def _async_validation(self, input_data: Any) -> None:
        """Placeholder para validación async."""
        # Simulate async I/O - filosofía requires no sync operations
        import asyncio

        await asyncio.sleep(0.001)  # Tiny async operation

        # Validación simple
        if isinstance(input_data, dict) and not input_data:
            raise ValueError("Empty dictionary not allowed")
