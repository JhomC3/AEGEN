# Observabilidad Multi-Provider LLM — Plan de Implementación (C.5)

> **For Claude:** REQUIRED SUB-SKILL: Use the executing-plans skill to implement this plan task-by-task.

**Goal:** Hacer visible el 80-95% del tráfico LLM (Groq + OpenRouter) que actualmente produce `provider="unknown"`. Añadir estimación de costos para todos los providers, corregir endpoint de métricas con valores hardcodeados, y establecer alertas de fallback.

**Architecture:** Ampliar `extract_model_info` en `metrics_processor.py` con detección multi-clase. Añadir tabla de costos por provider. Integrar evento `system.llm_fallback` cuando Groq cae a OpenRouter. Opcionalmente añadir endpoint HTML de dashboard sin dependencias externas.

**Tech Stack:** Python 3.13, pytest, LangChain (ChatGroq, ChatOpenAI, ChatGoogleGenerativeAI), Prometheus, structlog, `make verify`

**ADR de referencia:** ADR-0035 (`adr/ADR-0035-observabilidad-multi-provider.md`)

---

## Task 1: Ampliar detección de provider en `metrics_processor.py`

**Files:**
- Modify: `src/core/observability/metrics_processor.py:13-22`
- Test: `tests/unit/core/test_metrics_processor.py` (crear nuevo)

**Step 1: Escribir tests que fallan**

```python
"""Tests de detección de provider LLM en metrics_processor."""
import pytest
from src.core.observability.metrics_processor import extract_model_info


@pytest.mark.parametrize("serialized,expected_provider,expected_model", [
    # Google Generative AI (ya funciona)
    (
        {"id": ["langchain_google_genai", "ChatGoogleGenerativeAI"],
         "kwargs": {"model": "gemini-2.5-flash"}},
        "google",
        "gemini-2.5-flash",
    ),
    # Groq (actualmente produce "unknown")
    (
        {"id": ["langchain_groq", "ChatGroq"],
         "kwargs": {"model_name": "openai/gpt-oss-120b"}},
        "groq",
        "openai/gpt-oss-120b",
    ),
    # OpenRouter vía interfaz OpenAI (actualmente produce "unknown")
    (
        {"id": ["langchain_openai", "ChatOpenAI"],
         "kwargs": {"model_name": "minimax/minimax-m2.5:free",
                    "openai_api_base": "https://openrouter.ai/api/v1"}},
        "openrouter",
        "minimax/minimax-m2.5:free",
    ),
    # OpenAI real (distinción por base_url)
    (
        {"id": ["langchain_openai", "ChatOpenAI"],
         "kwargs": {"model_name": "gpt-4o",
                    "openai_api_base": "https://api.openai.com/v1"}},
        "openai",
        "gpt-4o",
    ),
    # Azure OpenAI (distinción por base_url)
    (
        {"id": ["langchain_openai", "ChatOpenAI"],
         "kwargs": {"model_name": "gpt-4o",
                    "openai_api_base": "https://myresource.openai.azure.com"}},
        "azure_openai",
        "gpt-4o",
    ),
    # ChatOpenAI sin base_url → OpenAI por defecto
    (
        {"id": ["langchain_openai", "ChatOpenAI"],
         "kwargs": {"model_name": "gpt-4o-mini"}},
        "openai",
        "gpt-4o-mini",
    ),
    # Unknown (clase no reconocida)
    (
        {"id": ["langchain_unknown", "SomeRandomLLM"],
         "kwargs": {}},
        "unknown",
        "unknown",
    ),
])
def test_extract_model_info(serialized, expected_provider, expected_model):
    provider, model = extract_model_info(serialized)
    assert provider == expected_provider, f"Provider: got {provider!r}, expected {expected_provider!r}"
    assert model == expected_model, f"Model: got {model!r}, expected {expected_model!r}"
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/core/test_metrics_processor.py -v
```

Esperado: FAIL en casos de Groq y OpenRouter.

**Step 3: Implementar detección multi-provider**

Reemplazar `extract_model_info` en `src/core/observability/metrics_processor.py`:

