# Evaluación Forense: ADRs 0034-0038 y Planes de Implementación v0.9.0

- **Fecha:** 2026-05-29
- **Tipo:** Auditoría técnica crítica
- **Alcance:** 5 ADRs + 3 planes de implementación creados en la sesión de planificación
- **Metodología:** Revisión cruzada de decisiones documentadas vs. código real del codebase

---

## Resumen Ejecutivo

La documentación producida es **sólida en diagnóstico** pero presenta **17 gaps técnicos** y **8 decisiones subóptimas** que deben corregirse antes de implementación. Los problemas se clasifican en:

| Categoría | Cantidad | Severidad |
|---|---|---|
| Bugs en pseudocódigo de ADRs | 5 | Alta |
| Decisiones que contradicen el código real | 4 | Alta |
| APIs inexistentes asumidas como existentes | 3 | Media |
| Patrones deprecated en Python 3.13 | 3 | Media |
| Gaps de diseño conceptual | 6 | Media |
| Alternativas vanguardistas no consideradas | 4 | Baja |

**Veredicto general:** Los ADRs identifican correctamente los problemas pero proponen soluciones con errores de implementación que generarían bugs en producción si se implementan tal cual. Se requieren correcciones antes de ejecutar los planes.

---

## 1. ADR-0034: Graph-RAG Data-Driven

### 1.1 Gap crítico: `_check_edges_exist` solo verifica origen, ignora destino

**Problema:** La consulta SQL propuesta es:
```sql
SELECT 1 FROM memory_edges WHERE origen_id IN (:ids) LIMIT 1
```

Esto solo detecta aristas donde los fragmentos recuperados son el **origen** de la relación. Si un fragmento es el **destino** (ej. un fact de "ansiedad" que fue conectado como destino de un fact de "déficit calórico"), la consulta retorna vacío y el Graph-RAG no se activa.

**Impacto:** ~50% de las aristas relevantes se pierden. El grafo es bidireccional en la práctica (las relaciones causales pueden leerse en ambos sentidos), pero la verificación es unidireccional.

**Corrección:**
```sql
SELECT 1 FROM memory_edges
WHERE origen_id IN (:ids) OR destino_id IN (:ids)
LIMIT 1
```

**Justificación:** El costo sigue siendo <5ms con el índice `idx_edges_origen` + `idx_edges_destino` ya definidos en ADR-0033. No hay penalización de latencia.

### 1.2 Sobre-ingeniería: El parche de crisis en `_is_casual_message`

**Problema identificado (en mi evaluación previa):** Critiqué que `len(text.split()) <= 2` clasificaba "estoy mal" como casual y propuse una lista `_NON_CASUAL_KEYWORDS`.

**Evaluación crítica posterior:** Ese análisis fue **incorrecto**. El regex `_CASUAL_PATTERN` usa anclas `^...$`. Un mensaje de 2+ palabras como "estoy mal" o "ayuda" **nunca** matchea el regex. El bug de `len() <= 2` se corregía simplemente eliminando ese umbral. La lista de exclusión es código redundante que añade complejidad ciclomática (`C90`) sin valor lógico.

**Corrección aplicada:** Se eliminó tanto el umbral `len() <= 2` como `_NON_CASUAL_KEYWORDS`. La función `_is_casual_message` quedó en su forma más simple y elegante:

```python
def _is_casual_message(text: str) -> bool:
    normalized = unicodedata.normalize("NFC", text)
    return bool(_CASUAL_PATTERN.match(normalized))
```

**Lección:** En AEGEN, pragmatismo > sobre-ingeniería. La solución más simple (regex anclado) resuelve tanto el caso casual como el de crisis sin necesidad de listas de exclusión.

### 1.3 Gap técnico: Regex no maneja emojis correctamente

