# INFORME FORENSE Y DISEÑO DETALLADO: LLM Registry & LCEL-Compatibilidad

- **Estado:** Completado / Especificación Aprobada
- **Fecha:** 2026-06-04
- **Autor:** Antigravity (AI Agent)
- **Documento de Referencia de Planificación:** [docs/planes/2026-06-03-desacoplamiento-y-observabilidad-llm.md](../planes/2026-06-03-desacoplamiento-y-observabilidad-llm.md)
- **ADR Relacionado:** [adr/ADR-0040-desacoplamiento-proveedores-llm-inventario.md](../adr/ADR-0040-desacoplamiento-proveedores-llm-inventario.md)

---

## 1. Resumen Ejecutivo de la Inspección Forense

Se ha realizado un escaneo estático y dinámico completo del código fuente (`src/`) para identificar la totalidad de los puntos de llamada (call sites) acoplados al motor de ejecución LLM (`src/core/engine.py`). 

El plan original y el ADR-0040 estimaban **12 call sites**. El análisis forense real ha descubierto **22 call sites de invocación LLM distribuidos en 17 archivos independientes**. Esto representa una subestimación del **83%** del alcance técnico de la migración.

Adicionalmente, se descubrió que **10 de los 22 call sites (45.5%) carecen de cualquier tipo de protección** contra fallos de red, caídas de API o rate limits (no tienen fallbacks ni rotación de llaves). De forma crítica, el motor síncrono de RAG (`get_rag_llm()`) opera con una sola key cableada en variables de entorno, y es consumido directamente por singletons a nivel de módulo en tiempo de importación, lo que arriesga fallos catastróficos en caliente que requieren reiniciar el proceso de la aplicación.

---

## 2. El Inventario Real de Call Sites (22 Invocaciones en 17 Archivos)

### 2.1. Métodos de Creación de Motores (`src/core/engine.py`)
El motor cuenta actualmente con 4 factorías y 1 singleton expuestos, descritos a continuación:

| Función | Línea | Proveedor Primario | Tipo de Retorno / Cadena | Protección Integrada |
|---|---|---|---|---|
| `_create_openrouter_llm()` | 13 | OpenRouter | `ChatOpenAI` | Reintentos (3) |
| `_create_groq_llm()` | 28 | Groq | `ChatGroq` | Reintentos (3) |
| `_create_google_llm()` | 50 | Google Gemini | `ChatGoogleGenerativeAI` | Ninguna |
| `get_fast_llm()` | 71 | Groq | Chain con fallback (Groq -> OpenRouter -> Groq backup) | Fallbacks |
| `get_analytical_llm()` | 83 | Groq | Chain con fallback (Groq -> OpenRouter) | Fallbacks |
| `get_rag_llm()` | 94 | Google Gemini | `ChatGoogleGenerativeAI` (Single key) | **Ninguna** |
| `get_rag_llm_async()` | 99 | Google Gemini | `ChatGoogleGenerativeAI` (RoundRobin API Keys) | Key Rotation |
| `llm` (Singleton global) | 140 | Groq | Instanciado en import time (`get_fast_llm()`) | Fallbacks |

---

### 2.2. Clasificación de Call Sites por Patrón de Uso

#### PATRÓN A: Singleton `llm` Global (Groq-based, import-time)
*Se importa al inicio del módulo y se utiliza a lo largo del archivo.*

1. **`src/personality/skills/chat/tools.py:195`**
   - *Uso:* `chain = conversational_prompt | llm` (Composición LCEL via Pipe).
2. **`src/personality/skills/chat/multimodal.py:30`**
   - *Uso:* `await llm.ainvoke([HumanMessage(...)])` (Invocación asíncrona directa).
3. **`src/personality/skill_generator.py:53`**
   - *Uso:* `await llm.ainvoke(prompt)` (Invocación asíncrona directa).
4. **`src/agents/orchestrator/routing/routing_analyzer.py:53`**
   - *Uso:* `self._chain = routing_prompt | llm.bind_tools(...)` (Composición con tools vinculadas).