```python
_PROVIDER_BY_CLASS = {
    "ChatGoogleGenerativeAI": "google",
    "ChatGroq": "groq",
    "ChatAnthropic": "anthropic",
}

_OPENROUTER_DOMAINS = {"openrouter.ai"}
_AZURE_DOMAINS = {"openai.azure.com"}

def extract_model_info(serialized: dict[str, Any]) -> tuple[str, str]:
    """Extrae provider y modelo del LLM serializado."""
    class_name = (serialized.get("id") or ["unknown"])[-1]
    kwargs = serialized.get("kwargs", {})

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

**Step 4: Ejecutar tests**

```bash
pytest tests/unit/core/test_metrics_processor.py -v
```

Esperado: PASS en todos.

**Step 5: `make verify`**

```bash
make verify
```

Esperado: 0 errores.

**Step 6: Commit**

```bash
git add src/core/observability/metrics_processor.py tests/unit/core/test_metrics_processor.py
git commit -m "fix(observability): detección multi-provider en extract_model_info (ADR-0035)"
```

---

## Task 2: Añadir estimación de costos por provider

**Files:**
- Modify: `src/core/observability/metrics_processor.py`

**Step 1: Añadir tabla de costos y función de estimación**

En `metrics_processor.py`, añadir tras `_OPENROUTER_BASE_URLS`:

```python
# Costos por 1K tokens en USD. Actualizar cuando cambien los modelos.
# last_updated: 2026-05-29
_COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "groq": {"input": 0.0, "output": 0.0},       # Free tier
    "google": {"input": 0.000075, "output": 0.0003},  # Gemini 2.5 Flash
    "openrouter": {"input": 0.0, "output": 0.0},  # minimax-m2.5:free
    "openai": {"input": 0.0025, "output": 0.01},  # GPT-4o (referencia)
    "anthropic": {"input": 0.003, "output": 0.015},  # Claude 3.5 Sonnet (referencia)
    "unknown": {"input": 0.0, "output": 0.0},
}