**Problema:** El patrón `_CASUAL_PATTERNS` incluye emojis como `👋`, `🙋`, `👍`, `✅`. Sin embargo, `re.match` con `re.UNICODE` no garantiza matching correcto de emojis compuestos (ej. 👋🏽 = waving hand + skin tone modifier). Un mensaje como "👋🏽" no matchearía el patrón `👋`.

**Corrección:** Normalizar el texto antes del match:
```python
import unicodedata

def _is_casual_message(text: str) -> bool:
    normalized = unicodedata.normalize("NFC", text)
    return bool(_CASUAL_PATTERN.match(normalized))
```

### 1.4 Decisión subóptima: Test de sincronización con AST parsing

**Problema:** El test propuesto en el plan usa `ast.parse()` para extraer valores del `Literal` en `routing_tools.py`. Esto es frágil: cualquier cambio en el formato del archivo (comentarios, reordenamiento) puede romper el parser AST.

**Alternativa superior:** Usar `typing.get_args()` directamente sobre el tool importado:

```python
from typing import get_args
import inspect

def test_routing_tools_literal_covers_all_intent_types():
    from src.agents.orchestrator.routing.routing_tools import route_user_message
    sig = inspect.signature(route_user_message.func)  # .func para @tool
    intent_param = sig.parameters["intent"]
    literal_values = set(get_args(intent_param.annotation))
    enum_values = {e.value for e in IntentType}
    assert literal_values == enum_values
```

**Justificación:** `get_args()` es la API oficial de Python para inspeccionar tipos genéricos. Es más robusta que AST parsing y no depende del formato del archivo fuente.

### 1.5 Gap de diseño: Sin estrategia de `max_hops` adaptativo

**Problema:** El ADR menciona en "Riesgos" la mitigación de `max_hops=1` para intents no analíticos, pero no lo incluye en la **Decisión**. El código propuesto siempre usa `max_hops=2`.

**Corrección:** Añadir lógica adaptativa en la Decisión:

```python
_ANALYTICAL_INTENTS = {
    IntentType.INFORMATION_REQUEST,
    IntentType.PLANNING,
    IntentType.DOCUMENT_CREATION,
    IntentType.FILE_ANALYSIS,
}

max_hops = 2 if intent in _ANALYTICAL_INTENTS else 1
```

**Justificación:** Esto preserva la optimización de latencia para intents simples mientras permite exploración profunda cuando el usuario hace preguntas analíticas. A diferencia de los strings hardcodeados originales, estos valores SÍ existen en `IntentType` y el test de sincronización los validaría.

---

## 2. ADR-0035: Observabilidad Multi-Provider

### 2.1 Bug en la Decisión: `ChatOpenAI` → `openrouter` es incorrecto

**Problema:** El `_PROVIDER_MAP` propuesto mapea:
```python
"ChatOpenAI": "openrouter"
```

Esto es **falso**. `ChatOpenAI` es la clase base de LangChain para cualquier provider compatible con la API de OpenAI. Puede ser:
- OpenAI real (`api.openai.com`)
- OpenRouter (`openrouter.ai/api/v1`)
- Azure OpenAI (`*.openai.azure.com`)
- Together AI, Fireworks, etc.

El ADR identifica este problema en la sección de "Riesgos" pero la **Decisión principal** ya contiene el bug.

**Corrección:** La Decisión debe incluir la lógica de `base_url` desde el inicio:

```python
def extract_model_info(serialized: dict[str, Any]) -> tuple[str, str]:
    class_name = (serialized.get("id") or ["unknown"])[-1]
    kwargs = serialized.get("kwargs", {})

    if class_name == "ChatGroq":
        provider = "groq"
    elif class_name == "ChatGoogleGenerativeAI":
        provider = "google"
    elif class_name == "ChatAnthropic":
        provider = "anthropic"
    elif class_name == "ChatOpenAI":
        base_url = str(kwargs.get("openai_api_base") or kwargs.get("base_url", ""))
        if "openrouter" in base_url:
            provider = "openrouter"
        elif "azure" in base_url:
            provider = "azure_openai"
        else:
            provider = "openai"
    else:
        provider = "unknown"

    model = kwargs.get("model_name") or kwargs.get("model", "unknown")
    return provider, model
```

