# src/core/observability/llm_wrapper.py
"""
Wrapper para LLM con observabilidad automática.
Responsabilidad única: Integrar tracking transparente con LLM calls.
"""

from typing import Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import Runnable

from .handler import LLMObservabilityHandler


class ObservableLLM(Runnable):
    """
    Wrapper para LLM que incluye observabilidad automática.

    Mantiene la misma interfaz que el LLM original pero agrega
    tracking transparente de todas las llamadas.
    """

    def __init__(self, llm: BaseLanguageModel, call_type: str = "general"):
        """
        Inicializa el wrapper observable.

        Args:
            llm: LLM base a envolver
            call_type: Tipo de llamada por defecto
        """
        self.llm = llm
        self.default_call_type = call_type

    def invoke(self, input_data: Any, config: dict[str, Any] | None = None, **kwargs) -> Any:
        """
        Invoke síncrono con observabilidad.

        Args:
            input_data: Input para el LLM
            config: Configuración opcional
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del LLM
        """
        handler = self._create_handler(config)
        config = self._add_handler_to_config(config, handler)

        return self.llm.invoke(input_data, config, **kwargs)

    async def ainvoke(self, input_data: Any, config: dict[str, Any] | None = None, **kwargs) -> Any:
        """
        Invoke asíncrono con observabilidad.

        Args:
            input_data: Input para el LLM
            config: Configuración opcional
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del LLM
        """
        handler = self._create_handler(config)
        config = self._add_handler_to_config(config, handler)

        return await self.llm.ainvoke(input_data, config, **kwargs)

    def batch(self, inputs: list[Any], config: dict[str, Any] | None = None, **kwargs) -> list[Any]:
        """
        Batch processing con observabilidad.

        Args:
            inputs: Lista de inputs
            config: Configuración opcional
            **kwargs: Argumentos adicionales

        Returns:
            Lista de respuestas
        """
        handler = self._create_handler(config)
        config = self._add_handler_to_config(config, handler)

        return self.llm.batch(inputs, config, **kwargs)

    async def abatch(self, inputs: list[Any], config: dict[str, Any] | None = None, **kwargs) -> list[Any]:
        """
        Batch processing asíncrono con observabilidad.

        Args:
            inputs: Lista de inputs
            config: Configuración opcional
            **kwargs: Argumentos adicionales

        Returns:
            Lista de respuestas
        """
        handler = self._create_handler(config)
        config = self._add_handler_to_config(config, handler)

        return await self.llm.abatch(inputs, config, **kwargs)

    def _create_handler(self, config: dict[str, Any] | None) -> LLMObservabilityHandler:
        """Crea handler de observabilidad."""
        call_type = self._extract_call_type(config)
        return LLMObservabilityHandler(call_type)

    def _extract_call_type(self, config: dict[str, Any] | None) -> str:
        """Extrae call_type de la configuración."""
        if config and "call_type" in config:
            return config["call_type"]
        return self.default_call_type

    def _add_handler_to_config(
        self,
        config: dict[str, Any] | None,
        handler: LLMObservabilityHandler
    ) -> dict[str, Any]:
        """Agrega handler a la configuración."""
        if config is None:
            config = {}

        if "callbacks" not in config:
            config["callbacks"] = []

        config["callbacks"].append(handler)
        return config

    def __getattr__(self, name: str) -> Any:
        """Delega atributos no encontrados al LLM original."""
        return getattr(self.llm, name)
