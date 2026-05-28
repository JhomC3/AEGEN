# ADR-0031 - Exposición del Contexto RAG en GraphStateV2 y Nodo context_retriever

- **Fecha:** 2026-05-26
- **Estado:** Aceptado
- **Autor:** Lead Architect & MAGI AI
- **ADR Relacionado:** ADR-0026 (Skills Modulares / Agentic Hub), ADR-0028 (Parent-Child RAG), ADR-0030 (Two-Stage Retrieval)

## Contexto

En la arquitectura actual, la recuperación de contexto RAG ocurre **dentro de cada tool de cada especialista**, de forma invisible al orquestador y al grafo de LangGraph:

- `src/personality/skills/chat/tools.py:25-61`: `_get_chat_rag_context()` recupera 2+2 fragmentos y los formatea como texto plano.
- `src/personality/skills/tcc/tools.py:28-65`: `_get_cbt_rag_context()` recupera 3+2 fragmentos con la misma lógica.

Esto genera tres problemas estructurales:

1. **Invisibilidad al orquestador**: El `GraphStateV2` (`src/core/schemas/graph.py:44-51`) no tiene ningún campo para el contexto RAG. El orquestador no puede auditarlo, limitarlo ni inspeccionarlo para decisiones de enrutamiento.
2. **Recuperaciones duplicadas**: Si en el futuro un flujo involucra más de un nodo que necesite contexto (ej. nodo de análisis + nodo de respuesta), SQLite se consulta N veces con la misma query.
3. **Acoplamiento tool-recuperación**: La lógica de cómo se recupera el contexto está mezclada con la lógica de cómo se usa. Cambiar la estrategia de recuperación (ej. ADR-0030) requiere modificar cada tool de cada especialista por separado.

Además, el contexto RAG se inyecta al prompt en tres canales mezclados (`knowledge_context`, `history_summary`, `structured_knowledge`) sin ningún límite de tokens explícito ni priorización entre ellos.

## Decisión

Se introduce un **nodo dedicado `context_retriever`** en el grafo LangGraph y un nuevo schema `RagContextSnapshot` en `GraphStateV2`:

### 1. Nuevo Schema: `RagContextSnapshot`

```python
# src/core/schemas/graph.py
class RagContextSnapshot(TypedDict, total=False):
    semantic_fragments: list[dict]   # resultados del Two-Stage Retrieval
    evolution_note: str | None       # Nota Evolutiva desde Redis
    structured_facts: list[dict]     # facts atómicos de alta confianza
    total_tokens_estimated: int      # estimación para guardia de límite
    retrieved_at: float              # timestamp Unix de la recuperación
    cache_hit: bool                  # True si evolution_note vino de Redis
```

`GraphStateV2` incorpora el campo opcional:
```python
rag_context: RagContextSnapshot | None
```

### 2. Nodo `context_retriever` en el grafo

Se añade un nodo `context_retriever` que se ejecuta **después del enrutamiento y antes del nodo especialista**. Su responsabilidad única es:
1. Tomar `event.text` del estado como query.
2. Ejecutar el Two-Stage Retrieval (ADR-0030) para obtener `semantic_fragments`.
3. Consultar Redis para `evolution_note` (cache hit). Si miss, leer desde SQLite.
4. Cargar `structured_facts` de confianza ≥ 0.7 del perfil.
5. Estimar tokens totales y aplicar guardia: si supera `MAX_RAG_TOKENS` (configurable, default 2000), truncar `semantic_fragments` primero, luego `structured_facts`.
6. Depositar `RagContextSnapshot` en `state["rag_context"]`.

### 3. Refactorización de tools de especialistas

Los tools de Chat y CBT eliminan sus funciones `_get_chat_rag_context()` y `_get_cbt_rag_context()`. En su lugar, leen `state["rag_context"]` que ya viene precargado. La construcción del system prompt en `prompt_builder.py` consume `RagContextSnapshot` directamente.

### 4. RAG Condicional por intent (RAG Dinámico)

El nodo `context_retriever` aplica lógica condicional antes de recuperar:
- Si el `routing_metadata` del estado indica `intent = "casual_greeting"` o `processing_type = "conversational_only"`: no se ejecuta recuperación semántica. `semantic_fragments = []`. Solo se carga `evolution_note` desde Redis (0ms).
- Para todos los demás intents: recuperación completa.

Esto elimina la inyección de 1,000-2,000 tokens de teoría clínica en saludos.

## Consecuencias

### Positivas
- **Orquestador informado**: El grafo puede inspeccionar y tomar decisiones basadas en el contexto RAG disponible.
- **Cero recuperaciones duplicadas**: Un solo nodo, una sola consulta por interacción.
- **RAG dinámico real**: La recuperación es condicional al intent, no siempre activa.
- **Límite de tokens centralizado**: Un único punto de control para el presupuesto de tokens del contexto.
- **Testabilidad**: El nodo `context_retriever` es un componente independiente testeable en aislamiento.

### Negativas / Riesgos
- **Modifica `GraphStateV2`**: Es un cambio de schema de estado del grafo. Requiere que todos los nodos del grafo sean compatibles con el nuevo campo (es opcional/None, por lo que la compatibilidad hacia atrás está garantizada).
- **Añade latencia al grafo**: Un nodo extra significa una llamada más en el pipeline. Sin embargo, al eliminar las llamadas duplicadas desde los tools, el balance neto de latencia es neutro o negativo (menor latencia total).
- **Acoplamiento con el enrutador**: El nodo `context_retriever` necesita leer `routing_metadata` para aplicar la lógica condicional. El enrutador debe poblar este campo antes de que el nodo se ejecute.
