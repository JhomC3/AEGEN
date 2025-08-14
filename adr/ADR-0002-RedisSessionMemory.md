# ADR-0002 - Selección de Redis para la Memoria de Sesión Conversacional

- **Fecha:** 2025-08-13
- **Estado:** Aceptado

## Contexto

Para que los agentes puedan realizar tareas complejas de varios pasos (como el caso de uso del inventario), el sistema debe mantener el estado de la conversación (`GraphStateV1`) entre múltiples interacciones de un mismo usuario. Se necesita una solución de almacenamiento de baja latencia para guardar y recuperar este estado de sesión de forma eficiente. Se consideraron bases de datos relacionales (como PostgreSQL) y almacenes en memoria.

## Decisión

Se ha decidido utilizar **Redis** como el almacén de clave-valor para la memoria de sesión de corto plazo.

- La **clave** será el `chat_id` (o un identificador de sesión único).
- El **valor** será el objeto `GraphStateV1` serializado.

Antes de cada ejecución de un agente, el orquestador cargará el estado desde Redis. Después de cada ejecución, guardará el estado actualizado.

## Consecuencias

**Positivas:**
- **Baja Latencia:** Redis es un almacén en memoria, lo que garantiza un acceso casi instantáneo al estado de la sesión. Esto es crítico para mantener una experiencia de usuario fluida y responsiva.
- **Simplicidad:** El modelo de clave-valor es perfecto para el almacenamiento de sesiones y no requiere esquemas complejos.
- **Escalabilidad Probada:** Redis es un estándar de la industria para la gestión de cachés y sesiones en sistemas distribuidos.
- **Separación de Memorias:** Esta decisión distingue claramente la "memoria de trabajo" (Redis) de la "memoria de referencia" (que será una base de datos vectorial para RAG), permitiendo usar la herramienta correcta para cada trabajo.

**Negativas:**
- **No es un Almacén Permanente por Defecto:** La configuración por defecto de Redis es como una caché. Se debe asegurar una configuración de persistencia adecuada si se requiere que las conversaciones sobrevivan a reinicios del servidor de Redis.
- **No es para Consultas Complejas:** Redis no permite buscar o analizar el contenido de los estados de sesión de forma semántica. Su propósito es la recuperación rápida por clave.
