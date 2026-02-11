# Arquitectura del Sistema de Memoria

AEGEN utiliza una **Arquitectura de Memoria Híbrida Local-First** diseñada para baja latencia, alta trazabilidad y privacidad.

## 1. Capas de Almacenamiento

### Redis (Contexto Activo)
- **Session Memory (Memoria de Sesión)**: Almacena los últimos N mensajes de la conversación actual para contexto inmediato.
- **Message Buffer (Búfer de Mensajes)**: Retiene temporalmente eventos crudos antes de ser consolidados en la memoria a largo plazo.
- **Profile Cache (Caché de Perfil)**: Copia rápida del `UserProfile` (Perfil de Usuario) para la construcción veloz de prompts (instrucciones).

### SQLite + sqlite-vec (Memoria a Largo Plazo)
- **Tabla de Memorias**: El almacén definitivo para fragmentos de texto, hechos e historial de conversaciones.
- **Vector Search (Búsqueda Vectorial)**: Recuperación semántica usando embeddings (representaciones vectoriales) de 768 dimensiones (`gemini-embedding-001`).
- **Full-Text Search (Búsqueda de Texto Completo - FTS5)**: Recuperación léxica para coincidencias exactas de palabras clave.

## 2. Pipeline (Flujo) de Ingestión

Cada mensaje pasa por el siguiente flujo automatizado:
1.  **Buffering (Almacenamiento Temporal)**: Redis captura el evento.
2.  **Consolidation (Consolidación)**: Tras un umbral (N mensajes o tiempo), un trabajador se activa.
3.  **Extraction (Extracción)**: El `FactExtractor` identifica hechos atómicos y asigna **Provenance** (Procedencia).
4.  **Chunking (Fragmentación)**: El `RecursiveCharacterTextSplitter` divide el texto en piezas manejables.
5.  **Deduplication (Deduplicación)**: El hashing (resumen) SHA-256 evita el almacenamiento duplicado.
6.  **Persistence (Persistencia)**: Los datos se guardan en SQLite y se respaldan en Google Cloud Storage (GCS).

## 3. Provenance (Procedencia) y Privacidad

Cada fragmento de memoria lleva metadatos para asegurar que el asistente se mantenga fundamentado:
- **Source Type (Tipo de Origen)**:
    - `explicit`: Declaraciones literales del usuario.
    - `observed`: Comportamiento del sistema detectado.
    - `inferred`: Hipótesis del LLM (requiere verificación).
- **Confidence (Confianza)**: Puntuación 0.0 - 1.0 para inferencias.
- **Evidence (Evidencia)**: Fragmento de texto que justifica la memoria.
- **Sensitivity (Sensibilidad)**: Clasificación (Baja/Media/Alta) para disparar bucles de validación.

## 4. Retrieval (Recuperación - Búsqueda Híbrida)

Los fragmentos recuperados se ordenan usando **Reciprocal Rank Fusion (RRF)**:
- **Vector Weight (Peso Vectorial - 0.7)**: Prioriza el significado semántico.
- **Keyword Weight (Peso de Palabra Clave - 0.3)**: Asegura que se encuentren nombres o términos específicos.
- **Time Decay (Decaimiento Temporal - v0.7.0)**: Las memorias recientes reciben un impulso en el ranking (clasificación).

---
*Para detalles de implementación, ver `src/memory/`*
