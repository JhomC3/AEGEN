# Flujos de Datos de AEGEN

Este documento detalla los procesos secuenciales de datos para las interacciones principales del sistema.

## 1. Flujo Conversacional (Texto)

```mermaid
graph TD
    A[Usuario envía texto] --> B[Telegram Webhook]
    B --> C[CanonicalEventV1]
    C --> D[SessionManager: Carga Memoria]
    D --> E[MasterOrchestrator]

    E --> F[EventRouter: ¿tipo_evento?]
    F -->|texto| G[EnhancedRouter]
    G --> H[RoutingAnalyzer: Análisis]

    H -->|conversación simple| I[Respuesta Directa]
    H -->|tarea compleja| J[Delegación a Especialista]

    J --> L[Traducción de Respuesta]
    L --> M[Respuesta en Lenguaje Natural]

    I --> N[Actualización de Memoria]
    M --> N
    N --> O[Guardar en Redis/SQLite]
    O --> P[Responder a Usuario]
```

## 2. Flujo de Procesamiento de Audio

```mermaid
graph TD
    A[Usuario envía audio] --> B[Telegram Webhook]
    B --> C[CanonicalEventV1]
    C --> D[SessionManager: Carga Memoria]
    D --> E[MasterOrchestrator]

    E --> F[EventRouter: audio]
    F --> G[TranscriptionAgent]
    G --> H[Procesamiento de Voz]
    H --> I[Chaining Router]

    I --> J[ChatSpecialist: MAGI]
    J --> K[Respuesta Inteligente]
    K --> L[Actualización de Memoria]
    L --> M[Guardar en Redis/SQLite]
    M --> N[Responder a Usuario]
```

---
*Referencia: Evolución de Arquitectura v2.0*