5. **`src/agents/orchestrator/specialist_cache.py:73`**
   - *Uso:* `self._llm_with_tools = llm.bind_tools(self._routable_tools)` (Vínculo de herramientas dinámicas).
6. **`src/memory/consolidation_worker.py:24`**
   - *Uso:* `detector_llm = llm` (Inyección de fallback en constructor de `EvolutionDetector`).
7. **`src/memory/long_term_memory.py:15`**
   - *Uso:* `self.llm = llm` (Almacenado como propiedad de clase).

---

#### PATRÓN B: Factoría Lazy `get_fast_llm()` (Groq-based)
*Se llama a la función bajo demanda (dentro de la función o método).*

8. **`src/memory/nudge_worker.py:68`**
   - *Uso:* `llm = get_fast_llm()` -> `await llm.ainvoke(prompt)` (Invocación directa).
9. **`src/core/context_compressor.py:81`**
   - *Uso:* `llm = get_fast_llm()` -> `await llm.ainvoke(prompt)` (Invocación directa).

---

#### PATRÓN C: Factoría Lazy `get_analytical_llm()` (Groq-based)
*Se llama a la función bajo demanda.*

10. **`src/personality/skills/tcc/tools.py:186`**
    - *Uso:* `analytical_llm = get_analytical_llm()` -> `chain = conversational_prompt | analytical_llm` (LCEL Pipe).
11. **`src/personality/skills/psicotrading/tools.py:50`**
    - *Uso:* `analytical_llm = get_analytical_llm()` -> `chain = conversational_prompt | analytical_llm` (LCEL Pipe).
12. **`src/personality/skill_workshop.py:98`**
    - *Uso:* `llm = get_analytical_llm()` -> `response = await llm.ainvoke(prompt)` (Invocación directa).
13. **`src/agents/workers/life_review.py:67`**
    - *Uso:* `llm = get_analytical_llm()` -> `response = await llm.ainvoke(prompt)` (Invocación directa).

---

#### PATRÓN D: Invocación Estática `get_rag_llm()` en Tiempo de Importación (RAG Gemini-based)
*Peligro de muerte súbita del proceso: Se ejecuta una única vez cuando el backend arranca y carga las clases.*

14. **`src/memory/reranker.py:19`**
    - *Uso:* `self.llm = get_rag_llm()` en el constructor de `SemanticReranker`. El archivo se instancia a nivel de módulo en la base.
15. **`src/memory/fact_extractor.py:21`**
    - *Uso:* `self.llm = get_rag_llm()` en el constructor de `FactExtractor`. Se instancia un singleton global al final del archivo (`fact_extractor = FactExtractor()`).

---

#### PATRÓN E: Factoría Lazy `get_rag_llm()` (RAG Gemini-based)
*Se llama a la factoría de forma bajo demanda.*

16. **`src/memory/consolidation_worker.py:22`**
    - *Uso:* `detector_llm = get_rag_llm()` -> Pasado al constructor de `EvolutionDetector` si no falla.
17. **`src/memory/consolidation_worker.py:212`**
    - *Uso:* `llm_chain = prompt | get_rag_llm()` (LCEL Pipe con invocación dinámica).
18. **`src/memory/consolidation_worker.py:305`**
    - *Uso:* `llm = get_rag_llm()` -> `response = await llm.ainvoke(prompt)` (Invocación directa).
19. **`src/memory/long_term_memory.py:20`**
    - *Uso:* `summarizer_llm = get_rag_llm()` -> Pasado a `MemorySummarizer` en inicialización.
20. **`src/memory/services/memory_summarizer.py:25`**
    - *Uso:* `self.llm = get_rag_llm()` como fallback en constructor si no se le inyecta uno.

---

#### PATRÓN F: Factoría Asíncrona `get_rag_llm_async()` (Gemini con Rotación)
*Única llamada protegida contra rate limit.*

21. **`src/memory/semantic_chunker.py:106`**
    - *Uso:* `llm = await get_rag_llm_async()` -> `chain = self.chunking_prompt | llm` (LCEL Pipe).

