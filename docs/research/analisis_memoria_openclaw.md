# Investigación: Arquitectura de Memoria OpenClaw

**Estado:** Referencia utilizada para el diseño de la Fase F de AEGEN.
**Fecha:** Febrero 2026

---

Este documento detalla la investigación sobre la arquitectura técnica de memoria utilizada por OpenClaw, que sirve como modelo de referencia para la evolución de AEGEN hacia un sistema Local-First.

---

## 1. Filosofía de Diseño: Local-First

OpenClaw prioriza la velocidad y la privacidad procesando la memoria localmente antes de sincronizar con la nube.

**Latencia Objetivo:** Menor a 10ms para búsquedas locales.

**Persistencia:** SQLite como motor transaccional.

**¿Persistencia, se refiere a que los datos queden guardados siempre?**
Sí. En informática, persistencia significa que la información sobrevive a la finalización del programa o al apagado del sistema. Los datos se escriben en el almacenamiento físico (SSD/Disco Duro) y no solo en la memoria RAM (que es volátil y se borra al reiniciar).

**¿Qué es un motor transaccional?**
Es un sistema que garantiza que las operaciones en la base de datos sean seguras mediante algo llamado ACID (Atomicidad, Consistencia, Aislamiento y Durabilidad). Básicamente, asegura que si intentas guardar algo y el sistema falla a mitad del proceso, la base de datos no se corrompa ni guarde datos a medias; o se guarda todo correctamente o no se guarda nada, volviendo al estado anterior al error.

**¿Osea que SQLite, es una base de datos y al mismo tiempo el motor que hace posible guardar los datos?**
Exactamente. SQLite es ambas cosas en un solo paquete. A diferencia de otras bases de datos como PostgreSQL o MySQL que necesitan un "servidor" aparte corriendo, SQLite es solo una librería que vive dentro de tu aplicación. El "motor" es el código que escribe los datos, y la "base de datos" es el archivo final que ves en tu carpeta. Es como si el editor de texto y el documento fueran una sola herramienta integrada.

**Independencia:** Capacidad de funcionar 100% offline con proveedores de embeddings locales.

---

## 2. Stack Tecnológico de Memoria

**¿Todo el almacenamiento es local?**
En la arquitectura de OpenClaw, sí. Todo se almacena en un archivo `.sqlite` dentro del mismo servidor o computadora donde corre el agente. Para AEGEN, la recomendación es usar este almacenamiento local en el servidor para ganar velocidad, pero manteniendo una copia en la nube (GCP) para respaldo y portabilidad.

**¿En caso de que se decidiera replicar a Openclaw en la gestion de los datos usando SQLite, Podriamos guardar estos archivos en el almacenamiento de google o en MV que estoy usando para desplegar la aplicación?, ¿Seria recomendable, se podria usar de forma gratuita asi sea con limites?**
Lo ideal y más recomendable es guardarlos en el disco de la **Máquina Virtual (MV)** que ya estás usando. Al estar en el disco local de la MV, el acceso es instantáneo (gratis, ya que el espacio en disco suele estar incluido en el costo de la MV). Guardarlos directamente en el "almacenamiento de Google" (como Cloud Storage) obligaría a descargar el archivo cada vez, lo cual sería lento y costoso. Mi sugerencia: trabajar en el disco de la MV para velocidad y enviar una copia al almacenamiento de Google una vez al día como respaldo de seguridad.

**Runtime:** Node.js 22+ (TypeScript).

**Base de Datos:** SQLite (Persistencia de texto y metadatos).

**Motor Vectorial:** `sqlite-vec` (Extensión escrita en C para búsqueda por similitud).

**Motor de Texto:** FTS5 (Full-Text Search integrado en SQLite).

**¿Cuál es la función de este motor de texto?**
Su función es la búsqueda literal o por palabras clave exactas. Mientras que la búsqueda vectorial entiende "conceptos" (ej. buscas "salud" y encuentra "bienestar"), el motor de texto FTS5 es excelente encontrando términos específicos, IDs, nombres propios, comandos o códigos de error que el modelo vectorial podría ignorar por no tener un "significado" semántico claro.

