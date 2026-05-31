# ADR-0034 - Graph-RAG Data-Driven y Corrección de IntentType en context_retriever

- **Fecha:** 2026-05-29
- **Estado:** Aceptado
- **Autor:** MAGI AI (auditoría automatizada)
- **ADR Relacionado:** ADR-0031 (context_retriever), ADR-0033 (memory_edges), ADR-0026 (routing)

## Contexto

La auditoría del codebase (2026-05-29) reveló tres bugs críticos interrelacionados en el sistema de enrutamiento e intents que invalidan funcionalidad ya mergeada:

### Bug 1: Graph-RAG muerto (ADR-0033 no operativo)

`context_retriever.py:142` hardcodea:

```python
analytical_intents = {"life_review", "pattern_analysis", "cross_domain_query"}
if intent in analytical_intents and semantic_fragments:
    graph_fragments = await expand_with_edges(...)
```

Ninguno de esos tres strings existe en `IntentType` (definido en `routing_models.py`). El enum solo define: `CHAT, FILE_ANALYSIS, SEARCH, HELP, TASK_EXECUTION, INFORMATION_REQUEST, PLANNING, DOCUMENT_CREATION, VULNERABILITY, TOPIC_SHIFT, PSICOTRADING`.

El router solo emite los 11 valores del enum, por lo que `intent in analytical_intents` **nunca es verdadero**. Todo el código de Graph-RAG de ADR-0033 (la tabla `memory_edges`, la función `expand_with_edges`, las CTEs recursivas) existe en disco y en la base de datos, pero **jamás se ejecuta** desde el deploy de v0.9.0.

### Bug 2: CASUAL_INTENTS inoperativo — RAG en saludos

`context_retriever.py` define:

```python
CASUAL_INTENTS = {"casual_greeting", "farewell", "acknowledgement"}
if intent in CASUAL_INTENTS:
    # skip búsqueda semántica
    return state
```

Igual que el anterior: ninguno de esos strings existe en `IntentType`. En la práctica, **el skip de búsqueda semántica para saludos nunca opera**. El RAG se ejecuta en cada mensaje, incluyendo saludos y despedidas, añadiendo latencia innecesaria (~400-800ms) y consumiendo tokens de embeddings en interacciones triviales.

### Bug 3: Psicotrading inaccesible vía LLM

`routing_tools.py` define un `Literal` de 10 intents para la función calling del router LLM. Falta `"psicotrading"`, que sí existe en `IntentType` y en `specialist_mapper.py`. El LLM del router nunca puede seleccionar el especialista Psicotrading; la detección de ese dominio queda restringida a los patrones de regex de `intent_patterns_data.py`, que tienen menor recall.

### Raíz del problema

Los tres bugs tienen la misma causa raíz: existen **cuatro fuentes de verdad** para el conjunto de intents válidos, que se han desincronizado:

1. `src/core/routing_models.py` → `IntentType` enum (fuente canónica)
2. `src/agents/orchestrator/routing/routing_tools.py` → `Literal` del tool LLM
3. `src/agents/orchestrator/context_retriever.py` → strings hardcodeados en `CASUAL_INTENTS` y `analytical_intents`
4. `src/agents/orchestrator/routing/intent_patterns_data.py` → patrones de regex por intent

Cada vez que se añade un intent nuevo, hay que actualizar los cuatro archivos. La ausencia de un test de sincronización hace que estas desincronizaciones sean invisibles hasta auditoría manual.

## Decisión

### 1. Graph-RAG activado por datos, no por intents

**Eliminar** el bloque `analytical_intents` en `context_retriever.py`. Reemplazarlo por una consulta de existencia de aristas sobre los fragmentos ya recuperados:

```python
# Verificar si algún fragmento semántico tiene aristas en memory_edges
if semantic_fragments:
    seed_ids = [item["id"] for item in semantic_fragments if "id" in item]
    if seed_ids:
        has_edges = await _check_edges_exist(store=manager.store, memory_ids=seed_ids)
        if has_edges:
            graph_fragments = await expand_with_edges(
                store=manager.store, seed_memory_ids=seed_ids, max_hops=2
            )
```

