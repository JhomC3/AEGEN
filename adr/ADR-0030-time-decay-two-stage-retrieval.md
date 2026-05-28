# ADR-0030 - Time Decay Real y Two-Stage Retrieval en Búsqueda Híbrida

- **Fecha:** 2026-05-26
- **Estado:** Aceptado
- **Autor:** Lead Architect & MAGI AI
- **ADR Relacionado:** ADR-0028 (Parent-Child RAG), Plan Maestro B.3 (Smart Decay)

## Contexto

El motor de búsqueda híbrida actual (`src/memory/hybrid_search.py`) aplica Reciprocal Rank Fusion (RRF) con pesos fijos (`vw=0.7`, `kw=0.3`, `k=60`) sobre los resultados de `VectorSearch` (sqlite-vec, KNN) y `KeywordSearch` (FTS5 BM25). El campo `created_at` de cada memoria **no se considera en ningún punto del ranking**.

Esto genera un problema estructural creciente: a medida que el usuario acumula meses de conversaciones, memorias de hace un año compiten con exactamente el mismo peso que las de ayer. Un hecho obsoleto (*"Usuario estresado por el Proyecto X"*) puede posicionarse por encima de su resolución posterior (*"Usuario completó el Proyecto X con éxito"*) si el embedding de la queja antigua tiene mayor similitud semántica con la consulta actual.

La documentación interna de v0.7.0 afirmaba que el Time Decay estaba implementado. La auditoría del código confirma que no lo está — es deuda técnica documentada incorrectamente.

Adicionalmente, `sqlite-vec` no permite inyectar fórmulas matemáticas arbitrarias en su motor KNN interno. El decaimiento exponencial debe aplicarse en Python, post-recuperación, lo que define la arquitectura Two-Stage obligatoriamente.

## Decisión

Se implementa el **Two-Stage Retrieval con Decaimiento Exponencial Temporal** como el nuevo estándar de ranking en `HybridSearch`:

### Etapa 1 — Recuperación Semántica Amplia (SQLite + Python)
`VectorSearch.search()` devuelve los **Top-100** candidatos por similitud semántica pura (KNN en sqlite-vec). El valor 100 garantiza cobertura suficiente para que el re-ranking temporal pueda seleccionar los mejores sin perder candidatos relevantes recientes que el KNN puro habría deprioritizado.

### Etapa 2 — Re-ranking con Decaimiento Exponencial (Python)
Sobre los 100 candidatos, se aplica en Python:

$$Score_{final} = Score_{similitud} \times e^{-\lambda \cdot \Delta t_{dias}}$$

donde:
- $Score_{similitud}$: puntuación RRF normalizada de la Etapa 1.
- $\Delta t_{dias}$: antigüedad de la memoria en días desde `created_at` hasta ahora.
- $\lambda$: parámetro de decaimiento, **valor inicial = 0.01** (equivale a una vida media de ~70 días; una memoria de 70 días vale ~50% de una memoria de hoy con igual similitud semántica).
- $\lambda$ se expone como `MEMORY_DECAY_LAMBDA` en `src/core/config/base.py` para calibración empírica sin cambios de código.

Se retornan los **Top-15** por `Score_final`. Este número reemplaza los límites hardcoded por especialista (chat: 4, CBT: 5) con un pool compartido que los especialistas filtran según contexto.

### Filtro de Umbral Complementario
Se mantiene el umbral de similitud mínima de `score >= 0.70` establecido en ADR-0028. Memorias por debajo del umbral se descartan antes del re-ranking temporal, evitando que memorias antiguas irrelevantes "sobrevivan" por ser ligeramente relevantes.

### Compatibilidad con Parent-Child RAG (ADR-0028)
El Two-Stage Retrieval opera sobre los chunks hijos (embeddings de alta resolución). Tras el re-ranking, la resolución al chunk padre se mantiene igual que en ADR-0028: `JOIN` por `parent_id` para inyectar contexto extendido.

## Consecuencias

### Positivas
- **Smart Decay implementado**: Cierra la deuda técnica del Plan Maestro B.3 y la inconsistencia de documentación de v0.7.0.
- **Contexto temporalmente coherente**: Las memorias recientes tienen prioridad natural. Los hechos resueltos o contradichos no compiten en igualdad de condiciones con los actuales.
- **Calibrable sin código**: `λ` en settings permite ajustar la "memoria" del sistema sin redeployment.
- **Sin costo adicional**: El re-ranking ocurre en Python con operaciones matemáticas simples. Cero llamadas LLM adicionales.

### Negativas / Riesgos
- **Top-100 vs Top-N**: Recuperar 100 candidatos de sqlite-vec en lugar de 5-10 implica un overhead de I/O medible. Benchmarking necesario para confirmar que se mantiene bajo 100ms en la DB actual.
- **Calibración de λ**: El valor inicial 0.01 es una estimación razonada, no empírica. Si el usuario tiene conversaciones muy espaciadas (ej. habla con MAGI una vez por semana), el decaimiento puede ser demasiado agresivo. El monitoreo de métricas de relevancia informará ajustes.
- **Memorias sin timestamp**: Si `created_at` es NULL (datos legacy o bugs de ingesta), la fórmula debe manejar el caso con un fallback a `Score_final = Score_similitud` (sin penalización).
