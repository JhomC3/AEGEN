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

## 3. Flujo de Datos de Alto Nivel (Arquitectura General)

```mermaid
graph TD
    A[Telegram] --> B(Webhook);
    B --> C{Evento Canónico};
    C --> D[MasterOrchestrator];
    D --> E{Router Mejorado};
    E --> F[Analizador de Rutas];
    F --> G{LLM Multi-Proveedor};
    E --> H[Agente Especialista];
    H --> I[Ejecución de Grafo];
    I --> J[Búfer de Mensajes Redis];
    J --> K[Trabajador de Consolidación];
    K --> L[Almacén SQLite / sqlite-vec];
    L -- "RAG: Origen/Confianza/Evidencia" --> Specialists;
    L -.-> M[Respaldo: GCS];
    I --> N(Respuesta);
    N --> A;

    Z[PDFs en storage/knowledge] -.-> Y[KnowledgeWatcher];
    Y -- "Async Polling (Auto-Sync)" --> L;

    subgraph Memoria
        J
        K
        L
        O[Gestor de Perfil Pydantic]
        Y
    end
```

---
*Referencia: Evolución de Arquitectura v2.0*