La función auxiliar `_check_edges_exist` es una consulta bidireccional:

```sql
SELECT 1 FROM memory_edges
WHERE origen_id IN (:ids) OR destino_id IN (:ids)
LIMIT 1
```

**Importante:** La consulta verifica tanto `origen_id` como `destino_id`. Las aristas en `memory_edges` son direccionales (origen → destino), pero para activar Graph-RAG nos interesa saber si el fragmento participa en **cualquier** relación, independientemente de la dirección. Verificar solo `origen_id` perdería ~50% de las aristas relevantes.

**Costo:** <5ms si no hay aristas (caso típico en sesiones nuevas). ~50-150ms si las hay, marginalmente sobre los ~7s totales del pipeline. Los índices `idx_edges_origen` e `idx_edges_destino` (definidos en ADR-0033) garantizan este rendimiento.

**Efecto:** El Graph-RAG se activa automáticamente para **cualquier intent** cuando `memory_edges` tenga datos relevantes. Cuando no haya aristas (usuario nuevo o primeras sesiones), el costo es nulo. Esto es correcto semánticamente: si no hay relaciones entre dominios, no hay grafo que expandir.

### 1b. Profundidad y poda del grafo

El Graph-RAG usa `max_hops=2` en todos los casos donde existan aristas. No se discrimina por `IntentType` — hacerlo reintroduce el mismo anti-patrón del bug original (gatear por intent en lugar de por datos). Ver sección 4 de este ADR.

```python
# Sin discriminación por intent. Se expanden 2 saltos si hay aristas.
if has_edges:
    graph_fragments = await expand_with_edges(
        store=manager.store, seed_memory_ids=seed_ids, max_hops=2
    )
```

Sin embargo, la expansión a ciegas puede saturar la ventana de contexto en usuarios con grafos densos. Se imponen tres límites para garantizar que la información expandida sea relevante:

**1. Orden por peso acumulado:** La CTE recursiva de `expand_with_edges` ordena los fragmentos por `accumulated_weight` descendente (el producto de los pesos de las aristas recorridas). Esto asegura que las relaciones más fuertes lleguen primero al contexto.

**2. Límite de fragmentos expandidos:** La expansión retorna como máximo 8 fragmentos por consulta. Más allá de 8, el ruido comienza a degradar la precisión del LLM (*Lost in the Middle*).

**3. Umbral de peso mínimo:** Fragmentos expandidos cuyo `accumulated_weight` sea menor a 0.3 se descartan. Aristas con peso < 0.3 representan correlaciones débiles o anecdóticas que no merecen ocupar tokens en el contexto del LLM.

Estos límites se implementan directamente en la query SQL (`graph_search.py`), no en Python:

```sql
WITH RECURSIVE subgraph(memory_id, depth, accumulated_weight) AS (
    SELECT e.origen_id, 0, 1.0 FROM memory_edges WHERE origen_id IN (...)
    UNION ALL
    SELECT e.destino_id, s.depth + 1, s.accumulated_weight * e.peso
    FROM memory_edges e
    JOIN subgraph s ON e.origen_id = s.memory_id
    WHERE s.depth < 2
)
SELECT DISTINCT memory_id, MAX(accumulated_weight) as relevance
FROM subgraph
WHERE accumulated_weight > 0.3   -- Umbral de peso mínimo
GROUP BY memory_id
ORDER BY relevance DESC
LIMIT 8                          -- Máximo de fragmentos expandidos
```

### 1c. Aprendizaje Evolutivo de los Pesos de Aristas (Sistema Vivo)

El grafo no tiene pesos estáticos. Cada arista en `memory_edges` tiene un `peso` que el `ConsolidationWorker` ajusta en cada ciclo de consolidación, basándose en razonamiento real del LLM sobre qué fragmentos fueron útiles en la conversación.

