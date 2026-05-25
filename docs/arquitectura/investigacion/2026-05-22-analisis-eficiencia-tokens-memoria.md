# Especificación de Arquitectura: Eficiencia de Tokens, Cerebro Virtual y Graph-RAG Dinámico

- **Fecha:** 22 de Mayo de 2026
- **Autores:** Lead Architect & MAGI AI
- **Estado:** Aceptado (Base de Diseño de Producción)

---

## 1. Definición del Problema y Radiografía de Ineficiencia

El sistema de memoria original de AEGEN experimentó fallos de estabilidad en producción (Google Cloud VM), manifestados en errores `413 Request too large` (Rate Limit de 8,000 Tokens Por Minuto en Groq `gpt-oss-120b`). Estos fallos son el síntoma de una ineficiencia estructural en tres capas:

### A. Ingesta de Fuerza Bruta Lineal
- **El Bug:** El chunker tradicional corta textos clínicos y transcripciones de YouTube a bloques lineales rígidos de 400 tokens sin criterio semántico.
- **Consecuencia:** Se almacenan y vectorizan muletillas (*"suscríbete al canal"*, *"eh..."*), números de página y frases rotadas por la mitad. Al buscar, se inyecta "basura" cruda que satura la ventana de tokens sin aportar valor terapéutico real.

### B. Recuperación Estática (El RAG Rígido)
- **El Bug:** La herramienta de TCC recupera siempre 3 fragmentos globales y 2 de usuario.
- **Consecuencia:** Incluso si el usuario envía un mensaje casual de saludo (*"Hola, ¿cómo estás?"*), el RAG inyecta de 1,000 a 2,000 tokens innecesarios de teoría clínica en el prompt de sistema del especialista.

### C. Ruido Cognitivo por Crecimiento de Hechos (`structured_knowledge`)
- **El Bug:** El extractor de hechos añade información de forma lineal a un JSON plano.
- **Consecuencia:** Con los meses, el JSON acumula hechos viejos irrelevantes o contradictorios (*"Usuario estresado por Proyecto X"* vs *"Usuario completó con éxito el Proyecto X"*), saturando el prompt con datos desactualizados y sin orden temporal.

---

## 2. La Solución Arquitectónica Elegida (Los Tres Pilares)

Para construir un sistema cognitivo de nivel mundial que sea estable en Groq (8k TPM), soporte transcripciones masivas de canales de YouTube y libros, y entregue una comprensión profunda del usuario, se adopta de forma integrada la siguiente **Arquitectura de Memoria Asociativa Multiresolución (Obsidian-like)**:

```text
                  ┌────────────────────────────────────────┐
                  │   Pilar I: Semantic Ingestion (LLM)    │
                  │   Destila & clasifica en 4 Niveles     │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │   Pilar III: Cerebro Virtual (SQLite)  │
                  │   Grafo Relacional + Notas Evolutivas  │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │   Pilar II: RAG Dinámico (Redis+SQL)   │
                  │   Caché Evolutivo -> GraphRAG -> Rerank│
                  └────────────────────────────────────────┘
```

---

### Pilar I: Ingesta Jerárquica Multinivel Asistida por Destilación

Descartamos la ingesta por fuerza bruta. El nuevo estándar de ingesta se estructura en una **Red Jerárquica Multinivel (Cerebro Virtual)**. Dado que la información proviene de orígenes fundamentalmente distintos, la arquitectura implementa una bifurcación ontológica estricta:

1. **Ingesta Asíncrona Diferenciada:**
   - **Fuentes Externas (Libros, YouTube):** Un agente ligero (Gemini) purifica el texto entrante, elimina ruido y aplica formato estructurado antes de guardar.
   - **Fuentes Internas (Chat del Usuario):** Los mensajes se guardan en el búfer de forma inmediata (cruda) para garantizar 0 latencia en la interacción de Telegram. Es el proceso en background del Pilar III el que posteriormente los destila y clasifica.
2. **Doble Ontología Jerárquica:**
   - **Ontología Semántica (Fuentes Externas):**
     - Nivel 1: Conceptos Clínicos Universales (ej. Terapia Cognitiva).
     - Nivel 2: Marcos Teóricos (ej. Distorsiones Cognitivas).
     - Nivel 3: Técnicas (ej. Reestructuración).
     - Nivel 4: Fragmentos purificados del libro o video.
   - **Ontología Episódica (Fuentes Internas):**
     - Nivel 1: Macro-narrativa de Vida (Línea de tiempo general y estado global).
     - Nivel 2: Áreas de Vida Agnosticas (Psicología, Finanzas, Fitness, Nutrición).
     - Nivel 3: Patrones y Rutinas (ej. Hábitos matutinos, Presupuesto mensual, Progresión de cargas).
     - Nivel 4: Eventos Atómicos y Métricas (ej. Mensaje de ánimo, Gasto: $50 en café, Entrenamiento: Sentadilla 100kg, Calorías: 2000kcal).
