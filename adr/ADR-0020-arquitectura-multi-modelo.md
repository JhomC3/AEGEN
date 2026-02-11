# ADR-0020: Arquitectura Multi-Modelo por Tareas

- **Fecha:** 2026-02-04
- **Estado:** Aceptado

## Contexto

El sistema AEGEN utilizaba modelos hardcodeados en varios componentes (Speech Processing, Researcher) y una configuración global única (`DEFAULT_LLM_MODEL`). Esto limitaba la capacidad de optimizar cada tarea según el modelo más adecuado (ej: Kimi K2 para lógica, Whisper para audio, Gemini para RAG de contexto largo).

Además, se detectó que el uso de Gemini File API para transcripciones de audio cortas era más lento y complejo que el uso de Groq Whisper API.

## Decisión

Implementar una arquitectura de configuración multi-modelo donde cada tarea principal tenga su propio modelo asignado en `settings`:

1.  **CHAT_MODEL / REASONING_MODEL / ROUTING_MODEL**: Se asigna `moonshotai/kimi-k2-instruct-0905` (Kimi K2) vía Groq por su alta capacidad de razonamiento y baja latencia.
2.  **AUDIO_MODEL**: Se asigna `whisper-large-v3-turbo` vía Groq para transcripciones rápidas y precisas.
3.  **RAG_MODEL**: Se mantiene `gemini-2.5-flash-lite` para aprovechar la ventana de contexto masiva de Google y su File API nativa para documentos.

Todos los modelos son configurables a través de variables de entorno en el archivo `.env`.

## Consecuencias

### Positivas
- **Optimización de Costo/Rendimiento**: Cada tarea usa el "mejor" modelo disponible para su propósito.
- **Mantenibilidad**: Se eliminan los modelos hardcodeados del código fuente.
- **Flexibilidad**: Es fácil probar nuevos modelos cambiando solo una variable de entorno.
- **Velocidad**: La transcripción vía Groq Whisper es significativamente más rápida que vía Gemini.

### Negativas/Riesgos
- **Complejidad de Configuración**: Más variables de entorno que gestionar.
- **Límites de Groq**: Groq impone un límite de 25MB para archivos de audio (Whisper).
- **Dependencia de Proveedores**: El sistema ahora depende críticamente tanto de Google como de Groq para diferentes funciones core.