### 2.2 Decisión subóptima: Tabla de costos hardcodeada en código fuente

**Problema:** El ADR propone una tabla `_COST_PER_1K_TOKENS` hardcodeada en `metrics_processor.py`. Los precios de los modelos LLM cambian frecuentemente (OpenRouter ajusta precios semanalmente). Hardcodearlos en código fuente requiere un commit + deploy para cada actualización.

**Alternativa superior:** Usar `litellm` (librería ya popular en el ecosistema LangChain) que mantiene una base de datos de precios actualizada:

```python
# Opción A: litellm (requiere añadir dependencia)
from litellm import cost_per_token
input_cost, output_cost = cost_per_token(model="minimax/minimax-m2.5:free",
                                           prompt_tokens=1000,
                                           completion_tokens=500)
```

```python
# Opción B: Archivo de configuración externo (sin nueva dependencia)
# costs.json actualizable sin deploy
import json
from pathlib import Path

_COSTS_FILE = Path("config/llm_costs.json")
_COST_TABLE = json.loads(_COSTS_FILE.read_text()) if _COSTS_FILE.exists() else {}
```

**Justificación:** La Opción A es más robusta pero añade una dependencia. La Opción B es pragmática y no requiere dependencias nuevas. Ambas son superiores a hardcodear en código fuente.

**Nota:** `litellm` no está en `pyproject.toml` actualmente. Si se adopta, requiere `uv add litellm`.

### 2.3 Gap conceptual: Sin métricas de calidad de respuesta

**Problema:** El ADR se enfoca en métricas de infraestructura (latencia, tokens, costos) pero ignora métricas de **calidad de respuesta**:
- Tasa de reintentos del usuario (indica respuesta insatisfactoria)
- Longitud de respuesta vs. satisfacción
- Fallbacks consecutivos (indica degradación sistémica)

**Recomendación:** Añadir al menos una métrica de calidad: `llm_retry_rate` (porcentaje de mensajes del usuario que son reintentos o reformulaciones dentro de la misma sesión).

### 2.4 Gap de diseño: Dashboard sin especificación de deploy

**Problema:** El ADR menciona "Configurar Prometheus + Grafana" pero no especifica:
- ¿Grafana corre en la misma VM de GCP? (requiere ~512MB RAM adicional)
- ¿O en un servicio externo (Grafana Cloud free tier)?
- ¿Cómo se expone `/metrics` al exterior? (actualmente solo accesible localmente)

**Recomendación:** Para v0.9.x, usar Grafana Cloud free tier (10K series gratis) + Prometheus remote write. No requiere infraestructura adicional en la VM.

---

## 3. ADR-0036: Inteligencia Temporal

### 3.1 Bug: `datetime.utcnow()` está deprecated en Python 3.12+

**Problema:** El pseudocódigo del ADR usa `datetime.utcnow()` en tres lugares:
- Sección 1: `datetime.utcnow()` para calcular elapsed
- Sección 2: `datetime.utcnow().isoformat()` como fallback
- Sección 3: `datetime.utcnow()` en `_format_age`

El proyecto requiere Python >= 3.13 (confirmado en `pyproject.toml`). `datetime.utcnow()` genera `DeprecationWarning` desde Python 3.12.

**Corrección:** Reemplazar todas las ocurrencias por `datetime.now(timezone.utc)`:
```python
from datetime import datetime, timezone

ts = datetime.now(timezone.utc)
```

**Nota:** El código existente en `prompt_builder.py` ya usa el patrón correcto: `datetime.now(ZoneInfo(user_tz))`. El ADR debería seguir la convención existente.

### 3.2 Inconsistencia: Metadata temporal se añade al dict, no al campo `metadata` JSON