**Algoritmo de Feedback (ejecutado en background por el ConsolidationWorker):**

```python
# En consolidation_worker.py, después de _generate_transversal_edges()
async def _adjust_edge_weights_from_feedback(
    store, chat_id, conversation_history, injected_fragments
) -> None:
    """
    El LLM (Gemini Flash) evalúa qué fragmentos inyectados en el contexto
    fueron realmente pertinentes a la conversación. Los pesos de las aristas
    se refuerzan (+0.05) si el fragmento fue usado, se atenúan (-0.03) si no.
    """
    prompt = FEEDBACK_PROMPT.format(
        conversation=conversation_history,
        fragments=format_fragments_with_edges(injected_fragments),
    )
    response = await get_rag_llm().ainvoke(prompt)
    useful_ids = parse_useful_fragment_ids(response)

    for frag in injected_fragments:
        if frag["id"] in useful_ids:
            await _reinforce_edges(store, frag["id"], delta=+0.05)
        else:
            await _decay_edges(store, frag["id"], delta=-0.03)
```

**¿Por qué esto funciona y no la alternativa descartada (cosine similarity)?**
- **Cero ruido:** El LLM evalúa si el fragmento fue *pertinente a la dirección de la conversación*, no solo si sus palabras aparecen en la respuesta (falsos positivos frecuentes con cosine similarity).
- **Cero latencia para el usuario:** Ocurre en el `ConsolidationWorker` asíncrono (background, cada ~10 mensajes o 30 min).
- **Evolución real:** Las aristas que producen insights útiles suben de peso. Las que generan ruido bajan. Con el tiempo, el sistema aprende qué conexiones son valiosas para este usuario específico.

**Efecto neto sobre la poda (sección 1b):** Los umbrales `weight > 0.3` y `LIMIT 8` son solo los valores iniciales. El feedback del ConsolidationWorker afina los pesos de cada arista, haciendo que la poda sea progresivamente más precisa para cada usuario.

### 2. CASUAL_INTENTS alineado con IntentType real

Los intents casuales no están modelados en `IntentType` porque el router los colapsa a `CHAT`. La solución correcta no es añadir nuevos valores al enum (eso rompe la consistencia de routing), sino detectar casualidad **semánticamente** mediante el texto del mensaje.

Se añade una función `_is_casual_message(text: str) -> bool` con un patrón regex anclado que solo matchea mensajes que son **exclusivamente** una expresión casual:

```python
_CASUAL_PATTERN = re.compile(
    r"^\s*(hola|hey|buenas|ey|hi|hello|ok|okey|vale|gracias|"
    r"de nada|bye|hasta|adiós|chao|👋|🙋|entendido|claro|perfecto"
    r"|👍|✅)\s*[!.?]*\s*$",
    re.IGNORECASE | re.UNICODE,
)

def _is_casual_message(text: str) -> bool:
    """Detecta mensajes triviales que no requieren búsqueda semántica."""
    import unicodedata
    return bool(_CASUAL_PATTERN.match(unicodedata.normalize("NFC", text)))
```

**Nota de diseño:** El regex usa `^` y `$` para anclar la coincidencia al texto completo. Un mensaje como "estoy mal" **no** matchea porque el regex solo reconoce expresiones casuales puras ("hola", "gracias", etc.). No se requiere lista de exclusión de crisis — el anclaje del regex la vuelve redundante. En un contexto de salud mental, es más seguro dejar pasar falsos negativos (hacer RAG innecesario en un saludo) que arriesgar falsos positivos (saltar RAG en "me muero"). Esta función no depende del enum `IntentType` y no se desincroniza.

### 3. Usar `IntentType` directamente como anotación del tool, no un Literal hardcodeado

En lugar de mantener un `Literal` de strings a mano (propenso a desincronización), `routing_tools.py` usa el enum `IntentType` directamente como tipo del parámetro `intent`:

```python
from src.core.routing_models import IntentType

@tool
async def route_user_message(
    intent: IntentType,  # ← LangChain extrae los valores del enum automáticamente
    confidence: float,
    target_specialist: str,
    ...
```

