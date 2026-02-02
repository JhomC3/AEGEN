# ADR-0017: Arquitectura de Auto-Recuperación Semántica (RecoveryManager)

- **Fecha:** 2026-02-02
- **Estado:** Aceptado
- **Relacionado con:** ADR-0012 (Diskless Memory)

## Contexto

Tras un incidente de pérdida de datos en Redis (volumen corrompido/recreado), se identificó que aunque el sistema es "Write-Through" (escribe en Redis y en Google Cloud), no era "Read-Through" ni "Self-Healing".

Si Redis perdía los perfiles o la bóveda de conocimiento, el sistema volvía a un estado inicial ("Usuario", sin preferencias), ignorando los backups semánticos en la nube.

## Decisión

Implementar un **RecoveryManager** que actúe como una capa de persistencia de último recurso utilizando Smart RAG:

1. **Detección de Cold Start:** Cuando un Manager (`ProfileManager`, `KnowledgeBaseManager`) no encuentra datos en Redis para un `chat_id` conocido.
2. **Reconstrucción Semántica:** En lugar de fallar, se realiza una consulta RAG a Google File API (`query_files`) pidiendo específicamente los datos del perfil y conocimiento.
3. **Rehidratación de Redis:** Los datos recuperados (aunque sean una reconstrucción aproximada vía LLM) se vuelven a guardar en Redis para restaurar la fluidez conversacional.
4. **Priorización de Tags:** Se utilizan tags como `USER_PROFILE`, `VAULT` y `KNOWLEDGE` para filtrar archivos relevantes durante la recuperación.

## Consecuencias

### Positivas
- ✅ **Resiliencia ante Desastres:** El sistema puede sobrevivir a una pérdida total de Redis sin perder la identidad del usuario.
- ✅ **Cero Dependencia de GCS:** Se utiliza la infraestructura RAG existente sin añadir nuevas dependencias de almacenamiento (GCS/S3).
- ✅ **Cero Fricción para el Usuario:** La recuperación es transparente; el usuario no percibe que hubo un fallo de base de datos.

### Negativas / Riesgos
- ❌ **Recuperación Aproximada:** El LLM podría parafrasear o simplificar datos del perfil original durante la reconstrucción.
- ❌ **Latencia de Inicio:** La primera consulta tras una pérdida de datos tardará ~5s adicionales debido al proceso RAG.
- ❌ **Costo de Tokens:** Cada recuperación consume tokens de entrada/salida de Gemini.

## Alternativas Consideradas
- **Alternativa A (GCS):** Guardar JSON exactos. Se descartó por requerir nuevas librerías y configuración de permisos de Service Account.
- **Alternativa B (Solo Redis):** Confiar en persistencia AOF. Se descartó porque no protege contra corrupción del volumen Docker.