**Problema:** El texto del ADR dice:
> "Estos campos se almacenan en el campo `metadata` (JSON) del fact, no como columnas nuevas"

Pero el código propuesto hace:
```python
fact["day_of_week"] = ts.weekday()
fact["hour_of_day"] = ts.hour
```

Esto añade los campos al dict raíz, no al sub-dict `metadata`. Si el schema de la tabla `memories` tiene una columna `metadata` JSON, los campos deben ir ahí:

```python
metadata = json.loads(fact.get("metadata", "{}"))
metadata["day_of_week"] = ts.weekday()
metadata["hour_of_day"] = ts.hour
fact["metadata"] = json.dumps(metadata)
```

### 3.3 Decisión subóptima: Detección de patrones con substring matching

**Problema:** La detección de patrones temporales usa:
```python
anxiety_facts = [f for f in facts if "ansied" in f["content"].lower()]
```

Esto es extremadamente simplista. "ansiedad" matchea, pero "nervioso", "preocupado", "inquieto", "tensión" no. Además, "ansiedad" en contexto positivo ("mi ansiedad ha bajado") se contaría como negativo.

**Alternativa superior:** Usar el LLM de consolidación (Gemini Flash, ya disponible via `get_rag_llm()`) para clasificar los hechos por categoría emocional:

```python
CLASSIFICATION_PROMPT = """
Clasifica estos hechos del usuario en categorías emocionales.
Retorna JSON: {"hecho_id": categoria}
Categorías: ansiedad, tristeza, alegría, ira, neutro, físico, financiero, social
Hechos: {facts_json}
"""
```

**Justificación:** El `ConsolidationWorker` ya usa Gemini Flash para generar aristas transversales. Añadir clasificación emocional en el mismo prompt tiene costo marginal (~200 tokens adicionales) y produce resultados significativamente mejores que substring matching.

### 3.4 Gap conceptual: Sin mecanismo de feedback para patrones temporales

**Problema:** Los patrones temporales se generan con `confidence=0.7` y se "refinan con más datos", pero no hay mecanismo de refinamiento definido. ¿Cómo se actualiza la confianza? ¿Cómo se eliminan patrones incorrectos?

**Recomendación:** Añadir un mecanismo de decay: cada semana, si no se detectan nuevas instancias del patrón, reducir `confidence *= 0.9`. Cuando `confidence < 0.3`, desactivar el patrón.

---

## 4. ADR-0037: Aprendizaje Continuo

### 4.1 Gap crítico: `keyword_search.search_conversations` no existe

**Problema:** El ADR propone un `Session Search Tool` que llama a:
```python
keyword_search.search_conversations(
    query=query, namespace=..., type_filter="conversation",
    days_back=days_back, limit=5
)
```

**Verificación contra código real:** `src/memory/keyword_search.py` solo tiene un método `search()` con parámetros: `query_text`, `limit`, `chat_id`, `namespace`, `source_skill`. **No existe** `search_conversations`, ni `type_filter`, ni `days_back`.

**Impacto:** El plan de implementación asume una API que no existe. Implementarlo tal cual generaría un `AttributeError` inmediato.

**Corrección:** El ADR debe especificar que se requiere **extender** `KeywordSearch` con un nuevo método:

```python
async def search_conversations(
    self,
    query_text: str,
    namespace: str,
    type_filter: str | None = None,
    days_back: int = 30,
    limit: int = 5,
) -> list[dict]:
    """Búsqueda FTS5 con filtrado temporal y por tipo."""
```

### 4.2 Decisión subóptima: Desduplicación con embeddings en el nudge

**Problema:** En mi evaluación previa recomendé usar embeddings (`sqlite-vec`) para la desduplicación del nudge, argumentando que FTS5 no detecta similitud semántica.