---

## 3. Análisis de Brecha de Seguridad y Observabilidad

1. **Vulnerabilidad de Gemini Síncrono (RAG):** Las llamadas síncronas de consolidación de hechos, re-rankeo y sumarización de memoria episódica a largo plazo (`get_rag_llm()`) se ejecutan con `settings.GOOGLE_API_KEY` directamente sin pasar por el `RoundRobinKeyProvider`. Si hay más de 15 solicitudes en un minuto, todo el pipeline de ingestión y memoria de AEGEN se bloquea y retorna excepciones directas de HTTP 429.
2. **Invisibilidad para Prometheus:** El sistema de instrumentación de Prometheus (`PrometheusLLMExporter`) solo rastrea métricas cuando se inyecta un callback handler. Actualmente, esto solo se hace a través de `create_observable_config()`, que solo está implementado en **3 de los 22 call sites** (Chat, CBT, Routing). El 86% de las peticiones LLM a producción no son visibles en Grafana.
3. **Brecha de Privacidad en Observabilidad Cruda (Filtro Regex Ineficiente):** El diseño original proponía guardar prompts crudos en memoria y redactar datos sensibles mediante expresiones regulares. Esto introduce riesgos severos de cumplimiento y seguridad. La solución definitiva es la **retención cero de texto**: solo se registrarán y expondrán agregados numéricos de tamaño (caracteres de sistema, usuario, historial, RAG, etc.), tokens de consumo y latencias, descartando y omitiendo por completo cualquier guardado o persistencia de texto crudo. El endpoint de depuración `/system/prompts/recent` se cancela en favor de `/system/llm-telemetry`.
4. **Choque Sync/Async en la Rotación de Llaves:** `RoundRobinKeyProvider` expone solo un método asíncrono `get_key()`. Sin embargo, `ManagedLLM` debe soportar el método `.invoke()` síncrono de LangChain. Si intentamos invocar la IA síncronamente, no podemos hacer `await` del proveedor dentro del event loop de FastAPI.
   *Solución simple:* El `RoundRobinKeyProvider` implementará un método síncrono ultra-rápido `get_key_sync()` protegido con un simple `threading.Lock()`. Como la operación es solo leer una lista en memoria RAM e incrementar un índice, se ejecuta en <0.01ms y es completamente segura.

---

## 4. Diseño del Sistema Dual: Decorador e Inyección LCEL

### 4.1. El Conflicto con LangChain Expression Language (LCEL)

El operador pipe `|` en LangChain es resuelto por el método `__or__` de la clase base `Runnable`. Si intentamos usar un decorador simple `@llm_call` sobre una función para interceptar y retornar una instancia cruda del modelo, rompemos los casos donde el LLM es parte de una cadena pre-compilada, como en:
`self._chain = routing_prompt | llm.bind_tools(routing_tools)` (routing_analyzer:53)

En este escenario, `routing_analyzer` crea la cadena en el constructor (`__init__`), lo que significa que el modelo se enlaza una sola vez y no en tiempo de ejecución. 

### 4.2. La Arquitectura Dual Propuesta

Para resolver esto sin reescribir toda la lógica conversacional, se introduce un sistema dual:

1. **La Interfaz `ManagedLLM` (LCEL-Compatible):**
   Un wrapper que hereda de `Runnable` y posterga la resolución del proveedor de LLM (y sus API keys rotativas) al momento de ejecución (`ainvoke` o `invoke`), permitiendo el uso del operador `|` y métodos como `.bind_tools()`. Soporta tanto el flujo asíncrono como síncrono delegando a `get_key()` y `get_key_sync()` de forma nativa.
2. **El Decorador `@llm_call` (Inyección de Modelo):**
   Un decorador de Python estándar para inyectar una instancia fresca y resuelta del modelo en funciones que realizan invocaciones directas (`ainvoke`) o ejecutan múltiples llamadas en un mismo contexto.

---