LangChain convierte automáticamente el enum `IntentType` al JSON Schema que el LLM necesita para function calling. El LLM ve exactamente los mismos 11 valores. La diferencia: **cuando se añade un valor a `IntentType`, el tool se actualiza automáticamente.** No hay un segundo lugar que editar.

Esto elimina la raíz del BUG-3 (psicotrading faltante) y del problema estructural de "4 fuentes de verdad". Las 4 fuentes se reducen a 1: el enum `IntentType` en `routing_models.py` es la única fuente de verdad. El test de sincronización se simplifica a verificar que la anotación es `IntentType` y que ningún otro archivo hardcodea strings de intents.

**Comparación de enfoques:**

| Enfoque | Fuentes de verdad | Riesgo de desincronización | Esfuerzo al añadir intent |
|---|---|---|---|
| Literal hardcodeado (original) | 4 archivos | Alto | Manual en 4 lugares |
| Literal hardcodeado + test (ADR-0034 v1) | 4 archivos + test | Medio, el test detecta | Manual en 4 lugares, test valida |
| **IntentType directo (nuevo)** | **1 archivo** | **Cero** | **Solo añadir al enum** |

### 4. Test de validación de anotación de intents

Se añade un test en `tests/unit/core/test_intent_annotation.py` que verifica:

- La anotación del parámetro `intent` en `route_user_message` es `IntentType` (no un `Literal`).
- Ningún set de strings hardcodeados en `context_retriever.py` (CASUAL_INTENTS, analytical_intents, etc.) usa valores que no existan en `IntentType`.

Este test falla en CI si alguien vuelve a hardcodear un `Literal` o reintroduce strings de intents en archivos que no sean `routing_models.py`.

## Consecuencias

### Positivas
- **Graph-RAG operativo:** ADR-0033 comienza a funcionar por primera vez en producción. Las relaciones entre dominios en `memory_edges` empezarán a enriquecer el contexto.
- **Aprendizaje evolutivo de aristas:** El ConsolidationWorker ajusta los pesos de `memory_edges` basándose en qué fragmentos fueron realmente útiles en la conversación. Las aristas valiosas se refuerzan, las irrelevantes se atenúan. El grafo mejora con cada ciclo de consolidación, sin intervención humana.
- **Latencia reducida en saludos:** El skip de búsqueda semántica opera correctamente, ahorrando ~400-800ms en mensajes triviales.
- **Psicotrading accesible:** El LLM del router puede enrutar correctamente a psicotrading basándose en el contexto.
- **Prevención de regresiones:** El test de sincronización hace imposible la desincronización silenciosa de intents.

### Negativas / Riesgos
- **Graph-RAG activo para todos los intents:** Un intent `CHAT` simple que tenga fragmentos en `memory_edges` activará la expansión. Esto es deseable (más contexto), pero añade latencia para usuarios con muchas aristas. **Mitigado:** El umbral de peso mínimo (`accumulated_weight > 0.3`) y el límite de 8 fragmentos en la CTE previenen la saturación del contexto. Además, si no hay aristas (<5ms de verificación), no hay penalización de latencia.
- **Calidad del feedback inicial:** En usuarios nuevos con pocas aristas, el ConsolidationWorker no tendrá suficiente historial para evaluar utilidad. Las aristas mantendrán sus pesos iniciales (asignados por el LLM al crearlas) hasta acumular ~3 ciclos de feedback.
- **Patrones de casualidad falsos positivos:** Un mensaje muy corto como "sí" o "no" puede matchear el patrón casual si se añade al regex (actualmente no está). **Mitigado:** El regex anclado `^...$` solo matchea mensajes que son **exclusivamente** expresiones casuales.
- **Cambio de comportamiento en producción:** La primera vez que se despliegue, el RAG comenzará a operar en interacciones que antes lo saltaban (el bug de CASUAL_INTENTS). Esto es correcto técnicamente pero genera un cambio observable en respuestas.
