# ADR-0012: Arquitectura de Memoria Diskless (Redis + Google Cloud)

- **Fecha:** 2026-01-25
- **Estado:** Aceptado

## Contexto

El sistema de memoria original de AEGEN (Fase 1 y 2) dependía del sistema de archivos local (`storage/`) utilizando `aiofiles` para persistir historiales de conversación y perfiles de usuario. Esta arquitectura presentaba varios problemas:
1. **Escalabilidad Horizontal:** Los servidores con estado (stateful) dificultan el despliegue en arquitecturas serverless o clusters de contenedores donde el almacenamiento local es efímero.
2. **Multi-tenancy:** La gestión de archivos por `chat_id` en una estructura de carpetas local se vuelve inmanejable y lenta a medida que crece el número de usuarios.
3. **Persistencia:** En entornos cloud-native, los datos locales se pierden al reiniciar o escalar el servicio.
4. **Acoplamiento:** La lógica de negocio estaba fuertemente acoplada a la infraestructura de archivos local.

## Decisión

Adoptar una arquitectura **Diskless** donde toda la persistencia de datos de usuario se traslada a servicios distribuidos (Redis + Google Cloud):

1. **RedisMessageBuffer:** Implementar un buffer de mensajes en Redis (`chat:buffer:{chat_id}`) para almacenar interacciones recientes de forma extremadamente rápida.
2. **ConsolidationManager:** Un trabajador encargado de "consolidar" los mensajes del buffer hacia almacenamiento de largo plazo cuando se cumplen ciertas condiciones (N >= 20 mensajes o 6 horas de inactividad).
3. **Google File Search API:** Utilizar la API de búsqueda de archivos de Google Gemini como almacenamiento de largo plazo para historiales consolidados, eliminando la necesidad de ChromaDB para casos de uso simples de recuperación de historial.
4. **Stateless ProfileManager:** Refactorizar la gestión de perfiles para usar Redis como caché de alta velocidad y Google Cloud como backup persistente, eliminando cualquier dependencia de `storage/`.

## Consecuencias

### Positivas
- ✅ **Stateless UI/Engine:** Los componentes pueden escalarse horizontalmente sin preocuparse por la sincronización de archivos locales.
- ✅ **Rendimiento:** El uso de Redis para el buffer de mensajes y caché de perfiles reduce la latencia de I/O drásticamente.
- ✅ **Seguridad y Aislamiento:** El prefijo `{chat_id}/` en Google File Search garantiza un aislamiento lógico de los datos por usuario.
- ✅ **Simplicidad:** Se elimina la complejidad de mantener una base de datos vectorial local (ChromaDB) para la recuperación de historial básico.

### Negativas / Riesgos
- ❌ **Dependencia Externa:** El sistema ahora depende totalmente de la disponibilidad de Redis y las APIs de Google Cloud.
- ❌ **Costos Cloud:** El almacenamiento en la API de Google y el uso de instancias de Redis pueden incrementar los costos operativos.
- ❌ **Consistencia Eventual:** La consolidación es un proceso asíncrono, lo que significa que hay una ventana de tiempo donde los datos solo están en Redis antes de pasar a la nube.

## Relación con ADR-0007
ADR-0007 proponía el uso de ChromaDB para memoria vectorial multi-tenant. Esta decisión (ADR-0012) simplifica el enfoque utilizando Google File Search API como primera capa de búsqueda semántica. ADR-0007 se mantiene como referencia histórica para necesidades avanzadas de RAG que superen las capacidades de la API de Google.