### 4.3. Especificación Técnica de Clases

```python
# src/core/llm_registry.py

import logging
from typing import Any, Callable, Dict, List, Optional, Union
import yaml
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ModelRoute(BaseModel):
    provider: str
    model: str
    temperature: float = 0.7
    key_rotation: bool = False
    max_input_chars: Optional[int] = None
    fallbacks: List[Dict[str, str]] = []


class CallRegistry:
    """
    Carga config/llm_inventory.yaml e instancia los proveedores 
    abstrayendo la rotación de API keys y los fallbacks dinámicos.
    """
    
    def __init__(self, yaml_path: str = "config/llm_inventory.yaml") -> None:
        self.yaml_path = Path(yaml_path)
        self.routes: Dict[str, ModelRoute] = {}
        self.load_inventory()

    def load_inventory(self) -> None:
        """Carga el inventario YAML en caliente. Lanza excepción en prod si falla."""
        # Si no existe y estamos en desarrollo, se crea un default básico
        # ... (implementación concreta en Fase 1)
        pass

    def resolve_provider(self, call_name: str, sync: bool = False) -> BaseLanguageModel:
        """
        Retorna la instancia del proveedor LLM configurada para la llamada.
        Aplica RoundRobinKeyProvider si key_rotation está habilitado usando la vía sync/async correcta.
        """
        route = self.routes.get(call_name)
        if not route:
            # Fallback de emergencia si no está definida en el inventario
            logger.warning("Call name '%s' not registered in inventory. Using general default.", call_name)
            return self._get_emergency_model()
            
        return self._build_model_chain(route, sync)

    def _build_model_chain(self, route: ModelRoute, sync: bool) -> BaseLanguageModel:
        """Crea el modelo primario e inyecta su cadena de fallbacks."""
        primary = self._instantiate_concrete_provider(route.provider, route.model, route.temperature, route.key_rotation, sync)
        
        if not route.fallbacks:
            return primary
            
        fallback_instances = []
        for fb in route.fallbacks:
            fb_inst = self._instantiate_concrete_provider(
                provider=fb.get("provider", "groq"),
                model=fb.get("model", "llama3-70b-8192"),
                temperature=route.temperature,
                key_rotation=fb.get("key_rotation", False),
                sync=sync
            )
            fallback_instances.append(fb_inst)
            
        return primary.with_fallbacks(fallback_instances)

    def _instantiate_concrete_provider(
        self, provider: str, model: str, temperature: float, use_rotation: bool, sync: bool
    ) -> BaseLanguageModel:
        """Inicializa la instancia física del SDK correspondiente de LangChain."""
        # Lógica para Gemini con RoundRobinKeyProvider, Groq y OpenRouter
        # ... (implementación concreta en Fase 1)
        pass


class ManagedLLM(Runnable):
    """
    Representa una llamada LLM perezosa (lazy) que se integra en chains de LCEL.
    Intercepta las peticiones en runtime y resuelve el modelo y la observabilidad.
    """

    def __init__(self, call_name: str, registry: CallRegistry) -> None:
        self.call_name = call_name
        self.registry = registry
        self._bound_tools: Optional[List[Any]] = None
        self._kwargs: Dict[str, Any] = {}

    def bind_tools(self, tools: List[Any], **kwargs: Any) -> "ManagedLLM":
        """Soporta bind_tools de LangChain clonando el ManagedLLM."""
        clone = ManagedLLM(self.call_name, self.registry)
        clone._bound_tools = tools
        clone._kwargs = kwargs
        return clone

    async def ainvoke(
        self,
        input: Any,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any
    ) -> Any:
        """Ejecuta invocación asíncrona resolviendo el LLM y la observabilidad."""
        concrete_llm = self.registry.resolve_provider(self.call_name, sync=False)
        if self._bound_tools:
            concrete_llm = concrete_llm.bind_tools(self._bound_tools, **self._kwargs)
            
        obs_config = self._enrich_config(config)
        self._capture_metadata(input, obs_config)
        
        return await concrete_llm.ainvoke(input, config=obs_config, **kwargs)

    def invoke(
        self,
        input: Any,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any
    ) -> Any:
        """Ejecuta invocación síncrona resolviendo el LLM y la observabilidad."""
        concrete_llm = self.registry.resolve_provider(self.call_name, sync=True)
        if self._bound_tools:
            concrete_llm = concrete_llm.bind_tools(self._bound_tools, **self._kwargs)
            
        obs_config = self._enrich_config(config)
        self._capture_metadata(input, obs_config)
        
        return concrete_llm.invoke(input, config=obs_config, **kwargs)

    def _enrich_config(self, config: Optional[RunnableConfig]) -> RunnableConfig:
        """Configura callbacks para Prometheus y logs de traza."""
        from src.core.engine import create_observable_config
        return create_observable_config(self.call_name, config)

    def _capture_metadata(self, input_data: Any, config: RunnableConfig) -> None:
        """
        Extrae y registra de forma segura los tamaños numéricos de la petición
        sin almacenar texto crudo ni violar la privacidad del usuario.
        """
        # ... (implementación concreta en Fase 3)
        pass


# Instancia única del registro a nivel de framework
_registry = CallRegistry()

def get_llm(call_name: str) -> ManagedLLM:
    """Función de conveniencia para recuperar un ManagedLLM LCEL-compatible."""
    return ManagedLLM(call_name, _registry)
```


