# Análisis Crítico y Estratégico: Eficiencia de Tokens, RAG Dinámico y Evolución de Memoria en AEGEN

- **Fecha:** 22 de Mayo de 2026
- **Autores:** MAGI AI & Lead Architect
- **Estado:** En Revisión (Estratégico)

---

## 1. Introducción y Cronología del Problema

El sistema de memoria de AEGEN (MAGI) experimentó recientemente fallos críticos de estabilidad en entornos de producción (Google Cloud VM), manifestados principalmente en errores `413 Request too large` (Rate Limit Exceeded en TPM) al utilizar el motor de Groq (`gpt-oss-120b`).

Al desglosar los logs forenses, se identificó que el sistema estaba atrapado en un bucle infinito de fallos debido a que:
1. **La Consolidación Episódica paralela** (doble disparo) leía un búfer acumulado sin bloqueo distribuido en Redis, duplicando el procesamiento.
2. **El búfer de mensajes no se limpiaba en Redis al fallar el LLM**, provocando que en cada interacción subsiguiente el payload de mensajes creciera exponencialmente (superando los 8,000 tokens de límite estricto de Groq).
3. **El especialista de TCC (`cbt_specialist`)** colapsaba con payloads de hasta 9,554 tokens en conversaciones en vivo.

Aunque se aplicaron parches inmediatos (bloqueo por Redis Lock, reducción de umbrales a 10 mensajes, y recorte de búfer a 10 mensajes seguros), esto abrió una discusión mucho más profunda: **¿Por qué MAGI necesita el equivalente a 20 páginas de un libro en su prompt de sistema para responder a una interacción cotidiana de Telegram? ¿Cómo diseñamos una arquitectura verdaderamente inteligente, eficiente y scalables para soportar transcripciones masivas (como canales de YouTube) y libros clínicos en el futuro?**

---

## 2. Radiografía del Desperdicio de Tokens en la Arquitectura Actual

Al analizar con rigor la ingesta y la recuperación actuales, identificamos que el sistema es ineficiente en tres capas fundamentales:

### A. La Ingesta de Fuerza Bruta (`RecursiveChunker`)
- **Comportamiento Actual:** El chunker actual divide los textos crudos (PDFs de libros clínicos o transcripciones automáticas de YouTube) de manera lineal cada 400 tokens con overlap de 80.
- **El Ruido:** Este enfoque a ciegas guarda metadatos huérfanos, números de página, saludos, muletillas (*"eh...", "como les decía...", "suscríbete al canal"*) y frases cortadas por la mitad en la base de datos vectorial de SQLite.
- **Consecuencia:** Al recuperar información, el buscador de similitud inyecta "basura" cruda directamente en el prompt del LLM, degradando el contexto cognitivo y saturando la ventana de tokens sin aportar valor terapéutico real.

### B. Recuperación Estática (El RAG Rígido)
- **Comportamiento Actual:** La herramienta de TCC (`tools.py`) recupera **siempre** de forma fija 3 fragmentos globales y 2 fragmentos del usuario.
- **El Desperdicio:** Si el usuario envía un mensaje casual (*"Hola MAGI, ¿cómo estás?"*), el RAG de TCC sigue realizando la búsqueda e inyectando de 1,000 a 2,000 tokens del RAG en el prompt de sistema del especialista. Es un desperdicio absoluto de tokens y potencia de cómputo para un mensaje que no requiere contexto clínico.

### C. Amnesia y Crecimiento Acumulativo de Hechos (`structured_knowledge`)
- **Comportamiento Actual:** El extractor de hechos (`FactExtractor`) añade hechos al JSON del usuario de forma lineal.
- **El Ruido Cognitivo:** A medida que la conversación progresa a lo largo de meses, este JSON acumula hechos antiguos que pueden contradecirse con hechos nuevos (*"El usuario está estresado por el proyecto X"* vs. *"El usuario completó el proyecto X"*), saturando el prompt con información desactualizada. No hay noción de decaimiento del tiempo o consolidación semántica.