**¿Donde hace esta busqueda en la base de datos de SQLlite?**
La búsqueda se hace sobre una tabla especial llamada "Virtual Table". Cuando instalas FTS5, SQLite crea un índice gigante de cada palabra de tus textos. Cuando haces una búsqueda, SQLite no lee todos los archivos uno por uno; consulta ese índice (como el índice de un libro) para saber exactamente en qué fila está la palabra que buscas, lo que lo hace ridículamente rápido.

**¿Osea que los resumenes de la conversación que hace el llm se guradan en la base de datos SQLite y adicional se crea la tabla virtual especial y se van agergando nuevos indices a medida que aumenta la información y si hay nueva información que pueda tener el mismo indice que ya existe que pasa?, ¿osea que el motor primero busca el indice y luego va donde esta la información relaciona con ese indice y extrae la información, que tanta informacion extrae como hace para saber que tanta extraer?**
Así es. El resumen del LLM se guarda en la tabla principal de SQLite (donde está el texto completo). Al mismo tiempo, el motor FTS5 actualiza automáticamente su índice "virtual" con las palabras de ese nuevo resumen.
- **Si hay nueva información con el mismo índice:** (ej. dos conversaciones hablan de "vacaciones"), el índice de la palabra "vacaciones" simplemente añade una referencia más: "ahora aparece en el documento A y también en el documento B". No sobrescribe nada, solo agrega punteros.
- **Cómo extrae:** El motor busca en el índice, encuentra que la palabra está en el "Documento B, posición 50", y va directo allí.
- **Cuánta información extrae:** Extrae el fragmento (chunk) completo donde apareció la coincidencia. Como previamente dividimos el texto en bloques de 400 tokens (chunking), el sistema sabe que debe traerse solo ese bloque específico, no todo el historial de chat.

**¿Las conversaciones se gurdan literalmente en la base de datos?**
Depende de la configuración. En OpenClaw, se guarda una **interpretación o resumen** en la memoria de largo plazo (SQLite), pero se puede guardar la conversación **literal** en una tabla de "historial" diferente. Lo más valioso para la "memoria" del agente no es el historial palabra por palabra, sino los hechos extraídos (ej: "El usuario dijo que prefiere el color azul").

**Embeddings:** Abstracción multi-provider (OpenAI, Gemini, Local via llama.cpp).

---

## 3. Componentes Críticos del Sistema

### A. El Manager de Memoria (`src/memory/manager.ts`)

Orquestador de alto nivel que implementa las siguientes políticas:

**Chunking Recursivo:** Divide los documentos en bloques de 400 tokens con un 80 tokens de overlap. Esto asegura que el contexto no se corte abruptamente en los bordes del fragmento.

**¿Para qué se hace chunking?**
Se hace por dos razones principales: 1) Los modelos de IA tienen un límite de "contexto" (no pueden leer un libro entero para responder una pregunta pequeña) y 2) Los vectores (embeddings) son mucho más precisos cuando representan una sola idea o párrafo corto que cuando intentan resumir un documento largo. El chunking permite recuperar solo la pieza exacta de información necesaria.

**¿Los chunks se guardan con etiquetas especificas dependiendo el tema o caracteristicas?**
Sí, se guardan con **metadatos**. Cada chunk lleva etiquetas como: `chat_id`, `fecha`, `fuente` (ej: "telegram"), y a veces `entidades` (ej: nombres de personas mencionadas). Estas etiquetas permiten que el agente no solo busque por "significado", sino que pueda filtrar: "busca solo lo que hablamos sobre _finanzas_ en el chat de _Telegram_".

**Deduplicación por Hash:** Antes de procesar un chunk, genera un hash SHA-256. Si el hash ya existe en la DB, omite el paso de generación de embedding para ahorrar costos y tiempo.

**¿A qué se refiere con procesar un chunk, a consultarlo?**
En este contexto, "procesar" se refiere al momento de **guardarlo** (ingestión). Antes de enviar el texto a la API de Google o OpenAI para convertirlo en un vector (lo cual cuesta dinero y tiempo), el sistema calcula una "huella digital" única (hash).

