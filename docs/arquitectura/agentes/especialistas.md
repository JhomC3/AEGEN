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

## 2. Registro y Carga Diferida

Para evitar dependencias circulares y asegurar un arranque robusto de la aplicación, el registro de especialistas se realiza de forma diferida mediante la función `register_all_specialists()`, la cual es invocada durante el evento `lifespan` de FastAPI.

Este mecanismo permite una **Degradación Suave**: si un especialista presenta errores en sus dependencias o configuración, el sistema registra el error en los logs pero permite que el resto de los especialistas y el motor principal continúen funcionando.

---
*Ver `src/agents/specialists/`*
