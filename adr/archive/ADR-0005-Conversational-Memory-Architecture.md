# ADR-0005: Phase 3B - Conversational Memory Architecture

- **Fecha:** 2025-08-19
- **Estado:** Propuesto
- **Autores:** @jhomc + Gemini AI Strategic Analysis

## Contexto

El sistema actual (fin de Fase 3A) procesa mensajes de audio retornando una transcripción directa al usuario. Esto crea una experiencia de usuario deficiente, ya que la expectativa es una respuesta conversacional inteligente. La Fase 3B tiene como objetivo introducir memoria conversacional para habilitar interacciones multi-turno con estado.

Esto requiere cambios arquitectónicos fundamentales en gestión de estado, lógica de orquestación y dependencias de infraestructura.

## Decisión

Implementaremos un sistema de memoria conversacional comprehensivo adoptando los siguientes patrones arquitectónicos y tecnologías:

### 1. Especialista Compuesto (`ConversationAgent`)

Para manejar flujos conversacionales multi-paso (ej. Transcribir → Chat), crearemos un nuevo especialista compuesto. Este agente encapsulará el flujo dentro de su propio `StateGraph`, preservando el rol del `MasterOrchestrator` como un router simple y sin estado, manteniendo el Registry Pattern.

### 2. Nuevo Schema de Estado (`GraphStateV2`)

Introduciremos un nuevo objeto de estado no compatible hacia atrás. `GraphStateV2` extenderá `GraphStateV1` con un campo `conversation_history: list[V2ChatMessage]`. El historial usará un `TypedDict` simple y JSON-serializable para asegurar serialización robusta a Redis y prevenir problemas de versionado de dependencias.

```python
class V2ChatMessage(TypedDict):
    """Mensaje de chat Redis-safe, JSON-serializable."""
    role: Literal["user", "assistant", "system", "tool"]
    content: str

class GraphStateV2(TypedDict):
    """Objeto de estado evolucionado para flujos conversacionales. (Versión 2)"""
    event: CanonicalEventV1
    payload: dict[str, Any]
    error_message: str | None
    conversation_history: list[V2ChatMessage]
```

### 3. Redis para Almacenamiento de Sesión

Usaremos Redis como backend para almacenar historial conversacional.

- **Gestión de Conexiones:** Un pool de conexiones Redis será manejado por el context manager `lifespan` de FastAPI y expuesto vía factory con dependency injection (`get_redis`), siguiendo mejores prácticas modernas.
- **TTL de Sesión:** Se implementará un TTL sliding window de 24 horas en cada escritura a Redis para asegurar que conversaciones activas no terminen prematuramente.

### 4. Gestión de Sesión In-Graph

La responsabilidad de cargar y guardar datos de sesión será explícitamente manejada por nodos dentro del grafo del `ConversationAgent` (`load_session`, `save_session`). Esto se alinea con nuestro principio de mantener I/O dentro de la capa de orquestación.

### 5. Estrategia de Manejo de Errores

En caso de indisponibilidad de Redis, el sistema **fallará rápido**. El grafo loggeará el error, poblará un mensaje de error en el estado, y terminará el flujo graciosamente sin intentar generar una respuesta stateless (y potencialmente incorrecta).

### 6. Integración LangSmith

LangSmith se configurará para tracear todo el flujo end-to-end, incluyendo spans explícitos para operaciones I/O de Redis, para proveer visibilidad completa para debugging y monitoreo de performance.

## Timeline de Implementación

### Principio Fundamental: 🚨 REVISAR CONTEXTO PRIMERO
Antes de escribir cualquier código, crear archivos o carpetas, SIEMPRE revisar primero qué ya existe usando herramientas de búsqueda (Read, LS, Grep, Glob). Esto previene duplicación, conflictos y trabajo innecesario.

- **Semana 1:** GraphStateV2 + ConversationAgent (stateless)
- **Semana 2:** Gestión de sesión Redis + integración LangSmith
- **Semana 3-4:** Hardening de testing + validación de recuperación de errores

## Stack Tecnológico

- **Redis:** Cliente async redis-py 5.x con connection pooling
- **LangSmith:** API estable más reciente para observabilidad LLM
- **FastAPI:** Patrón lifespan para gestión de conexiones
- **Gestión de Estado:** Historial conversacional JSON-serializable

## Consecuencias

### Positivas
- **Fix UX Inmediato:** Usuarios reciben respuestas inteligentes en lugar de transcripts crudos
- **Memoria Escalable:** Redis provee almacenamiento de sesión robusto y persistente
- **Observabilidad Completa:** LangSmith habilita debugging comprehensivo y tracking de costos
- **Arquitectura Limpia:** Patrón de agente compuesto mantiene separación de responsabilidades

### Negativas
- **Nueva Dependencia:** El proyecto ahora tiene dependencia hard en una instancia Redis corriendo
- **Cambio Breaking:** La migración a `GraphStateV2` requiere refactor coordinado de agentes existentes y tests que usan el graph state
- **Complejidad:** Complejidad operacional adicional para gestión y monitoreo de Redis

### Requerimientos de Testing
- Nuevos tests E2E e integración requeridos para validar persistencia de historial conversacional y manejo correcto de contexto por el `ChatAgent`
- Testing basado en mocks para inyección de contexto LLM para asegurar validación determinística
- Tests de integración Redis con contenedores reales para validación de persistencia de sesión

## Definition of Done

"Usuario envía audio → recibe respuesta inteligente → puede referenciar conversación anterior"

## Referencias

- PROJECT_OVERVIEW.md - Constitución y roadmap del proyecto
- ADR-0002-RedisSessionMemory.md - Fundaciones de memoria Redis
- ADR-0003-Dynamic-Tool-Based-Routing.md - Patrón registry para especialistas
- Sesión de Análisis Estratégico Gemini AI - 2025-08-19
- Mejores Prácticas Redis-py AsyncIO - Documentación FastAPI