def estimate_cost_usd(
    provider: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float:
    """Estima el costo en USD basado en el provider y tokens consumidos."""
    costs = _COST_PER_1K_TOKENS.get(provider, _COST_PER_1K_TOKENS["unknown"])
    input_cost = ((input_tokens or 0) / 1000) * costs["input"]
    output_cost = ((output_tokens or 0) / 1000) * costs["output"]
    return round(input_cost + output_cost, 8)
```

**Step 2: Integrar `estimate_cost_usd` en `update_metrics_from_result`**

En `update_metrics_from_result`, al final antes del return:

```python
    # Estimar costo después de conocer tokens
    if metrics.input_tokens is not None or metrics.output_tokens is not None:
        metrics.estimated_cost_usd = estimate_cost_usd(
            metrics.provider,
            metrics.input_tokens,
            metrics.output_tokens,
        )
```

**Step 3: Escribir test de estimación de costos**

En `tests/unit/core/test_metrics_processor.py`, añadir:

```python
from src.core.observability.metrics_processor import estimate_cost_usd

def test_estimate_cost_groq_is_zero():
    """Groq free tier no tiene costo."""
    cost = estimate_cost_usd("groq", input_tokens=1000, output_tokens=500)
    assert cost == 0.0

def test_estimate_cost_google_gemini():
    """Gemini Flash tiene costo por tokens."""
    cost = estimate_cost_usd("google", input_tokens=1000, output_tokens=1000)
    # 1K input * 0.000075 + 1K output * 0.0003 = 0.000375
    assert abs(cost - 0.000375) < 1e-8

def test_estimate_cost_unknown_provider_is_zero():
    """Provider desconocido no debe generar costo para no distorsionar métricas."""
    cost = estimate_cost_usd("unknown", input_tokens=9999, output_tokens=9999)
    assert cost == 0.0
```

**Step 4: Ejecutar tests**

```bash
pytest tests/unit/core/test_metrics_processor.py -v
```

Esperado: PASS en todos.

**Step 5: `make verify`**

```bash
make verify
```

**Step 6: Commit**

```bash
git add src/core/observability/metrics_processor.py tests/unit/core/test_metrics_processor.py
git commit -m "feat(observability): estimación de costos por provider LLM (ADR-0035)"
```

---

## Task 3: Corregir endpoint `/system/llm/metrics/summary`

**Files:**
- Modify: `src/api/routers/` — buscar el router que expone el endpoint
- Test: `tests/unit/api/test_system_endpoints.py` (crear o añadir)

**Step 1: Encontrar el archivo del endpoint**

```bash
grep -r "llm/metrics/summary" src/ --include="*.py" -l
```

Registrar el archivo encontrado. Probablemente `src/api/routers/status.py` o `llm_metrics.py`.

**Step 2: Leer el endpoint actual**

Leer el archivo encontrado. Identificar los valores hardcodeados (`latency: 0.0`, timestamp fijo).

**Step 3: Escribir test del comportamiento esperado**

```python
"""Tests del endpoint de métricas LLM."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


def test_llm_metrics_summary_returns_real_timestamp(client: TestClient):
    """El endpoint debe retornar un timestamp actual, no hardcodeado."""
    from datetime import datetime, timezone
    before = datetime.now(timezone.utc).timestamp()
    response = client.get("/system/llm/metrics/summary")
    after = datetime.now(timezone.utc).timestamp()

    assert response.status_code == 200
    data = response.json()
    # El timestamp retornado debe estar entre before y after
    ts = data.get("generated_at") or data.get("timestamp")
    assert ts is not None, "El endpoint debe incluir un campo de timestamp"


def test_llm_metrics_summary_no_hardcoded_zero_latency(client: TestClient):
    """La latencia no debe ser siempre 0.0 si hay llamadas registradas."""
    response = client.get("/system/llm/metrics/summary")
    assert response.status_code == 200
    # Al menos verificamos que el campo existe y tiene el tipo correcto
    data = response.json()
    assert "latency" in data or "avg_latency_ms" in data, (
        "El endpoint debe incluir campo de latencia"
    )
```

**Step 4: Corregir el endpoint**

En el archivo del endpoint, reemplazar valores hardcodeados por:

```python
from datetime import datetime, timezone

# Timestamp real
generated_at = datetime.now(timezone.utc).isoformat()

# Latencia desde métricas Prometheus (o 0.0 si no hay datos aún)
# Ejemplo de lectura del registro Prometheus:
from prometheus_client import REGISTRY
llm_latency_samples = list(REGISTRY.get_sample_value(
    "llm_latency_seconds_sum"
) or [])
# Si no hay datos, retornar 0.0 explícitamente con una nota
```

Si la integración con Prometheus es compleja, un mínimo correcto es:

```python
return {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "note": "No hay llamadas registradas desde el último reinicio." if not calls else None,
    "avg_latency_ms": 0.0,  # Se actualizará cuando haya datos reales
    ...
}
```

**Step 5: Ejecutar tests del endpoint**

```bash
pytest tests/unit/api/test_system_endpoints.py -v
```

Esperado: PASS.

**Step 6: `make verify`**

```bash
make verify
```

**Step 7: Commit**

```bash
git add src/api/routers/<archivo>.py tests/unit/api/test_system_endpoints.py
git commit -m "fix(api): corregir valores hardcodeados en /system/llm/metrics/summary (ADR-0035)"
```

---

## Task 4: Evento `system.llm_fallback` en `engine.py`

**Files:**
- Modify: `src/core/engine.py`
- Test: `tests/unit/core/test_engine_fallback.py` (crear nuevo)

**Step 1: Leer `engine.py` completo**

Leer `src/core/engine.py` para entender la estructura actual de fallback en `get_fast_llm()` y `get_analytical_llm()`.

**Step 2: Escribir test del evento de fallback**

```python
"""Tests de publicación de evento de fallback LLM."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_llm_fallback_publishes_event_when_groq_fails():
    """Cuando Groq falla y se activa el fallback a OpenRouter, debe publicarse system.llm_fallback."""
    # El test específico depende de cómo está estructurado engine.py
    # Este es el patrón esperado después de refactorizar
    pass  # Implementar tras leer engine.py en Step 1
```

**Step 3: Añadir publicación de evento en el punto de fallback**

En `engine.py`, donde ocurre el fallback de Groq a OpenRouter, añadir:

```python
# Importar el event bus
from src.core.bus import get_event_bus

# En el punto de fallback:
async def _publish_fallback_event(primary: str, fallback: str, reason: str) -> None:
    try:
        bus = get_event_bus()
        await bus.publish("system.llm_fallback", {
            "primary_provider": primary,
            "fallback_provider": fallback,
            "reason": reason,
            "timestamp": time.time(),
        })
    except Exception:
        pass  # No fallar si el bus no está disponible
```

**Step 4: `make verify`**

```bash
make verify
```

**Step 5: Commit**

```bash
git add src/core/engine.py tests/unit/core/test_engine_fallback.py
git commit -m "feat(engine): publicar evento system.llm_fallback en activación de fallback (ADR-0035)"
```

---

## Task 5: Test final de regresión

**Step 1: Ejecutar suite completa**

```bash
make verify
```

Esperado: 0 errores, todos los tests pasan.

**Step 2: Verificar que Groq ya aparece en logs como provider detectado**

Revisar en logs de desarrollo que las llamadas a Groq ya no producen `provider="unknown"`. Si el sistema no está corriendo localmente, verificar en tests unitarios.

---

## Verificación de aceptación

1. `make verify` pasa al 100%.
2. `extract_model_info({"id": ["langchain_groq", "ChatGroq"], "kwargs": {"model_name": "openai/gpt-oss-120b"}})` retorna `("groq", "openai/gpt-oss-120b")`.
3. `/system/llm/metrics/summary` retorna timestamp actual (no hardcodeado).
4. Los eventos `system.llm_fallback` aparecen en logs cuando Groq falla.
