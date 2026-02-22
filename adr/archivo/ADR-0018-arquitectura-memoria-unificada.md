# ADR-0018: Arquitectura de Memoria Unificada (Markdown + YAML Frontmatter)

- **Fecha:** 2026-02-03
- **Estado:** Aceptado
- **Sustituye a:** Lógica de recuperación tentativa de ADR-0017.

## Contexto
La Google File API no soporta `application/json` para tareas RAG, lo que causaba pérdida de acceso a perfiles y conocimientos estructurados cuando Redis fallaba. Además, los archivos expiran cada 48 horas sin un mecanismo de renovación.

## Decisión
Adoptar una **Arquitectura de Memoria Unificada** basada en los siguientes pilares:

1.  **Formato Dual (Markdown + YAML):** Todos los datos persistentes en la nube usarán la extensión `.md`. El estado estructurado (JSON) se guardará en un bloque Frontmatter YAML al inicio del archivo, seguido de una representación textual legible para búsqueda semántica.
2.  **Gateway Centralizado (`CloudMemoryGateway`):** Un solo componente será responsable de la serialización, subida, descarga y deserialización de datos entre Redis y Google Cloud.
3.  **Persistencia Determinística:** La recuperación desde la nube ya no dependerá de inferencia LLM (RAG), sino del parseo directo del YAML Frontmatter.
4.  **Auto-Refresh (24h):** Un job periódico refrescará los archivos en la Google File API para evitar su expiración de 48h.
5.  **Bootstrap Automático:** Los archivos globales de conocimiento (`/knowledge/`) se sincronizarán automáticamente al iniciar la aplicación.

## Consecuencias
### Positivas
- ✅ **Resiliencia Total:** Recuperación exacta de perfiles y hechos incluso ante pérdida total de Redis.
- ✅ **Optimización RAG:** El contenido Markdown mejora la precisión de Gemini al buscar información del usuario.
- ✅ **Mantenibilidad:** Lógica centralizada y determinística.
### Negativas
- ❌ **Latencia de Startup:** El primer mensaje tras un fallo de Redis tardará ~2s más debido a la descarga y parseo.
- ❌ **Duplicación de Formato:** Los datos existen como objeto en memoria y como texto estructurado en la nube.
