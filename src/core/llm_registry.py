# src/core/llm_registry.py
"""
LLM Registry & LCEL-Compatible Call Router.

Orquesta la resolución dinámica de proveedores de IA basándose en
un inventario declarativo config/llm_inventory.yaml, con soporte
nativo para rotación de keys y fallbacks en caliente.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

import yaml
from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel, SecretStr

logger = logging.getLogger(__name__)


class ModelRoute(BaseModel):
    provider: str
    model: str
    temperature: float = 0.7
    key_rotation: bool = False
    max_input_chars: int | None = None
    fallbacks: list[dict[str, Any]] = []


class CallRegistry:
    """Carga y gestiona el mapeo de llamadas LLM basándose en llm_inventory.yaml."""

    def __init__(self, yaml_path: str = "config/llm_inventory.yaml") -> None:
        self.yaml_path = Path(yaml_path)
        self.routes: dict[str, ModelRoute] = {}
        self.load_inventory()

    def load_inventory(self) -> None:
        """Carga el inventario YAML. Si falla en producción lanza excepción."""
        from src.core.config import settings
        from src.core.config.environments import Environment

        if not self.yaml_path.exists():
            if settings.APP_ENV == Environment.PRODUCTION:
                raise FileNotFoundError(
                    f"Archivo de configuración crítico no encontrado: {self.yaml_path}"
                )
            logger.warning(
                "llm_inventory.yaml no encontrado en desarrollo. "
                "Cargando mapeo en memoria por defecto."
            )
            self._load_fallback_in_memory()
            return

        try:
            with self.yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                calls_data = data.get("calls", {})
                for call_name, route_data in calls_data.items():
                    self.routes[call_name] = ModelRoute(**route_data)
            logger.info("LLM CallRegistry cargado con %d rutas", len(self.routes))
        except Exception as e:
            if settings.APP_ENV == Environment.PRODUCTION:
                raise RuntimeError(
                    f"Fallo crítico cargando llm_inventory.yaml: {e}"
                ) from e
            logger.exception(
                "Error cargando llm_inventory.yaml en desarrollo. Usando defaults."
            )
            self._load_fallback_in_memory()

    def _load_fallback_in_memory(self) -> None:
        """Carga un mapeo de desarrollo básico si el YAML no existe o falla."""
        default_route = ModelRoute(
            provider="google",
            model="gemini-2.5-flash-lite",
            temperature=0.7,
            key_rotation=True,
            fallbacks=[{"provider": "groq", "model": "openai/gpt-oss-120b"}],
        )
        for name in [
            "chat_response",
            "cbt_therapeutic_response",
            "psicotrading_response",
            "routing_analysis",
            "rag_chunking",
            "rag_fact_extraction",
            "rag_reranking",
            "rag_summarization",
            "nudge_extraction",
            "context_compression",
            "skill_generation",
            "life_review",
        ]:
            self.routes[name] = default_route

    def resolve_provider(self, call_name: str, sync: bool = False) -> BaseLanguageModel:
        """Resuelve el proveedor concreto para el call_name, con fallbacks."""
        route = self.routes.get(call_name)
        if not route:
            logger.warning(
                "Ruta LLM '%s' no encontrada. Usando chat_response.", call_name
            )
            route = self.routes.get("chat_response")
            if not route:
                raise RuntimeError("No default route configured in registry.")

        return self._build_model_chain(route, sync)

    def _build_model_chain(self, route: ModelRoute, sync: bool) -> BaseLanguageModel:
        """Crea el modelo primario y concatena su secuencia de fallbacks nativos."""
        primary = self._instantiate_concrete_provider(
            provider=route.provider,
            model=route.model,
            temperature=route.temperature,
            use_rotation=route.key_rotation,
            sync=sync,
        )

        if not route.fallbacks:
            return primary

        fallback_instances = []
        for fb in route.fallbacks:
            try:
                fb_inst = self._instantiate_concrete_provider(
                    provider=fb.get("provider", "groq"),
                    model=fb.get("model", "llama3-70b-8192"),
                    temperature=route.temperature,
                    use_rotation=fb.get("key_rotation", False),
                    sync=sync,
                )
                fallback_instances.append(fb_inst)
            except Exception as e:
                logger.error("No se pudo instanciar fallback LLM %s: %s", fb, e)

        if fallback_instances:
            return cast(BaseLanguageModel, primary.with_fallbacks(fallback_instances))
        return primary

    def _instantiate_concrete_provider(  # noqa: C901
        self,
        provider: str,
        model: str,
        temperature: float,
        use_rotation: bool,
        sync: bool,
    ) -> BaseLanguageModel:
        """Inicializa físicamente la conexión del SDK correspondiente de LangChain."""
        from src.core.config import settings

        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            target_model = model if model.startswith("models/") else f"models/{model}"
            api_key: str | None = None

            if use_rotation:
                from src.core.providers.round_robin_key import get_round_robin_provider

                rr = get_round_robin_provider()
                api_key = rr.get_key_sync()

            if not api_key:
                api_key = (
                    settings.GOOGLE_API_KEY.get_secret_value()
                    if settings.GOOGLE_API_KEY
                    else None
                )

            if not api_key:
                raise RuntimeError("No Google/Gemini API Key configurada.")

            return ChatGoogleGenerativeAI(
                model=target_model,
                temperature=temperature,
                top_p=0.9,
                top_k=40,
                convert_system_message_to_human=True,
                api_key=SecretStr(api_key),
            )

        if provider == "groq":
            from langchain_groq import ChatGroq

            groq_raw = (
                settings.GROQ_API_KEY.get_secret_value()
                if settings.GROQ_API_KEY
                else None
            )
            if not groq_raw:
                raise RuntimeError("No Groq API Key configurada.")

            return ChatGroq(
                model=model,
                temperature=temperature,
                api_key=SecretStr(groq_raw),
                max_retries=1,
                timeout=30,
            )

        if provider == "openrouter":
            from langchain_openai import ChatOpenAI

            openrouter_raw = (
                settings.OPENROUTER_API_KEY.get_secret_value()
                if settings.OPENROUTER_API_KEY
                else None
            )
            if not openrouter_raw:
                raise RuntimeError("No OpenRouter API Key configurada.")

            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=SecretStr(openrouter_raw),
                base_url="https://openrouter.ai/api/v1",
                max_retries=1,
                timeout=30,
            )

        raise ValueError(f"Proveedor LLM desconocido o no soportado: {provider}")


class ManagedLLM(Runnable):
    """
    Runnable intermedio compatible con LCEL.
    Se comporta como un BaseLanguageModel ante LangChain y el operador Pipe '|',
    pero difiere la resolución del proveedor e inyección de llaves a la llamada.
    """

    def __init__(self, call_name: str, registry: CallRegistry) -> None:
        self.call_name = call_name
        self.registry = registry
        self._bound_tools: Sequence[Any] | None = None
        self._kwargs: dict[str, Any] = {}

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> ManagedLLM:
        """Replica bind_tools clonando el ManagedLLM."""
        clone = ManagedLLM(self.call_name, self.registry)
        clone._bound_tools = tools
        clone._kwargs = kwargs
        return clone

    def _resolve_with_tools(self, sync: bool) -> Any:
        """Resuelve proveedor y aplica bind_tools si está configurado."""
        concrete: Any = self.registry.resolve_provider(self.call_name, sync=sync)
        if self._bound_tools:
            return concrete.bind_tools(self._bound_tools, **self._kwargs)
        return concrete

    async def ainvoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        """Invocación asíncrona resolviendo el pool dinámico y telemetría."""
        concrete_llm = self._resolve_with_tools(sync=False)
        obs_config = self._enrich_config(config)
        self._capture_metadata(input, obs_config)

        # Timeout adaptativo según el tipo de llamada
        # Routing: 15s, Chat/CBT: 30s, RAG: 20s
        timeout = 15 if self.call_name == "routing_analysis" else 30
        try:
            return await asyncio.wait_for(
                concrete_llm.ainvoke(
                    input, config=cast(RunnableConfig, obs_config), **kwargs
                ),
                timeout=timeout,
            )
        except TimeoutError:
            logger.error("LLM call '%s' timed out after %ds", self.call_name, timeout)
            raise RuntimeError(
                f"LLM call '{self.call_name}' timed out after {timeout}s"
            ) from None

    def invoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        """Invocación síncrona resolviendo el pool dinámico y telemetría."""
        concrete_llm = self._resolve_with_tools(sync=True)
        obs_config = self._enrich_config(config)
        self._capture_metadata(input, obs_config)
        return concrete_llm.invoke(
            input, config=cast(RunnableConfig, obs_config), **kwargs
        )

    async def astream(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        """Invocación de streaming asíncrono."""
        concrete_llm = self._resolve_with_tools(sync=False)
        obs_config = self._enrich_config(config)
        self._capture_metadata(input, obs_config)
        async for chunk in concrete_llm.astream(
            input, config=cast(RunnableConfig, obs_config), **kwargs
        ):
            yield chunk

    def _enrich_config(self, config: RunnableConfig | None) -> dict[str, Any]:
        """Inyecta el callback de observabilidad de Prometheus en el config."""
        from src.core.engine import create_observable_config

        return create_observable_config(
            self.call_name, dict(config) if config else None
        )

    def _capture_metadata(self, input_data: Any, config: dict[str, Any]) -> None:  # noqa: C901
        """Mide tamaños de chars del prompt en metadata para observabilidad segura."""
        try:
            system_chars = 0
            user_chars = 0
            history_messages = 0

            if hasattr(input_data, "messages"):
                messages = input_data.messages
            elif isinstance(input_data, list):
                messages = input_data
            elif isinstance(input_data, dict):
                messages = []
                user_chars += len(str(input_data.get("user_message", "")))
                hist = input_data.get("messages", [])
                if isinstance(hist, list):
                    history_messages = len(hist)
            else:
                messages = [input_data]

            for msg in messages:
                content = getattr(msg, "content", str(msg))
                role = getattr(msg, "type", "")
                if role == "system" or "system" in str(type(msg)).lower():
                    system_chars += len(content)
                elif (
                    role == "human"
                    or "human" in str(type(msg)).lower()
                    or "user" in str(type(msg)).lower()
                ):
                    user_chars += len(content)
                elif role == "ai" or "ai" in str(type(msg)).lower():
                    history_messages += 1

            if "metadata" not in config:
                config["metadata"] = {}

            config["metadata"].update({
                "system_prompt_chars": system_chars,
                "user_message_chars": user_chars,
                "history_messages_count": history_messages,
                "rag_context_chars": len(str(input_data.get("knowledge_context", "")))
                if isinstance(input_data, dict)
                else 0,
                "learned_preferences_chars": len(
                    str(input_data.get("structured_knowledge", ""))
                )
                if isinstance(input_data, dict)
                else 0,
            })
        except Exception:
            logger.debug("Error capturando metadatos de observabilidad", exc_info=True)


# Instancia del registro central
_registry = CallRegistry()


def get_llm(call_name: str) -> ManagedLLM:
    """Función de conveniencia para recuperar un ManagedLLM LCEL-compatible."""
    return ManagedLLM(call_name, _registry)


def llm_call(call_name: str) -> Callable[[Callable], Callable]:
    """
    Decorador para inyectar un ManagedLLM en las funciones que hacen ainvoke() directo.

    Uso:
        @llm_call("chat_response")
        async def responder(..., *, _llm=None):
            return await _llm.ainvoke(...)
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs["_llm"] = get_llm(call_name)
            return await func(*args, **kwargs)

        import functools

        return functools.wraps(func)(wrapper)

    return decorator