---

## 3. Puntos Ciegos Clave Identificados en la Arquitectura

### A. Falta de "Metadatos Temporales" en Vectores (Amnesia del Decaimiento Temporal)
- **El Problema:** Si le dices a MAGI *"Hoy inicié el día con movimiento"* y el buscador vectorial recupera fragmentos de usuario, encontrará esta frase. Pero para el algoritmo vectorial clásico, un vector registrado hoy y uno registrado hace un año tienen exactamente el mismo peso matemático si el texto coincide. El sistema carece de perspectiva temporal de lo que es actual frente a lo que ya pertenece al pasado.
- **Solución de Vanguardia (Time-Weighted Vector Search):** En lugar de buscar exclusivamente por la similitud de coseno, la fórmula de la búsqueda híbrida debe multiplicar la similitud por un decaimiento temporal exponencial:
  $$Score_{final} = Similitud \times e^{-\lambda t}$$
  Donde $t$ es la edad del fragmento y $\lambda$ es la tasa de decaimiento. De esta forma, los recuerdos y hechos recientes de tu vida tienen peso de forma natural, a menos que un hecho muy antiguo sea sumamente relevante (similitud semántica altísima).

### B. Ingesta Ineficiente de YouTube (La Pesadilla de los Transcripts Crudos)
- **El Problema:** Las transcripciones generadas automáticamente en YouTube carecen de puntuación (puntos, comas) y están plagadas de muletillas, pausas, silencios e interrupciones ajenas al conocimiento real del video. Partir esto de forma lineal con overlap inyecta texto inútil y confunde al LLM.
- **Solución (Semantic Chunking & Agentic Distillation):**
  1. **Semantic Chunking:** En lugar de cortes de caracteres fijos, se evalúan las diferencias en la distancia semántica de las oraciones consecutivas. El chunk se corta naturalmente solo cuando hay un salto semántico en el tema que se expone.
  2. **Agentic Distillation (Destilación en Ingesta):** Antes de persistir y vectorizar el chunk, un LLM de alta velocidad y bajo costo (Gemini 2.5 Flash Lite) purifica y reescribe la transcripción a prosa limpia, profesional y altamente estructurada en Markdown, abstrayendo conceptos clave, entidades y sentimiento en metadatos específicos.

---

## 4. Técnicas de RAG de Próxima Generación (2026) para MAGI

### A. Reranking Semántico (Coherence Filtering)
- **Cómo Funciona:** El buscador semántico clásico (Dense Retrieval) es excelente para recuperar rápidamente 20 candidatos semánticos candidatos de manera barata, pero carece de un criterio fino de relevancia clínica.
- **El Proceso:** Estos 20 fragmentos se envían a un **Reranker** (un modelo cross-encoder ligero y local). El Reranker reordena los fragmentos basándose en la coherencia estricta de la pregunta del usuario, y se queda solo con los **3 mejores**, reduciendo instantáneamente el 85% de los tokens basura antes de llamar al LLM del chat.

### B. Graph-RAG (Conocimiento Terapéutico Conectado)
- **Cómo Funciona:** En lugar de buscar sobre fragmentos de texto planos y huérfanos, construimos un **Knowledge Graph (Grafo de Conocimiento)** relacional en SQLite donde los nodos son *Conceptos* o *Personas* (ej. "Usuario", "Sentadillas", "Ansiedad", "Energía") y las aristas son las *Relaciones* entre ellos (ej. "Hacer sentadillas -> Aumenta -> Energía").
- **Por Qué es Revolucionario:** Permite a MAGI realizar razonamiento clínico y "multi-salto". Si le dices *"el lío es tener cada mañana la fuerza para moverme"*, el Grafo permite conectar que *"Moverse está ligado a tu meta de Vitalidad, pero choca con tu creencia de Fatiga Mental registrada el mes pasado"*. Esto produce análisis terapéuticos infinitamente superiores.