**¿Entonces si ya se consultó ese chunk, ya existe el hash y no hay que consultarlo nuevamente, ya hay una preconsulta? ¿Pero dónde está esa preconsulta?**
La "preconsulta" ocurre localmente en la base de datos SQLite antes de llamar a la API externa. Si el sistema ve que esa huella digital (hash) ya está en la base de datos, significa que ya tenemos ese texto guardado y su vector correspondiente. Así, no gasta recursos volviendo a generar un embedding para algo que ya conoce.

**Gestión de Colecciones:** Organiza la memoria por espacios (namespaces) o `chat_id`.

**¿Esto se guarda en SQLite?**
Sí. SQLite permite usar columnas adicionales para filtrar. Por ejemplo, cada fila de memoria tiene una columna `chat_id`. Cuando el agente busca, SQLite filtra instantáneamente para que solo vea los recuerdos que pertenecen a ese usuario o chat específico.

### B. Búsqueda Híbrida (`src/memory/hybrid.ts`)

**¿Hay dos formas de guardar los datos en una base de datos vectorial de sqlite, una textual en sqlite?**
Sí, exactamente. Se guardan "espejeados". El texto legible se guarda en una tabla normal (o FTS5) para búsquedas de palabras exactas, y su representación matemática (el vector) se guarda en la tabla de `sqlite-vec`. La búsqueda híbrida consulta ambas tablas al mismo tiempo y combina los resultados.

**Búsqueda Semántica:** Usa el vector generado para encontrar fragmentos con significados similares (ej: buscar "salud" encuentra "bienestar").

**Búsqueda por Keywords:** Usa FTS5 para encontrar términos exactos, códigos, comandos o nombres propios que el modelo vectorial podría ignorar.

**Ranking (RRF):** Combina ambas listas con pesos configurables (típicamente 0.7 Vector / 0.3 Keyword).

### C. Sistema de Cache de Embeddings

OpenClaw mantiene una tabla dedicada para cachear vectores de texto comunes. Si un agente genera el mismo texto frecuentemente, el sistema recupera el vector de la DB en lugar de llamar a la API externa.

**¿Dónde se guarda este cache, o sea que el cache es de la base vectorial sqlite-vec? ¿A qué API hace el llamado?**
El cache se guarda en una tabla estándar de SQLite (texto -> vector). La API a la que se refiere es el proveedor de embeddings (como la API de Google Gemini o OpenAI). Si el texto es "Hola usuario", y ya tenemos su vector en el cache local, no necesitamos llamar a Google para que nos diga cuál es su vector; lo sacamos de nuestra propia base de datos local en milisegundos.

**¿Cuando openclaw esta funcionando offline, que pasa con la vectorización?**
Si está offline, OpenClaw utiliza un **modelo local** (como los de la librería `transformers` o `llama.cpp`) para generar el vector. En lugar de enviar el texto a Google, usa el procesador de tu computadora para calcular el vector matemático. Es más lento que una API potente, pero permite que el sistema de memoria siga funcionando sin internet.

---

## 4. Flujos de Trabajo (Data Pipelines)

### Ingestión de Memoria

**Entrada:** Texto Markdown de la sesión o documentos externos.

**¿Qué características tiene?**
Suele ser texto estructurado. El formato Markdown es ideal porque es ligero y permite a la IA distinguir fácilmente entre encabezados, listas y metadatos (quién habló, cuándo y en qué contexto).

**Preprocessing:** Normalización de texto y metadatos.

**¿Qué tipo de normalización, qué se hace exactamente en este paso?**
Se limpia el texto: se eliminan espacios en blanco excesivos, se estandarizan formatos de fecha, se eliminan caracteres que no aportan valor y se fragmenta el texto de forma que cada parte mantenga sus metadatos (ej: "este párrafo pertenece al Chat X, del día Y"). Esto asegura que la base de datos esté "limpia" para búsquedas eficientes.

**¿Este preprocesing es el mismo que hace el llm con la interpretación y resumen?**
No, son pasos distintos.
1. **Interpretación del LLM:** Es "inteligente". El modelo lee el chat y escribe un resumen lógico (ej: "Usuario interesado en Python").
2. **Preprocessing (este paso):** Es "mecánico" y ocurre después. Toma ese resumen que escribió el LLM y lo limpia técnicamente (quita emojis raros, normaliza mayúsculas/minúsculas, asegura que la fecha esté en formato ISO `2024-02-07`). Es fontanería de datos, no inteligencia.

