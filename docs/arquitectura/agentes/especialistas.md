# Catálogo de Especialistas

AEGEN es un sistema multi-agente donde cada "especialista" posee una habilidad única y un contexto de herramientas específico.

## 1. Especialistas Actuales

### Chat Specialist (MAGI)
- **Habilidad**: Conversación general, empatía y acompañamiento básico.
- **Herramientas**: Búsqueda en memoria de largo plazo.

### CBT Specialist (Especialista TCC)
- **Habilidad**: Intervención basada en Terapia Cognitivo Conductual.
- **Reglas**: No diagnóstico, enfoque en identificación de distorsiones y recursos de afrontamiento.

### Transcription Agent (Agente de Transcripción)
- **Habilidad**: Conversión de voz a texto usando FasterWhisper.
- **Flujo**: Siempre encadenado con el Chat Specialist tras completar la tarea.

## 2. Registro de Habilidades

Cada especialista se registra automáticamente en el `MasterOrchestrator` mediante el `SpecialistRegistry`, permitiendo un crecimiento modular del sistema.

---
*Ver `src/agents/specialists/`*