3. **Mapeo Relacional Transversal (Grafo Verdadero):** Además de la relación jerárquica (`parent_id`), el pipeline utilizará una tabla adicional `memory_edges` (`origen_id`, `destino_id`, `tipo_relacion`) para establecer asociaciones directas entre distintos dominios, materializando el Graph-RAG.

---

### Pilar II: RAG Adaptativo, Tiempo y Recuperación Cognitiva

Rechazamos los umbrales matemáticos rígidos y los cachés de respuesta estática. El motor de recuperación debe poseer conciencia temporal y adaptabilidad clínica:

1. **Caché del Estado Cognitivo Unificado (Redis):**
   - *Corrección de Arquitectura:* Un caché semántico tradicional de "respuesta exacta" es inútil terapéuticamente. MAGI no puede responder siempre igual ante la misma queja.
   - *La Solución:* Redis almacenará el **Estado Cognitivo Pre-calculado** (la Nota Evolutiva generada por el Pilar III). Cuando el usuario habla, MAGI accede a esta nota en Redis con latencia de 0ms, obteniendo la foto temporal exacta y la evolución del usuario sin tener que hacer una búsqueda en SQLite, unificando la evolución a largo plazo con la velocidad de memoria a corto plazo.
2. **Graph-RAG Relacional (Análisis Transversal):**
   - El buscador recupera sub-grafos relacionales que conectan múltiples dominios mediante la tabla `memory_edges` (ej. *Déficit calórico -> incrementa -> Irritabilidad -> dispara -> Gasto impulsivo*). Esto dota a MAGI de razonamiento analítico "multi-salto", cruzando métricas duras con variables blandas.
3. **Filtro Rígido Pre-Búsqueda y Jerarquía Dinámica:**
   - La estructura de metadatos será obligatoria (ej. `{"domain": "fitness", "hierarchy_level": 3, "timestamp": 1716382910}`). Esto permite aplicar un filtro SQL `WHERE` previo a la consulta vectorial, ahorrando un inmenso costo computacional.
   - Preguntas macro traen el resumen Nivel 1. Preguntas micro apuntan al Nivel 4. Esto reduce el tamaño del prompt hasta un 90%.
4. **Reranker Semántico:** Un cross-encoder local filtra el sub-grafo recuperado para garantizar que solo se inyecte al LLM información 100% coherente con la pregunta actual.

---

### Pilar III: Consolidación Evolutiva Temporal

El conocimiento episódico del usuario no debe acumularse infinitamente en un JSON plano. Se adopta un modelo de consolidación temporal que delega el cómputo pesado a background:

1. **Two-Stage Retrieval (Motor Matemático Híbrido):**
   - *El Problema Técnico:* `sqlite-vec` es extremadamente rápido para buscar similitud pura, pero no permite inyectar fórmulas matemáticas exponenciales de tiempo en su motor interno.
   - *La Solución:* (Fase 1) SQLite devuelve los Top-100 resultados por similitud semántica pura. (Fase 2) En Python, se aplica la fórmula de decaimiento: $$Score_{final} = Similitud \times e^{-\lambda t}$$ a esos 100 resultados, extrayendo los 10 o 15 de mayor prioridad crónica. Esto entrega al agente un contexto perfecto y reciente.
2. **El Motor Cognitivo (Notas de Evolución Multidisciplinar mediante LLM en Background):**
   - El agente de consolidación lee esos eventos atómicos filtrados (sean financieros, físicos o emocionales) y redacta una **Nota de Progreso Analítica de Nivel 1/2**. Esta misma nota se propaga al caché de Redis del Pilar II.
   - *Ejemplo de Evolución:* En lugar de inyectar 30 reportes diarios aislados, MAGI solo lee una nota estructurada: *"El usuario ha mantenido un déficit calórico constante durante 3 semanas... sin embargo, esto ha correlacionado con una desviación en su presupuesto"*.
3. **Recolección de Basura Cognitiva (Garbage Collection):**
   - A medida que el agente de consolidación crea nuevas narrativas en Niveles 1 y 2, tiene la capacidad de aplicar un *Soft Delete* (`is_active = 0`) a los vectores atómicos del Nivel 4 que ya han sido asimilados o resueltos. Esto previene el crecimiento infinito de la base de datos y mantiene las consultas vectoriales rápidas y puras.

---

## 3. Consideraciones de Implementación

- **Estructura DB (Grafo):** La tabla `memories` adoptará el campo opcional `parent_id` para profundidad, y se creará la tabla `memory_edges` para las conexiones transversales (Graph-RAG verdadero).
- **Esquema de Metadatos:** Será estrictamente tipado (Validado por Pydantic) garantizando que todo recuerdo ingrese con `domain`, `hierarchy_level` y `timestamp` para filtrado SQL optimizado.
- **Mitigación de Riesgos de Rendimiento:** La separación del *Two-Stage Retrieval* y el traslado del análisis cognitivo pesado a procesos asíncronos en background asegura que la experiencia del usuario final en Telegram se mantenga por debajo del segundo de latencia.
