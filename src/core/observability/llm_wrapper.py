# src/core/observability/llm_wrapper.py
"""
Wrapper para LLM con observabilidad automática.
Responsabilidad única: Integrar tracking transparente con LLM calls.
"""

from typing import Any, cast

from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import Runnable, RunnableConfig

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

    def invoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        """
        Invoke síncrono con observabilidad.

        Args:
            input: Input para el LLM
            config: Configuración opcional
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del LLM
        """
        handler = self._create_handler(config)
        # Aseguramos que config es un dict válido para pasar al LLM
        safe_config = config or {}
        # Combinamos handlers
        existing_callbacks = safe_config.get("callbacks", [])
        if isinstance(existing_callbacks, list):
            callbacks = existing_callbacks + [handler]
        else:
            callbacks = [existing_callbacks, handler]  # type: ignore

        # Inyectamos el handler en una copia de la config
        run_config = {**safe_config, "callbacks": callbacks}  # type: ignore
        return self.llm.invoke(input, cast(RunnableConfig, run_config), **kwargs)

    async def ainvoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        """
        Invoke asíncrono con observabilidad.

        Args:
            input: Input para el LLM
            config: Configuración opcional
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del LLM
        """
        handler = self._create_handler(config)
        safe_config = config or {}
        existing_callbacks = safe_config.get("callbacks", [])
        if isinstance(existing_callbacks, list):
            callbacks = existing_callbacks + [handler]
        else:
            callbacks = [existing_callbacks, handler]  # type: ignore

        run_config = {**safe_config, "callbacks": callbacks}  # type: ignore

        return await self.llm.ainvoke(input, cast(RunnableConfig, run_config), **kwargs)

    def batch(
        self,
        inputs: list[Any],
        config: RunnableConfig | list[RunnableConfig] | None = None,
        *,
        return_exceptions: bool = False,
        **kwargs: Any,
    ) -> list[Any]:
        """
        Batch processing con observabilidad.
        """
        # Nota: Para batch, simplificamos usando la config global o la primera
        # Idealmente deberíamos inyectar handler en cada config de la lista
        handler_config = config[0] if isinstance(config, list) and config else config
        handler = self._create_handler(
            handler_config if isinstance(handler_config, dict) else None
        )

        # Esta implementación de wrapper para batch es simplificada
        # Simplemente inyectamos el callback en el LLM globalmente para este batch
        return self.llm.with_config({"callbacks": [handler]}).batch(
            inputs, config, return_exceptions=return_exceptions, **kwargs
        )

    async def abatch(
        self,
        inputs: list[Any],
        config: RunnableConfig | list[RunnableConfig] | None = None,
        *,
        return_exceptions: bool = False,
        **kwargs: Any,
    ) -> list[Any]:
        """
        Batch processing asíncrono con observabilidad.
        """
        handler_config = config[0] if isinstance(config, list) and config else config
        handler = self._create_handler(
            handler_config if isinstance(handler_config, dict) else None
        )

        return await self.llm.with_config({"callbacks": [handler]}).abatch(
            inputs, config, return_exceptions=return_exceptions, **kwargs
        )

    def _create_handler(
        self, config: RunnableConfig | dict[str, Any] | None
    ) -> LLMObservabilityHandler:
        """Crea handler de observabilidad."""
        call_type = self._extract_call_type(config)
        return LLMObservabilityHandler(call_type)

    def _extract_call_type(self, config: RunnableConfig | dict[str, Any] | None) -> str:
        """Extrae call_type de la configuración."""
        if config and "metadata" in config:
            # RunnableConfig usa 'metadata', nuestro dict custom usaba 'call_type' directo o en metadata
            metadata = config.get("metadata", {})
            if "call_type" in metadata:
                return str(metadata["call_type"])

        # Soporte legacy para dicts planos (aunque RunnableConfig es TypedDict, en runtime es dict)
        config_dict = cast(dict[str, Any], config)
        if isinstance(config, dict) and "call_type" in config_dict:
            return str(config_dict["call_type"])

        return self.default_call_type

    def _add_handler_to_config(
        self, config: dict[str, Any] | None, handler: LLMObservabilityHandler
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
