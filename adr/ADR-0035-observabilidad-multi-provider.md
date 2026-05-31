# ADR-0035 - Observabilidad Multi-Provider LLM y Dashboard de Telemetría

- **Fecha:** 2026-05-29
- **Estado:** Aceptado
- **Autor:** MAGI AI (auditoría automatizada)
- **ADR Relacionado:** ADR-0027 (Inteligencia Asimétrica), ADR-0025 (Observabilidad v0.8.5)

## Contexto

La auditoría del codebase (2026-05-29) reveló que el sistema de observabilidad tiene fallos estructurales que hacen invisible la mayoría del tráfico LLM real:

### Fallos actuales

**`metrics_processor.py:13-22`** — detección de provider:

```python
def extract_model_info(serialized: dict[str, Any]) -> tuple[str, str]:
    provider = "unknown"
    model = "unknown"
    if serialized.get("id", [])[-1] == "ChatGoogleGenerativeAI":
        provider = "google"
        model = serialized.get("kwargs", {}).get("model", "gemini-pro")
    return provider, model
```

Según ADR-0027, la arquitectura real usa:
- **Groq (`ChatGroq`)** → Chat, routing, fast LLM (primario: ~80% de llamadas conversacionales)
- **OpenRouter (`ChatOpenAI`)** → Analytical LLM fallback (~15% en fallos de Groq)
- **Google Gemini (`ChatGoogleGenerativeAI`)** → RAG, embeddings, consolidación (~5% conversacional, 100% background)

El código actual solo detecta Google. **~80-95% de las llamadas LLM producen `provider="unknown"`**, haciendo las 5 métricas Prometheus (`llm_calls_total`, `llm_tokens_total`, etc.) prácticamente inútiles para auditoría real.

**Endpoints REST con datos hardcodeados:**
- `/system/llm/metrics/summary` retorna `latency: 0.0` y `timestamp` fijo.
- Sin alertas automáticas cuando un provider falla.
- Sin estimación de costos para Groq ni OpenRouter.

**Sin dashboard:** Solo existe el endpoint `/metrics` de Prometheus. No hay Grafana ni equivalente configurado.

### Contexto adicional: ¿por qué Groq cae al fallback?

Los logs de producción muestran llamadas a `minimax/minimax-m2.5:free` (OpenRouter) para CBT, que debería usar Groq como primario. Esto indica que Groq está fallando periódicamente en producción. Sin telemetría de provider, es imposible cuantificar la frecuencia o la causa (rate limit, timeout, error 503, etc.).

## Decisión

### 1. Detección multi-provider en `metrics_processor.py`

Reemplazar la detección monolítica por un sistema que combina mapeo de clase con inspección de `base_url`:

```python
from typing import Any

# Mapeo directo para providers con clase única
_PROVIDER_BY_CLASS = {
    "ChatGroq": "groq",
    "ChatGoogleGenerativeAI": "google",
    "ChatAnthropic": "anthropic",
}

# Dominios para distinguir providers que comparten clase (ChatOpenAI)
_OPENROUTER_DOMAINS = {"openrouter.ai"}
_AZURE_DOMAINS = {"openai.azure.com"}

def extract_model_info(serialized: dict[str, Any]) -> tuple[str, str]:
    """Extrae provider y modelo del LLM serializado."""
    class_name = (serialized.get("id") or ["unknown"])[-1]
    kwargs = serialized.get("kwargs", {})

    # Providers con clase única
    if class_name in _PROVIDER_BY_CLASS:
        provider = _PROVIDER_BY_CLASS[class_name]
    elif class_name == "ChatOpenAI":
        # ChatOpenAI es usado por OpenAI real, OpenRouter, Azure, Together, etc.
        # Distinguir por base_url
        base_url = str(
            kwargs.get("openai_api_base") or kwargs.get("base_url", "")
        )
        if any(domain in base_url for domain in _OPENROUTER_DOMAINS):
            provider = "openrouter"
        elif any(domain in base_url for domain in _AZURE_DOMAINS):
            provider = "azure_openai"
        else:
            provider = "openai"
    else:
        provider = "unknown"

    model = kwargs.get("model_name") or kwargs.get("model", "unknown")
    return provider, model
```

**Importante:** `ChatOpenAI` **no** se mapea directamente a `openrouter`. Múltiples providers (OpenAI real, OpenRouter, Azure OpenAI, Together AI) usan la interfaz `ChatOpenAI` de LangChain. La distinción se hace inspeccionando `base_url` en los kwargs del objeto serializado.

### 2. Estimación de costos por provider

Añadir tabla de precios aproximados (USD por 1K tokens) en `metrics_processor.py`:

```python
_COST_PER_1K_TOKENS = {
    "groq": {
        "input": 0.0,    # Groq free tier
        "output": 0.0,
    },
    "google": {
        "input": 0.000075,   # Gemini 2.5 Flash
        "output": 0.0003,
    },
    "openrouter": {
        "input": 0.0,    # minimax-m2.5:free es gratuito
        "output": 0.0,
    },
}
```

Los costos se actualizan manualmente en este archivo cuando cambian los modelos. Para modelos de pago futuros (GPT-4o, Claude via OpenRouter), se añaden entradas aquí.

### 3. Corregir endpoints REST de métricas

`/system/llm/metrics/summary` debe leer datos reales de los contadores Prometheus en memoria (no hardcoded):

