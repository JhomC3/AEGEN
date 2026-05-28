# ADR-0033 - Graph-RAG Transversal: Tabla memory_edges y Búsqueda Multi-Dominio

- **Fecha:** 2026-05-26
- **Estado:** Aceptado
- **Autor:** Lead Architect & MAGI AI
- **ADR Relacionado:** ADR-0028 (Parent-Child RAG / parent_id), ADR-0030 (Two-Stage Retrieval), ADR-0031 (context_retriever), ADR-0032 (Ingesta Atómica)

## Contexto

La arquitectura actual de memoria es puramente **jerárquica lineal**: un recuerdo puede tener un padre (`parent_id`), pero no puede tener relaciones laterales con recuerdos de otros dominios. La búsqueda híbrida (vector + keyword) opera sobre recuerdos de forma aislada — no puede descubrir que un evento de Fitness (déficit calórico sostenido) tiene una correlación causal con un patrón de Psicología (irritabilidad) o de Finanzas (gasto impulsivo).

Para que MAGI ofrezca razonamiento analítico multi-dominio — la capacidad de cruzar métricas duras con variables blandas — se requiere un grafo de relaciones explícitas entre memorias. Este grafo, combinado con el Two-Stage Retrieval (ADR-0030), materializa el **Graph-RAG**: recuperación de sub-grafos relacionados en lugar de fragmentos aislados.

ADR-0028 introdujo `parent_id` para la jerarquía vertical (padre-hijo dentro del mismo documento). Este ADR introduce la dimensión horizontal: relaciones entre memorias de cualquier tipo y dominio.

## Decisión

### 1. Nueva tabla `memory_edges` en el schema

```sql
CREATE TABLE IF NOT EXISTS memory_edges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    origen_id    INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    destino_id   INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    tipo_relacion TEXT NOT NULL,   -- 'correlaciona_con' | 'causa' | 'resuelve' | 'contradice' | 'refuerza'
    peso         REAL NOT NULL DEFAULT 1.0,
    evidencia    TEXT,             -- cita textual o descripción del enlace
    created_by   TEXT NOT NULL,    -- 'consolidation_worker' | 'ingestion_pipeline' | 'manual'
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_edges_origen  ON memory_edges(origen_id);
CREATE INDEX IF NOT EXISTS idx_edges_destino ON memory_edges(destino_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_pair ON memory_edges(origen_id, destino_id, tipo_relacion);
```

El vocabulario controlado de `tipo_relacion` evita proliferación de tipos inconsistentes. Nuevos tipos se añaden mediante ADR o PR documentado.

### 2. Quién crea los edges

**`ConsolidationWorker` (background)**: Al redactar la Nota de Progreso Analítica, el LLM (Gemini Flash, per ADR-0029) identifica correlaciones entre eventos atómicos de distintos dominios y las escribe como `memory_edges` en la DB. El prompt de consolidación incluye instrucciones explícitas para detectar y declarar relaciones causales o de correlación.

**`IngestionPipeline` (fuentes externas)**: Al ingestar un libro o transcripción con la doble ontología (Pilar I), el agente de ingesta puede crear edges entre conceptos del mismo documento (ej. Nivel 2 → Nivel 3 dentro del mismo framework clínico).

### 3. Graph-RAG: Recuperación de Sub-grafos (máximo 2 saltos)

Se añade un nuevo módulo `src/memory/graph_search.py` con la función `expand_with_edges()`:

```python
async def expand_with_edges(
    seed_memory_ids: list[int],
    max_hops: int = 2,
    relation_types: list[str] | None = None,
) -> list[dict]:
    """
    Dado un conjunto de memory IDs semilla (resultado del Two-Stage Retrieval),
    expande el grafo hasta max_hops saltos usando memory_edges.
    Retorna los recuerdos del sub-grafo con su peso de arista acumulado.
    """
```

La implementación usa CTEs recursivos de SQLite:

```sql
WITH RECURSIVE subgraph(memory_id, depth, accumulated_weight) AS (
    -- Semilla: los IDs del Two-Stage Retrieval
    SELECT origen_id, 0, 1.0 FROM memory_edges WHERE origen_id IN (...)
    UNION ALL
    SELECT e.destino_id, s.depth + 1, s.accumulated_weight * e.peso
    FROM memory_edges e
    JOIN subgraph s ON e.origen_id = s.memory_id
    WHERE s.depth < 2   -- límite de 2 saltos
)
SELECT DISTINCT memory_id, MAX(accumulated_weight) as relevance
FROM subgraph
GROUP BY memory_id
ORDER BY relevance DESC;
```

El límite de **2 saltos** es fijo y no configurable. Profundidad mayor requeriría un motor de grafo dedicado (Neo4j, etc.) y degradaría la latencia en SQLite con volúmenes altos.

### 4. Integración en el nodo `context_retriever` (ADR-0031)

El nodo `context_retriever` ejecuta la expansión de grafo **opcionalmente**, solo cuando `routing_metadata` indica un intent analítico o de síntesis (ej. `"life_review"`, `"pattern_analysis"`). Para intents conversacionales simples, el grafo no se expande, preservando la latencia.

El `RagContextSnapshot` (ADR-0031) incorpora un campo adicional:
```python
graph_fragments: list[dict]  # memorias del sub-grafo expandido
```

### 5. Migración de datos existentes

La tabla `memory_edges` nace vacía. No requiere migración de datos existentes — el grafo se construye incrementalmente a medida que el `ConsolidationWorker` procesa sesiones futuras. Para usuarios activos, el grafo estará parcialmente poblado tras las primeras sesiones de consolidación post-deploy.

## Consecuencias

### Positivas
- **Razonamiento multi-dominio**: MAGI puede conectar déficit calórico → irritabilidad → gasto impulsivo de forma estructurada y recuperable, no como inferencia LLM sobre texto plano.
- **Grafo incremental**: No requiere migración masiva. Crece orgánicamente con cada sesión.
- **Vocabulario controlado**: El conjunto finito de `tipo_relacion` mantiene el grafo semánticamente coherente y consultable.
- **SQLite nativo**: Las CTEs recursivas son soportadas por SQLite 3.8.3+ (el proyecto ya usa versiones modernas). Sin dependencias adicionales.

### Negativas / Riesgos
- **Calidad del grafo depende del LLM**: Si `ConsolidationWorker` genera edges incorrectos o irrelevantes, el Graph-RAG amplifica el ruido. El campo `evidencia` y el `peso` permiten filtrado posterior pero no garantizan calidad en la generación.
- **Crecimiento de `memory_edges`**: Con el tiempo, la tabla puede crecer significativamente. El índice `idx_edges_pair` (UNIQUE sobre origen+destino+tipo) previene duplicados. Una tarea de mantenimiento periódico puede desactivar edges de baja confianza (peso < 0.3).
- **Latencia de CTEs recursivas**: Benchmarking necesario con volúmenes reales (>10K edges). Si supera 50ms, se puede materializar el sub-grafo como tabla temporal o limitar `max_hops` a 1 para intents no analíticos.
- **Requiere ADR previo a implementación**: Este ADR es el requisito formal. El script de migración de schema debe ejecutarse con backup previo de la DB de producción.
