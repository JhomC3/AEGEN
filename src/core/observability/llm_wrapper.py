from typing import Any, cast

from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import Runnable, RunnableConfig

from .handler import LLMObservabilityHandler


class ObservableLLM(Runnable):
    """Wrapper para LLM con observabilidad automática."""

    def __init__(self, llm: BaseLanguageModel, call_type: str = "general"):
        self.llm = llm
        self.default_call_type = call_type

    def invoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        """Invoke síncrono con observabilidad."""
        handler = self._create_handler(config)
        safe_config = dict(config) if config else {}
        callbacks = safe_config.get("callbacks", [])
        if isinstance(callbacks, list):
            new_callbacks = callbacks + [handler]
        else:
            new_callbacks = [callbacks, handler]
        safe_config["callbacks"] = new_callbacks
        return self.llm.invoke(input, cast(RunnableConfig, safe_config), **kwargs)

    async def ainvoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        """Invoke asíncrono con observabilidad."""
        handler = self._create_handler(config)
        safe_config = dict(config) if config else {}
        callbacks = safe_config.get("callbacks", [])
        if isinstance(callbacks, list):
            new_callbacks = callbacks + [handler]
        else:
            new_callbacks = [callbacks, handler]
        safe_config["callbacks"] = new_callbacks
        return await self.llm.ainvoke(
            input, cast(RunnableConfig, safe_config), **kwargs
        )

    def _create_handler(
        self, config: RunnableConfig | dict[str, Any] | None
    ) -> LLMObservabilityHandler:
        call_type = self._extract_call_type(config)
        return LLMObservabilityHandler(call_type)

    def _extract_call_type(self, config: RunnableConfig | dict[str, Any] | None) -> str:
        if config:
            # 1. Intentar desde metadata (RunnableConfig)
            metadata = config.get("metadata", {})
            if "call_type" in metadata:
                return str(metadata["call_type"])

            # 2. Intentar desde dict plano (Legacy)
            if isinstance(config, dict):
                # Usamos dict.get para evitar error de TypedDict
                val = cast(dict[str, Any], config).get("call_type")
                if val:
                    return str(val)

        return self.default_call_type

    def __getattr__(self, name: str) -> Any:
        return getattr(self.llm, name)