**Splitting:** Aplicación del algoritmo de chunking.

**Embedding:** Generación asíncrona de vectores (batch processing si es posible).

**Commit Atómico:** Escritura en SQLite asegurando integridad entre el texto y su representación vectorial.

**¿Puedes profundizar en esto del commit atómico?**
Es como un pacto de "todo o nada". Cuando guardas una memoria, tienes que escribir el texto en una tabla y el vector en otra. Si escribes el texto pero la luz se va antes de escribir el vector, tendrías una base de datos "coja". El **Commit Atómico** le dice a SQLite: "Prepara estos dos cambios, y solo ejecútalos si ambos están listos". Si algo falla, SQLite revierte todo como si nunca hubieras intentado guardar nada, manteniendo la base de datos siempre sana.

### Recuperación (Retrieval)

**Query Expansion:** El LLM puede reformular la pregunta del usuario para mejorar la búsqueda.

**Vectorización:** La query se convierte en vector.

**Search Loop:** Ejecución de consultas paralelas en SQLite (`sqlite-vec` + FTS5).

**Post-processing:** Filtrado por relevancia y ordenación por fecha/importancia.

**Context Injection:** Los fragmentos se inyectan en el prompt del agente como "Conocimiento de largo plazo".

**¿Cómo así conocimiento de largo plazo?**
Se refiere a información que no es parte de la conversación inmediata (que está en Redis o memoria de corto plazo), sino datos de hace días, semanas o meses que el agente "extrae" de su base de datos permanente para responder con contexto histórico.

✨ **[NUEVA PREGUNTA] ¿Cuando una conversación esta activa, donde se gurada el historial de esta conversación?**
En OpenClaw, el historial de la conversación activa se mantiene en la **memoria RAM** del proceso (dentro de una variable o array de Node.js). A diferencia de AEGEN que usa Redis para esto, OpenClaw prefiere no depender de servicios externos para su funcionamiento básico, manteniendo el contexto inmediato lo más cerca posible del procesador.

✨ **[NUEVA PREGUNTA] ¿Solo se procesa la conversación cuando la sesión termina?**
Generalmente sí. Procesar cada mensaje en tiempo real (generar embeddings y guardarlos) sería muy ineficiente y ruidoso. Al terminar la sesión, se tiene el panorama completo, lo que permite al LLM hacer un resumen mucho más coherente y útil para la memoria de largo plazo.

✨ **[NUEVA PREGUNTA] ¿Procesar la conversación es hacer chunks y guardarlos en las dos bases de datos?**
Correcto, pero con un filtro previo. No se guardan los mensajes "crudos" uno por uno. El proceso es:
1. El LLM extrae los puntos clave de la sesión.
2. Esos puntos clave se dividen en chunks (si son extensos).
3. Se guardan en la tabla de texto (SQLite) y en la tabla vectorial (sqlite-vec).

✨ **[NUEVA PREGUNTA] ¿Cada que entra un mensaje nuevo el agente toma el mensaje y evalua si necesita memoria de largo plazo o no, si no necesita memoria de largo plazo solo usa los datos de la memoria actual para mantener el contexto?**
Exactamente. OpenClaw inyecta los mensajes recientes de la sesión activa directamente en el "prompt" del agente (memoria de trabajo). El agente solo "decide" buscar en la base de datos de largo plazo si detecta que la pregunta del usuario requiere información que no está en esos mensajes recientes. Por ejemplo:
1. Mensaje: "Hola". Contexto: "Hola". No busca en memoria.
2. Mensaje: "¿Qué te dije el mes pasado sobre mi proyecto?". El agente ve que no tiene el mes pasado en su RAM y activa la herramienta de búsqueda en SQLite.

---

## 5. Integración con el Ecosistema

OpenClaw integra este sistema de forma transparente:

**Hooks:** Un hook de fin de sesión guarda automáticamente el historial del chat como nuevas memorias.