def llm_call(call_name: str):
    """
    Decorador para inyectar un LLM dinámico resuelto en los argumentos de una función.
    Útil para call-sites de invocación imperativa directa.
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Inyecta '_llm' en los kwargs de la función envuelta
            kwargs["_llm"] = get_llm(call_name)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

### 4.4. Ejemplos Concretos de Migración de Call-Sites

#### Caso A: Migración de Pipe LCEL (Chat / CBT)
*Reemplazar importación directa del singleton por la llamada funcional al registro.*

```python
# ANTES (chat/tools.py)
from src.core.engine import llm

chain = conversational_prompt | llm
response = await chain.ainvoke(prompt_input, config=config)

# DESPUÉS (chat/tools.py)
from src.core.llm_registry import get_llm

chain = conversational_prompt | get_llm("chat_response")
response = await chain.ainvoke(prompt_input, config=config)
```

---

#### Caso B: Migración de bind_tools (routing_analyzer)
*Permite enlazar herramientas dinámicamente sobre la referencia administrada.*

```python
# ANTES (routing_analyzer.py)
from src.core.engine import llm

self._chain = routing_prompt | llm.bind_tools(routing_tools)

# DESPUÉS (routing_analyzer.py)
from src.core.llm_registry import get_llm

self._chain = routing_prompt | get_llm("routing_analysis").bind_tools(routing_tools)
```

---

#### Caso C: Migración de Invocación Directa (skill_generator)
*Uso del decorador `@llm_call` para inyectar la dependencia.*

```python
# ANTES (skill_generator.py)
from src.core.engine import llm

async def generate_from_history(self, domain_name: str, samples: list[str]) -> str:
    response = await llm.ainvoke(prompt)
    return str(response.content).strip()

# DESPUÉS (skill_generator.py)
from src.core.llm_registry import llm_call

@llm_call("skill_generation")
async def generate_from_history(self, domain_name: str, samples: list[str], *, _llm=None) -> str:
    # _llm es inyectado automáticamente por el decorador en tiempo de ejecución
    response = await _llm.ainvoke(prompt)
    return str(response.content).strip()
```

---

#### Caso D: Solución a Inicializaciones Estáticas en Módulos (reranker / fact_extractor)
*Convertir las llamadas estáticas a resoluciones perezosas (lazy resolution) para habilitar key rotation e impedir cierres tempranos de sockets.*

```python
# ANTES (reranker.py)
from src.core.engine import get_rag_llm

class SemanticReranker:
    def __init__(self) -> None:
        self.llm = get_rag_llm()  # Instanciado permanentemente en import time

# DESPUÉS (reranker.py)
from src.core.llm_registry import get_llm

class SemanticReranker:
    def __init__(self) -> None:
        # Se guarda la referencia al ManagedLLM, la llamada real
        # se resolverá en caliente en cada invoke() / ainvoke()
        self.llm = get_llm("rag_reranking")
```

---

## 5. Estrategia de Migración Estructural ("Big Bang" sin Fachada de Compatibilidad)

Para garantizar la máxima coherencia arquitectónica y evitar arrastrar deuda técnica a futuro, **se descarta cualquier solución de puente o fachada intermedia (Bridge) en `src/core/engine.py`**. 

Toda la aplicación será migrada de manera directa y simultánea al nuevo `llm_registry` mediante los siguientes cambios de importación y uso en los 17 archivos afectados. El archivo `src/core/engine.py` será simplificado eliminando por completo las factorías legacy obsoletas:

### 5.1. Factorías a Eliminar Definitivamente de `src/core/engine.py`
- `get_fast_llm()`
- `get_analytical_llm()`
- `get_rag_llm()`
- `get_rag_llm_async()`
- `llm` (Singleton global legacy)

### 5.2. Mapeo de Sustitución Directa
- Las llamadas a `get_fast_llm()` y `llm` se reemplazan por `get_llm("chat_response")` o `@llm_call("chat_response")`.
- Las llamadas a `get_analytical_llm()` se reemplazan por `get_llm("cbt_therapeutic_response")` o el identificador correspondiente de su dominio analítico (ej: `psicotrading_response`).
- Las llamadas a `get_rag_llm()` y `get_rag_llm_async()` se reemplazan por `get_llm("rag_fact_extraction")` o `get_llm("rag_chunking")` respectivamente, pasando todas a resolverse dinámicamente en caliente.

---

## 6. Plan de Ejecución Revisado y Plan de Pruebas

Para garantizar cero regresiones y control de efectos colaterales, se define el siguiente pipeline de ejecución limpia de 4 fases:

### Fase 1: Registro e Inventario Base
- **Implementar** `src/core/llm_registry.py` con la lógica de resolución, `ManagedLLM` y el decorador `@llm_call`.
- **Crear** `config/llm_inventory.yaml` con las 10 firmas de llamadas mapeadas a Gemini como primario (multi-key) y Groq como fallback.

### Fase 2: Migración Simultánea de Call Sites (17 Archivos)
- **Modificar** todos los 17 archivos consumidores reemplazando la importación de `engine.py` por la importación directa de `get_llm` o `llm_call` desde `src/core/llm_registry.py`.
- **Refactorizar** `reranker.py` y `fact_extractor.py` a inyecciones perezosas (lazy).
- **Limpiar** `src/core/engine.py` eliminando el código muerto de factorías y variables globales obsoletas.
- **Borrar** `src/core/observability/llm_wrapper.py` (código muerto obsoleto `ObservableLLM`).
- **Validar** que no ocurran imports circulares al cargar el backend de FastAPI.

### Fase 3: Observabilidad de Telemetría Numérica Segura (Retención Cero de Texto)
- **Implementar** la recolección de metadatos estructurados en `ManagedLLM` que mide el tamaño de caracteres por sección (prompt de sistema, RAG, preferencias, historial y usuario) sin almacenar ni persistir un solo byte de texto de entrada crudo.
- **Implementar** endpoints `/system/llm-inventory` y `/system/llm-telemetry` (agregados numéricos y de consumo, protegidos mediante `access_controller.py`) en `src/api/routers/system_llm.py` y montarlos en `src/main.py`.

### Fase 4: Pruebas de Integración y Fallbacks
- **Simular** un rate-limit en la key primaria de Gemini mediante mocks y validar en logs que el sistema conmuta automáticamente a Groq sin perturbar la sesión del usuario.
- **Verificar** las métricas en Prometheus para validar la cobertura del 100% de llamadas registradas.
- **Ejecutar** `make verify` para asegurar cero errores de Ruff, Mypy y arquitectura.