**Evaluación crítica posterior:** Esa recomendación ignora el *trade-off operativo*. El nudge ocurre cada 3 turnos (alta frecuencia). Generar un embedding es una llamada externa a la API de Gemini (red + latencia + costo). El nudge debe ser ligero.

**Solución pragmática (dos capas):**
1. **Capa rápida (nudge):** Mantener FTS5 para deduplicación por palabras clave. Es instantáneo, cero costo de API. Hechos que FTS5 detecta como duplicados se rechazan al instante.
2. **Capa diferida (ConsolidationWorker):** El `ConsolidationWorker` (corre cada ~30 min) ejecuta un job de *Garbage Collection Semántico* usando embeddings (`sqlite-vec`) para fusionar facts redundantes que FTS5 no pudo detectar. Esto evita que se acumulen con el tiempo.

Esta arquitectura de dos capas respeta el principio de AEGEN de que el nudge debe ser rápido, delegando la deduplicación costosa al worker background que ya tiene latencia aceptable.

### 4.3 Gap de diseño: Nudge cada 3 turnos es demasiado agresivo

**Problema:** El ADR propone `NUDGE_EVERY_N_TURNS = 3`. Hermes-agent (la inspiración citada) usa N=5-10. Con N=3:
- Cada 3 mensajes del usuario → 1 llamada LLM adicional (Groq)
- En una sesión de 30 minutos (~20 turnos) → ~7 llamadas LLM extra
- Costo: ~7 × ~500 tokens = ~3500 tokens adicionales por sesión

**Recomendación:** Usar N=5 como default, configurable por tipo de sesión:
- Chat casual: N=10 (baja prioridad de extracción)
- CBT/Terapia: N=3 (alta prioridad: cada detalle importa)
- Trading: N=5 (prioridad media)

### 4.4 Gap conceptual: Curador de skills sin criterio de criticidad

**Problema:** El curador archiva skills no usadas en >90 días. Pero un skill de "gestión de crisis" o "primeros auxilios psicológicos" puede no usarse en 90 días y ser crítico cuando se necesita.

**Corrección:** Añadir un campo `criticality` al SKILL.md:
```yaml
requires:
  criticality: "high"  # high | medium | low
```

Skills con `criticality: high` nunca se archivan automáticamente, independientemente del uso.

---

## 5. ADR-0038: Skills Dinámicos

### 5.1 Bug: `importlib.import_module()` ejecuta side effects

**Problema:** El gating condicional usa:
```python
for package in requires.get("python_packages", []):
    try:
        importlib.import_module(package)
    except ImportError:
        return False
```

`importlib.import_module()` **ejecuta** el módulo al importarlo. Si el paquete tiene side effects al importar (registro de signal handlers, conexión a servicios, etc.), esto puede causar problemas durante la carga de skills.

**Corrección:** Usar `importlib.util.find_spec()` que verifica existencia sin ejecutar:
```python
import importlib.util

for package in requires.get("python_packages", []):
    if importlib.util.find_spec(package) is None:
        return False
```

### 5.2 Anti-patrón: `watchdog` para hot-reload contradice la filosofía AEGEN

**Problema:** En mi evaluación previa recomendé usar `watchdog` (eventos nativos del OS) como alternativa superior al polling asíncrono del `KnowledgeWatcher`.

**Evaluación crítica posterior:** Esta recomendación **viola el principio de Gestión de Dependencias** de AEGEN. El polling de 30s es una línea de `asyncio.sleep()` con 0 dependencias. Para un sistema local-first con volumen bajo de archivos, es la solución arquitectónicamente correcta. Instalar una C-extension + dependencias binarias del OS para ahorrar 30s en detección de cambios de skills es sobre-ingeniería sin pragmatismo.

**Veredicto:** Mantener el polling asíncrono existente. No añadir `watchdog`. La latencia de 30s en hot-reload es aceptable para desarrollo y los skills en `storage/skills/` no requieren detección instantánea.

### 5.3 Gap conceptual: Skill Workshop sin criterio de detección de patrones