**¿Explica qué es un hook, dónde se guarda el historial, se guarda literal el historial o alguna interpretación del LLM?**
Un "hook" es un disparador automático; una función que se ejecuta sola cuando ocurre un evento (ej: cuando el usuario cierra la sesión). El historial no suele guardarse "literal" (palabra por palabra de todo el chat) porque sería ineficiente. Normalmente, se le pide al LLM que haga una **síntesis o interpretación** de lo más importante ("El usuario mencionó que tiene una cita el lunes") y eso es lo que se guarda en la base de datos de largo plazo para futuras consultas.

✨ **[NUEVA PREGUNTA] ¿esta es la información que se gurada en chunks en la base de datos SQLite, y en la base de datos vectorial SQLite-vec?**
Sí. La interpretación refinada por el LLM es la que se somete al proceso de chunking y se indexa en ambas partes de la base de datos para asegurar que sea recuperable tanto por significado (vector) como por palabras clave (FTS5).

✨ **[NUEVA PREGUNTA] ¿Como se detecta el final de una sesion?**
En OpenClaw (que es mayormente CLI), el final se detecta cuando el usuario cierra el programa o envía un comando de salida. En un entorno de servidor (como el que queremos para AEGEN), se detecta por un "timeout" de inactividad (ej. 30 minutos sin mensajes) o porque el estado de la sesión se marca explícitamente como cerrada.

**Tools:** Los agentes tienen una herramienta `memory-search` que pueden invocar activamente si necesitan datos específicos del pasado.

✨ **[NUEVA PREGUNTA] ¿Como se determina como usar la herramienta, pura interpretación del agente?**
Es 100% interpretación del agente. En su sistema de instrucciones, el agente sabe que tiene una herramienta llamada `memory-search`. Cuando el usuario hace una pregunta que el agente no puede responder con su contexto actual, el agente genera un pensamiento interno: "Necesito datos históricos, voy a llamar a `memory-search` con estos términos". No hay una regla fija, es la propia inteligencia del modelo la que decide cuándo le falta información.

---

## 6. Diferencias Clave y Sugerencias para AEGEN

**Diferencias Actuales:**
AEGEN usa actualmente Google File API (Cloud) con latencias de 0.5s a 2s, mientras que OpenClaw usa SQLite Local con latencias menores a 0.01s. AEGEN no tiene chunking (envía archivos enteros), lo que reduce la precisión y aumenta el consumo de tokens.

**Sugerencias para AEGEN (Arquitectura y Fricción):**
El ecosistema de AEGEN no está pensado para funcionar 100% local, ya que los usuarios acceden mediante Telegram, WhatsApp, etc. Para mejorar la arquitectura actual manteniendo la mínima fricción:

1.  **Backend con Memoria Local:** El servidor donde corre AEGEN debe tener su propia base vectorial local (como ChromaDB o SQLite-vec). Esto permite que el agente responda instantáneamente a los mensajes de Telegram/WhatsApp sin esperar a la nube de Google.
2.  **Sincronización en Background:** Guardar los datos localmente para velocidad, y usar una tarea en segundo plano (asíncrona) para subir un respaldo a Google Cloud. Así, si el servidor falla, los datos no se pierden, pero la velocidad del usuario no depende de la nube.
3.  **Embeddings via API:** Seguir usando la API de Gemini para generar los vectores (ahorra RAM en tu servidor), pero guardarlos y buscarlos localmente.

**¿Esta parte (Chunking) se refiere a cómo se guardan los datos en la base de datos?**
Sí, exactamente. Se refiere a la estructura de almacenamiento. En lugar de guardar un documento como un solo registro gigante, lo guardas como cientos de registros pequeños e independientes. Esto es lo que permite que, al buscar, la base de datos te entregue solo el párrafo exacto que resuelve la duda del usuario, en lugar de obligar a la IA a leer todo el documento de nuevo.

---

## 7. Conclusiones para la Implementación en AEGEN

Para alcanzar el nivel de OpenClaw, AEGEN debe:
1.  Adoptar una base de datos vectorial local (como ChromaDB o SQLite con extensiones) en el servidor.
2.  Implementar el pipeline de chunking antes de cualquier almacenamiento para mejorar la precisión.
3.  Configurar la sincronización con Google Cloud como un proceso de respaldo y no como el paso principal de búsqueda.
