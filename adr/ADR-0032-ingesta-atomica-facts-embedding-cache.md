# ADR-0032 - Ingesta Atómica de Facts y Embedding Cache Operativa

- **Fecha:** 2026-05-26
- **Estado:** Aceptado
- **Autor:** Lead Architect & MAGI AI
- **ADR Relacionado:** ADR-0028 (Parent-Child RAG), ADR-0030 (Two-Stage Retrieval)

## Contexto

### Problema A: Ingesta de Facts como JSON Blob (No Atómica)

`FactExtractor` extrae hechos del usuario como un diccionario Python (ej. `{"nombre": "Juan", "profesion": "ingeniero", "meta": "bajar 5kg", ...}`). `knowledge_base_manager.save_knowledge()` serializa este diccionario completo como un string JSON y lo pasa a `IngestionPipeline.process_text()` (`src/memory/knowledge_base.py:96-107`).

`IngestionPipeline` chunquea este JSON a bloques de 400 tokens, generando chunks que mezclan múltiples hechos no relacionados:

```
Chunk 1: {"nombre": "Juan", "profesion": "ingeniero", "meta": "bajar 5kg", "estres_actual": "proyecto X", "dieta_preferida": "cetogenica", "hora_entrenamiento":
Chunk 2: "06:00", "presupuesto_mensual": 2000, "gasto_cafe_semanal": 50, ...}
```

Cuando el agente busca "¿cuál es la meta del usuario?", el vector más similar puede ser `Chunk 1` — que contiene la meta mezclada con 5 otros hechos no relacionados y truncada a la mitad. El LLM recibe ruido en lugar de información precisa.

Adicionalmente, el fallback de bóveda en `knowledge_base.py:59-75` busca `search_by_type(memory_type="fact", limit=1)` asumiendo que el JSON completo está en un único registro. Con el chunking, esta asunción es falsa: la bóveda se sirve incompleta silenciosamente.

### Problema B: Embedding Cache Inoperativa

`src/memory/schema.sql:61-65` define la tabla `embedding_cache` con columnas `content_hash`, `embedding`, `created_at`. Sin embargo, `EmbeddingService` (`src/memory/embeddings.py`) nunca consulta esta tabla antes de llamar a la API de Google, ni escribe en ella tras una llamada exitosa. Cada re-embedding de contenido idéntico incurre en costo de API innecesario. Durante re-ingestas de documentos (libros, PDFs), cientos de chunks idénticos se re-embeben.

Adicionalmente, la tabla `embedding_cache` no tiene índice sobre `content_hash`, lo que haría cualquier lookup O(n) incluso si la lógica existiera.

### Problema C: `source_skill` Nunca Poblado

La columna `source_skill` en `memories` está definida en el schema (`schema.sql:21`) y disponible como filtro en `KeywordSearch.search()` (`src/memory/keyword_search.py:105-107`). Sin embargo, `IngestionPipeline.process_text()` nunca recibe ni escribe este campo. El filtro por skill origen es inoperable en producción.

## Decisión

### Decisión A: Ingesta Atómica de Facts

Se reemplaza `save_knowledge()` por `save_knowledge_atomic()` en `KnowledgeBaseManager`:

- Itera cada entrada del diccionario de facts extraídos.
- Para cada hecho, construye una string de texto semánticamente auto-contenida: `"{clave}: {valor}"` con contexto adicional si el valor es complejo.
- Llama a `IngestionPipeline.process_text()` individualmente por hecho, con metadatos:
  ```python
  {
    "memory_type": "fact",
    "domain": "<dominio_inferido>",   # finance, fitness, psychology, general
    "hierarchy_level": 4,
    "fact_key": "<clave>",
    "source_skill": "<skill_origen>",
    "timestamp": <unix_epoch>
  }
  ```
- Cada hecho tiene su propio embedding, su propio registro en `memories`, y su propia entrada en `memory_vectors`. Es recuperable de forma precisa e independiente.
- El fallback de bóveda se reemplaza por una query `WHERE memory_type='fact' AND chat_id=? AND is_active=1 ORDER BY created_at DESC` que reconstruye la bóveda desde los registros atómicos.

### Decisión B: Activación de Embedding Cache con Índice

Se implementa la lógica hit/miss en `EmbeddingService`:

1. Antes de llamar a la API: `SELECT embedding FROM embedding_cache WHERE content_hash = ?`.
2. Si hay hit: deserializar y retornar el vector. Cero llamadas API.
3. Si hay miss: llamar a la API, guardar en `embedding_cache`, retornar el vector.
4. En `migration.py`: añadir `CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash ON embedding_cache(content_hash)` para garantizar lookup O(log n).
5. TTL de caché: las entradas de `embedding_cache` no tienen TTL — los embeddings de un modelo dado son deterministas. Solo se invalidan si se cambia el modelo de embedding.

### Decisión C: Propagación de `source_skill`

`IngestionPipeline.process_text()` recibe el parámetro opcional `source_skill: str | None = None` y lo escribe en la columna `source_skill` del registro `memories`. Todos los callers que conocen el skill origen (tools de CBT, Chat, Transcripción, `GlobalKnowledgeLoader`) deben pasarlo explícitamente.

## Consecuencias

### Positivas
- **Recuperación semántica precisa**: Buscar "meta del usuario" retorna exactamente ese hecho, no un chunk JSON mezclado.
- **Fallback de bóveda robusto**: La reconstrucción desde registros atómicos es completa y determinista.
- **Ahorro de API de embeddings**: En re-ingestas, cero llamadas duplicadas a la API de Google.
- **Filtrado por skill habilitado**: Permite queries como "dame solo los hechos extraídos por el especialista TCC".

### Negativas / Riesgos
- **Mayor volumen de registros en `memories`**: Una bóveda con 50 hechos genera 50 registros en lugar de ~3 chunks. El índice `idx_memories_chat_namespace` y el filtro `WHERE is_active=1` mitigan el impacto en queries.
- **Migración de datos existentes**: Los registros de tipo `fact` ya existentes en la DB son blobs JSON. Se requiere un script de migración one-shot que los reingeste atómicamente. Los blobs originales se marcan `is_active=0` tras la migración.
- **Complejidad de `save_knowledge_atomic()`**: La inferencia del `domain` por fact_key requiere un mapeador (dict de reglas heurísticas) que puede no cubrir todos los casos. Los facts sin dominio inferible reciben `domain="general"`.