- `llm_calls_total` por provider+model
- `llm_latency_seconds` percentil 50/95/99
- `llm_tokens_total` por tipo (input/output)
- `llm_cost_total` acumulado

Si el registro Prometheus está vacío (arranque fresco), retornar ceros reales con `timestamp` actual.

### 4. Alertas en AdminNotificator (integrar con ADR-0027)

El `AdminNotificator` ya existe (`src/api/services/admin_notifier.py` o similar) y escucha `system.llm_failure`. Extender para:

- **Fallback a OpenRouter**: Cuando Groq falla y se activa el fallback, publicar `system.llm_fallback` con provider origen y destino.
- **Tasa de errores alta**: Si en los últimos 10 minutos >20% de llamadas a un provider retornan error, publicar alerta.
- **Latencia anómala**: Si la latencia p95 de un provider supera 5s, publicar alerta.

Estas alertas llegan al `ADMIN_CHAT_ID` por Telegram (ya definido en ADR-0027).

### 5. Dashboard mínimo viable

Configurar un dashboard Grafana con 4 paneles clave, conectado al endpoint `/metrics`:

1. **Calls por provider/model** (últimas 24h) — detectar si Groq está fallando
2. **Latencia p50/p95 por provider** — identificar lentitud sistémica
3. **Tokens consumidos por sesión** — detectar sesiones anómalas (prompt injection, loops)
4. **Fallback rate** — porcentaje de llamadas que fueron al fallback vs primario

Si Grafana tiene fricción para el deploy en GCP, alternativa: endpoint `/system/llm/dashboard` que retorna HTML con SVG de las métricas (sin dependencias externas).

### 6. RoundRobinKeyProvider para rotación de API Keys de Google (A.10)

Para maximizar los rate limits gratuitos de Google AI Studio con múltiples cuentas, se crea un `RoundRobinKeyProvider` que encapsula la rotación de llaves sin que el resto del sistema sepa cuántas hay:

```python
# src/core/providers/round_robin_key.py
import asyncio
import os
from typing import Self


class RoundRobinKeyProvider:
    """
    Proporciona API keys de Google en rotación round-robin.

    Lee GEMINI_API_KEY_1, GEMINI_API_KEY_2, ..., GEMINI_API_KEY_N
    desde las variables de entorno y rota en cada solicitud.

    Si una key falla por rate limit (HTTP 429), la marca como
    agotada por 60 segundos y pasa a la siguiente automáticamente.
    """

    def __init__(self) -> None:
        self._keys: list[str] = []
        self._index: int = 0
        self._cooldowns: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._discover_keys()

    def _discover_keys(self) -> None:
        i = 1
        while True:
            key = os.environ.get(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            self._keys.append(key)
            i += 1
        # Fallback a la key única tradicional
        if not self._keys:
            single = os.environ.get("GEMINI_API_KEY")
            if single:
                self._keys.append(single)

    async def get_key(self) -> str | None:
        if not self._keys:
            return None
        async with self._lock:
            now = asyncio.get_running_loop().time()
            for _ in range(len(self._keys)):
                key = self._keys[self._index]
                self._index = (self._index + 1) % len(self._keys)
                cooldown_until = self._cooldowns.get(key, 0)
                if now >= cooldown_until:
                    return key
            # Todas en cooldown — devolver la primera igual
            self._index = (self._index + 1) % len(self._keys)
            return self._keys[self._index]

    async def mark_rate_limited(self, key: str) -> None:
        async with self._lock:
            self._cooldowns[key] = asyncio.get_running_loop().time() + 60
```

El provider se instancia una vez en `src/core/dependencies.py` y `engine.py` lo consulta para obtener la key antes de instanciar `ChatGoogleGenerativeAI`. El resto de AEGEN no sabe cuántas llaves hay ni cuál está activa.

**Configuración en `.env`:**
```bash
GEMINI_API_KEY_1=AIza...
GEMINI_API_KEY_2=AIza...
GEMINI_API_KEY_3=AIza...
```

Si solo hay una key (`GEMINI_API_KEY` tradicional), el provider funciona idéntico al comportamiento actual.

## Consecuencias

### Positivas
- **Visibilidad real:** El 80-95% del tráfico LLM que era invisible pasa a ser observable.
- **Diagnóstico de Groq:** Se puede cuantificar cuántas veces Groq falla y por qué (via los labels del evento de fallback).
- **Alertas proactivas:** El administrador sabe en tiempo real si un provider está degradado, antes de que los usuarios reporten problemas.
- **Base para A.10:** Los datos de observabilidad informan la decisión de migrar o no `REASONING_MODEL` a Gemini.

### Negativas / Riesgos
- **Tabla de costos manual:** Los precios de los modelos cambian con frecuencia. Si no se actualiza la tabla, los costos estimados son incorrectos. Mitigación: documentar en la tabla el `last_updated` y disparar una alerta si llevan >90 días sin actualización. Alternativa futura: migrar a archivo de configuración externo (`config/llm_costs.json`) o usar `litellm.cost_per_token()`.
- **Overhead de colección:** La instrumentación LangChain via callbacks añade <1ms por llamada. Aceptable.
- **Nuevos providers no mapeados:** Si se añade un provider LLM nuevo (ej. Anthropic directo, Cohere), aparecerá como `provider="unknown"` hasta que se añada al `_PROVIDER_BY_CLASS`. Mitigación: test unitario que verifica que ninguna llamada LLM en las últimas 24h tiene `provider="unknown"`.