**Problema:** El trigger del Skill Workshop es:
> "El ConsolidationWorker detecta que el usuario ha completado N (default: 5) sesiones con un patrón similar"

Pero no se define **cómo** se detecta similitud entre sesiones. ¿Por keywords? ¿Por embeddings? ¿Por intent?

**Recomendación:** Usar clustering de embeddings de sesión:
1. Al finalizar cada sesión, generar embedding del resumen de sesión
2. Almacenar en `session_embeddings` (tabla nueva o extensión de `memories`)
3. Cada N sesiones, ejecutar clustering simple (DBSCAN o umbral de cosine similarity)
4. Si un cluster tiene ≥5 sesiones → trigger de Skill Workshop

### 5.4 Gap de seguridad: Sin sandboxing futuro definido

**Problema:** El ADR dice que `tools.py` en skills dinámicos está "deshabilitado" en v0.9.x, pero no define la estrategia de sandboxing para cuando se habilite.

**Recomendación:** Documentar la estrategia futura:
- **v0.10:** `tools.py` solo en skills de `src/personality/skills/` (código revisado)
- **v0.11:** `tools.py` en `storage/skills/` con validación estática (ruff + mypy)
- **v1.0:** `tools.py` en `storage/skills/user/` con sandboxing (Docker container o RestrictedPython)

---

## 6. Evaluación de Planes de Implementación

### 6.1 Plan `2026-05-29-fix-intents-graph-rag.md`

**Fortalezas:**
- Estructura TDD correcta (test → fail → implement → pass)
- Tests de sincronización de intents son valiosos como guardia de CI
- Commits atómicos por bug

**Problemas:**
- Hereda todos los gaps del ADR-0034 (ver sección 1)
- El test de `test_context_retriever_uses_no_hardcoded_intent_strings` usa heurística de `"_" in val` que puede generar falsos positivos con strings legítimos que contienen underscore

### 6.2 Plan `2026-05-29-observabilidad-multi-provider.md`

**Fortalezas:**
- Tests parametrizados con `@pytest.mark.parametrize`
- Cobertura de múltiples providers

**Problemas:**
- Hereda el bug de `ChatOpenAI → openrouter` (ver sección 2.1)
- Task 3 (corregir endpoint) es vaga: "leer el archivo encontrado" no es una instrucción ejecutable
- No incluye tests de integración del endpoint corregido

### 6.3 Plan `2026-05-29-bloque-d-aprendizaje-continuo.md`

**Fortalezas:**
- Estructura modular (cada task es independiente)
- Código de implementación completo (no pseudocódigo)

**Problemas:**
- Hereda el gap de `search_conversations` inexistente (ver sección 4.1)
- El `_save_fact_if_new` usa `IngestionPipeline` directamente sin verificar si el método `save_knowledge` acepta los parámetros propuestos
- Task D.2b (hot-reload) es demasiado vaga: "leer knowledge_watcher.py" y "añadir observación" sin código concreto

---

## 7. Alternativas Vanguardistas Evaluadas vs. Filosofía AEGEN

**Nota filosófica:** `AGENTS.md` establece que *no se añadan dependencias sin antes verificar si ya existe una alternativa en el proyecto*. Las alternativas "vanguardistas" presentadas en esta sección fueron evaluadas contra ese principio. La mayoría resultaron ser **Anti-Patrones de sobredimensionamiento** para el estado actual del sistema.

### 7.1 OpenTelemetry — Anti-patrón para Local-First

**No adoptar.** Prometheus + callbacks custom cumple exactamente con las necesidades de un sistema local-first con ~5 métricas. OpenTelemetry requiere 3+ dependencias pesadas y su valor (trazas distribuidas) es irrelevante cuando todo corre en una sola VM. Re-evaluar solo si AEGEN migra a microservicios distribuidos.

### 7.2 LiteLLM — No justificado para 3 providers