### C. El Cerebro Virtual del Usuario: Arquitectura de Grafo Jerárquico (Obsidian-like)
- **El Concepto:** Almacenar la información que proporciona el usuario no como datos aislados, sino como un "cerebro virtual" de notas interconectadas mediante etiquetas y múltiples niveles de profundidad, inspirado en la aplicación Obsidian.
- **Análisis Crítico:**
  - *Pros:* Crea una memoria asociativa multiresolución. Permite conectar un patrón de sueño aislado con una rutina de ejercicio específica a través de etiquetas, dándole a MAGI la capacidad de deducir correlaciones profundas y hacer "Zoom In/Out" del contexto dependiendo del requerimiento específico del usuario en un momento dado.
  - *Contras:* Las etiquetas de texto manuales estáticas (ej. `#estrés`) son rígidas y tienden a romperse si el agente nombra las cosas de forma diferente (ej. `#ansiedad`). Las búsquedas de árboles profundos en SQLite plano (`WITH RECURSIVE`) pueden generar latencia alta.
- **Solución Integradora (Hierarchical GraphRAG):** Evolucionar de un modelo de "etiquetas estáticas" a una **Detección Automática de Comunidades**. Un agente extrae dinámicamente "Entidades" y "Relaciones" del mensaje del usuario y un algoritmo matemático las agrupa en diferentes niveles jerárquicos de forma automatizada (ej. Nivel 3 atómico: sentadillas hoy; Nivel 2: rutinas físicas; Nivel 1: gestión de vitalidad). El enrutador decide a qué nivel de profundidad acceder basado en la intención de la pregunta del usuario.

### D. Namespaces Dinámicos (Virtual Repositories)
- **Cómo Funciona:** Al inyectar transcripciones de canales completos de YouTube o libros clínicos pesados, no podemos mezclarlos en el mismo saco semántico. Cada recurso tiene su propio namespace en SQLite.
- **El Beneficio:** MAGI puede conmutar selectivamente: *"Para esta interacción clínica de TCC, voy a buscar solo en el namespace 'Canal_Psicologia_X' y 'Libro_Beck_TCC'"*, previniendo la contaminación de contexto y falsos matches semánticos.

### E. Caché Semántico en Redis (Semantic Cache)
- **Cómo Funciona:** Si haces preguntas repetitivas o similares, el sistema no tiene por qué llamar al RAG ni al LLM en cada interacción. Un caché semántico en Redis compara la similitud semántica del mensaje entrante con consultas anteriores en milisegundos.
- **El Beneficio:** Si la similitud es casi idéntica, el caché devuelve directamente la respuesta sintetizada previa, reduciendo costos de tokens y latencia de API a **cero**.

---

## 5. Análisis Crítico de Alternativas Arquitectónicas

Durante el debate, se analizaron diferentes técnicas para resolver estos problemas. A continuación, se presenta un desglose de las alternativas, evaluando sus pros, contras e impacto real:

### Alternativa 1: Cambiar de LLM a Gemini 2.5 Flash Lite (Ignorar la Eficiencia)
- **Concepto:** Migrar la herramienta y la consolidación a Gemini, el cual posee una ventana de 1 millón de tokens a un costo extremadamente bajo ($0.10 por millón de input tokens).
- **Crítica:** **Es un antipatrón de diseño.** Aunque resuelve el error de infraestructura, no soluciona el ruido cognitivo. Cargar "basura" o datos duplicados a un modelo con contexto masivo sigue degradando la precisión y la calidad de la respuesta final del agente. El sistema debe ser inherentemente eficiente e inteligente, independientemente de los costos del LLM.