**No adoptar.** `engine.py` maneja 3 providers con código explícito. LiteLLM abstrae 100+ providers, pero su sobrecarga no se justifica para un conjunto fijo y pequeño. Re-evaluar cuando se añadan 5+ providers.

### 7.3 Compresión de contexto con extractive summarization

**Opción válida pero no superior.** TextRank/LexRank elimina costo de tokens pero sacrifica coherencia narrativa. Para el contexto de terapia de AEGEN, la compresión LLM (Gemini Flash) produce mejor calidad. Documentar como alternativa para skills no conversacionales (trading, análisis de datos).

### 7.4 Feature flags para activación gradual

**Recomendación adoptada.** Ningún ADR actual menciona feature flags. Añadir un archivo simple `config/feature_flags.py` con un dict de flags booleanos. Sin dependencias externas. Esto permite activar/desactivar Graph-RAG data-driven, memory nudge, y hot-reload sin deploy.

---

## 8. Recomendaciones Priorizadas

### Prioridad Alta (corregir antes de implementar)

| # | Recomendación | ADR afectado |
|---|---|---|
| 1 | Corregir `_check_edges_exist` para verificar origen Y destino | ADR-0034 |
| 2 | Corregir `_PROVIDER_MAP` para `ChatOpenAI` con lógica de `base_url` | ADR-0035 |
| 3 | Reemplazar `datetime.utcnow()` por `datetime.now(timezone.utc)` | ADR-0036 |
| 4 | Especificar que `search_conversations` debe crearse (no existe) | ADR-0037 |
| 5 | Reemplazar `importlib.import_module` por `importlib.util.find_spec` | ADR-0038 |
| 6 | Eliminar `_NON_CASUAL_KEYWORDS` de `_is_casual_message` — el regex anclado lo hace redundante | ADR-0034 |

### Prioridad Media (corregir durante implementación)

| # | Recomendación | ADR afectado |
|---|---|---|
| 7 | Arquitectura de dedup en dos capas: FTS5 para nudge (rápido), consolidación semántica diferida | ADR-0037 |
| 8 | Añadir poda por peso: umbral `accumulated_weight > 0.3` y `LIMIT 8` en la CTE de `graph_search.py` | ADR-0034 |
| 9 | Mover tabla de costos a archivo de configuración externo | ADR-0035 |
| 10 | Añadir campo `criticality` al gating de skills | ADR-0038 |
| 11 | Usar LLM para clasificación emocional en patrones temporales | ADR-0036 |
| 12 | Añadir feature flags para activación gradual | Todos |

### Decisiones rechazadas por feedback del usuario