### Alternativa 2: Arquitectura Parent-Child RAG (Padre-Hijo)
- **Concepto:** Guardar Chunks Padres grandes (1,200 tokens) para conservar coherencia de lectura, y vectorizar únicamente Chunks Hijos pequeños (150 tokens) para la búsqueda semántica. Al hacer match, se inyecta el Chunk Padre completo.
- **Crítica:** Si bien la técnica de base de datos Padre-Hijo evita las frases cortadas y mejora la legibilidad, **por sí sola no resuelve la eficiencia del sistema**:
  - Si el documento origen tiene paja, el Chunk Padre recuperado seguirá inyectando paja en el prompt.
  - No soluciona el problema de inyectar RAG en interacciones casuales (mensajes vacíos de contenido clínico).
  - Sigue sin resolver la evolución e inteligencia temporal de los hechos del usuario.

### Alternativa 3: RAG Dinámico por Umbral Semántico (Score Gating)
- **Concepto:** Eliminar la inyección estática de fragmentos. Aplicar un umbral matemático (ej. `similarity_score >= 0.70`).
- **Crítica:** **Altamente eficiente.** Si el usuario envía un mensaje que no tiene relación semántica con los libros o hechos clínicos, el RAG inyecta **0 fragmentos**, reduciendo el tamaño del prompt a su mínima expresión en el 90% del chat cotidiano, y reservando los tokens del RAG únicamente cuando son clínicamente indispensables.

### Alternativa 4: Semantic Ingestion Pipeline (Destilación en la Ingesta)
- **Concepto:** Antes de guardar la información en la base de datos (especialmente transcripts de YouTube con saludos y muletillas), un agente ligero destila el texto, extrayendo únicamente principios estructurados, conceptos clave y hechos en un formato limpio (ej. Markdown). Solo se vectoriza y persiste la sustancia útil.
- **Crítica:** **Crucial para la escalabilidad.** Es la única forma de procesar canales enteros de YouTube o libros masivos sin contaminar la base de datos vectorial de SQLite con miles de tokens basura.

---

## 6. La Arquitectura Integradora Definitiva (Los Tres Pilares)

La arquitectura definitiva de AEGEN para el manejo de memoria a largo plazo no debe ser un parche temporal ni una solución de fuerza bruta basada en modelos gigantes. Debe estructurarse bajo los siguientes **tres pilares de eficiencia y calidad cognitiva**:

```
[Ingesta Destilada] ──> [Base de Datos Vectorial] ──> [Filtro de Umbral Semántico] ──> [Prompt de MAGI]
 (LLM Limpia Ruido)      (Parent-Child Opcional)        (RAG Dinámico > 0.70)          (Eficiente y Denso)
```

### Pilar I: La Ingesta Limpia y Destilada (Semantic Ingestion)
- Toda transcripción de YouTube o documento se procesa primero por un agente de destilación que elimina muletillas, saludos y formato.
- El conocimiento se almacena en SQLite en formatos limpios y estructurados.

### Pilar II: RAG Adaptativo con Umbrales Dinámicos y Decaimiento Temporal
- Implementar un filtro en `VectorMemoryManager` que evalúe la similitud semántica.
- Los fragmentos de RAG solo se inyectan en el prompt si la similitud semántica es alta. De lo contrario, se ahorran esos tokens por completo.
- El sistema calcula dinámicamente un "presupuesto de tokens" (Token Budgeting) al vuelo basado en la longitud del chat actual antes de llamar a la API.

### Pilar III: Consolidación Evolutiva Temporal (Graph Knowledge Base)
- El `EvolutionDetector` e `IncrementalExtractor` no deben acumular datos de forma infinita en el JSON.
- El sistema debe tener un mecanismo de "unificación y olvido semántico", donde los hechos viejos contradictorios o resueltos se consolidan en narrativas cortas o se archivan en el almacén vectorial histórico, manteniendo el perfil activo en Telegram siempre corto, conciso y de alta relevancia clínica.

---
*Este documento unifica el debate arquitectónico y servirá de base de diseño para la implementación de las siguientes fases de desarrollo del subsistema de memoria en AEGEN.*