| # | Recomendación descartada | Razón |
|---|---|---|
| — | `max_hops` adaptativo por `IntentType` | Reintroduce el mismo anti-patrón de BUG-1: gatear Graph-RAG por intent en lugar de por datos. La activación debe ser 100% data-driven. Reemplazado por poda por peso + LIMIT en la CTE (recomendación #8). |

### Prioridad Baja (mejoras futuras)

| # | Recomendación | ADR afectado |
|---|---|---|
| 13 | Definir estrategia de sandboxing para skills dinámicos | ADR-0038 |
| 14 | Definir mecanismo de detección de patrones para Skill Workshop | ADR-0038 |

---

## 9. Conclusión

Los ADRs 0034-0038 y sus planes de implementación representan un **buen diagnóstico** del estado del sistema. La evaluación forense identificó 6 problemas de Prioridad Alta, todos corregidos en los documentos.

Sin embargo, mi propia evaluación forense contenía **2 errores de criterio** (redundancia de la lista de crisis y embedding en nudge) y **3 recomendaciones anti-filosofía AEGEN** (OpenTelemetry, LiteLLM, watchdog) que violan el principio de Gestión de Dependencias. Además, el diseño de `max_hops` adaptativo por `IntentType` —que aprobé en la primera iteración— reintroducía el mismo anti-patrón de BUG-1, corregido en la iteración final por feedback del usuario.

**Lección principal:** La filosofía de AEGEN (Pragmatismo Medible, Gestión Estricta de Dependencias) no es opcional. Cada recomendación técnica debe pesarse contra estos principios, no solo contra la optimalidad técnica abstracta. El diseño correcto es:
1. **Activación 100% data-driven** (sin discriminar por intent)
2. **Poda por relevancia** (peso acumulado + límite de fragmentos) en lugar de filtro por intent

**Estado actual:**
- Los 7 problemas de Prioridad Alta están corregidos en ADRs y planes.
- Los problemas de Prioridad Media (recomendación #7-#12) pueden abordarse durante implementación.
- La decisión de `max_hops` adaptativo por intent fue rechazada formalmente (ver tabla en sección 8).
- Las mejoras de Prioridad Baja (#13-#14) son ideas válidas pero no urgentes.

## 10. Correcciones Aplicadas en Iteración Final (2026-05-29)

Basadas en feedback del usuario y re-evaluación contra la filosofía central de AEGEN (Arquitectura Evolutiva, sistema vivo):

| # | Corrección | Documentos afectados | Razón |
|---|---|---|---|
| 1 | **Añadido feedback loop de aristas vía ConsolidationWorker** | ADR-0034 (s1c), ADR-0037 (s5), ambos planes | La evolución viva es el eje central. El LLM en ConsolidationWorker evalúa utilidad de fragmentos y ajusta pesos de `memory_edges`. La alternativa descartada (cosine similarity) produce falsos positivos masivos. |
| 2 | **Eliminada duración de sesión de B.7** | ADR-0036, PLAN-MAESTRO | YAGNI. Sin instrucciones de pacing en los prompts actuales, inyectar el cronómetro no produce valor. |
| 3 | **Añadido RoundRobinKeyProvider** | ADR-0035 (s6), PLAN-MAESTRO (A.10) | El usuario dispone de múltiples cuentas Google AI Studio. Rotación round-robin con cooldown de 60s ante rate limits. Encapsulado en provider. |
| 4 | **Elevada prioridad del Bloque D** | PLAN-MAESTRO | La auto-mejora es el eje central. D.1 (aprendizaje continuo + edge feedback) sube en el orden de ejecución — inmediatamente después de corregir bugs críticos A.4/C.4. |
| 5 | **Marcado C.1 como prerequisito de D.2** | PLAN-MAESTRO | No se puede construir auto-generación de skills sin auditar que la fábrica de habilidades funcione. |
| 6 | **Descartada formalmente la Opción B (LLM-guía la expansión vía `relation_types`)** | ADR-0037 (s Decisiones descartadas) | El LLM decidiría a ciegas (sin ver contenido de las aristas). Es una llamada extra que no compra información real. |
| 7 | **Reemplazado Literal hardcodeado por `IntentType` directo en routing_tools** | ADR-0034 (s3), plan fix-intents (Task 1) | El Literal de 10 intents era la fuente de BUG-3 y requería mantenimiento manual en 4 archivos. Usar `IntentType` como tipo del parámetro `intent` elimina la desincronización: LangChain extrae los valores del enum automáticamente. Ahora solo hay 1 fuente de verdad: `routing_models.py`. |
| 8 | **Estabilización: intents = verbos fijos, skills = overlays dinámicos** | ADR-0038, PLAN-MAESTRO | Descartada la idea de ruteo dinámico para skills auto-generados. Los 11 intents son "verbos" (acciones fundamentales del usuario) y son estáticos. Las skills son "overlays" (dominios de conocimiento/herramientas) y son dinámicas. El Skill Workshop no genera intents; solo añade tools y prompts a los especialistas existentes. |

---

*Este documento fue generado y corregido como parte de la auditoría técnica del 2026-05-29. Las correcciones de Prioridad Alta están aplicadas en los ADRs y planes correspondientes.*
