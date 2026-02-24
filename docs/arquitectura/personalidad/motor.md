# Motor de Personalidad e Identidad

La personalidad de MAGI está diseñada como un **Sistema Adaptativo Multicapa** que evoluciona según la interacción con el usuario, manteniendo un núcleo ético estable.

## 1. El Soul Stack (Estructura de 6 Capas)

La identidad de MAGI se ensambla dinámicamente en cada turno mediante un stack jerárquico:

1.  **CAPA 1: IDENTITY**: Quién es (MAGI) y su rol básico.
2.  **CAPA 2: SOUL**: El núcleo ético y conductual (Honestidad radical, Refugio).
3.  **CAPA 3: THE MIRROR**: Adaptación al usuario (Eco léxico, estilo, formalidad).
4.  **CAPA 4: SKILL OVERLAY**: Patrones especializados (ej: TCC - Acción y Apoyo). Inyecta Gold Standards selectivos.
5.  **CAPA 5: RUNTIME CONTEXT**: Memoria episódica, RAG e intenciones proactivas pendientes.
6.  **CAPA 6: SYSTEM MANDATE (Late Injection)**: El "Martillazo". Instrucciones críticas inyectadas tras el historial para garantizar el tono y la neutralidad lingüística.

## 2. Perfil de Usuario Evolutivo

Almacenado como un **Modelo de Pydantic** validado, el perfil es el "conocimiento que el bot tiene del usuario":

- **Identity (Identidad)**: Nombre, estilo preferido, jerga detectada.
- **Support Preferences (Preferencias de Apoyo)**: Estilo Directo vs Suave, temas a evitar.
- **Coping Mechanisms (Mecanismos de Afrontamiento)**: Fortalezas reportadas por el usuario y anclajes de calma.
- **Psychological State (Estado Psicológico)**: Fase actual de crecimiento y luchas activas.
- **Clinical Safety (Seguridad Clínica)**: Contactos de emergencia y estado del descargo de responsabilidad (disclaimer).

## 3. Construcción Dinámica de Prompts (Instrucciones)

El `SystemPromptBuilder` ensambla la personalidad final para el LLM (Modelo de Lenguaje) turno a turno:

- **Base Context (Contexto Base)**: Fusiona SOUL e IDENTITY.
- **Adaptation (Adaptación)**: Inyecta datos específicos del usuario (nombre, dialecto, estilo).
- **Skill Injection (Inyección de Habilidad)**: Aplica el prompt específico del especialista (ej: guía de TCC).
- **Runtime Context (Contexto de Ejecución)**: Inyecta las memorias recuperadas vía RAG y el historial de la sesión.

## 4. Adaptación Lingüística (Mirroring - Efecto Espejo)

En lugar de forzar acentos regionales, MAGI utiliza un **Algoritmo de Mirroring**:
- Mantiene una base de español neutro y cálido.
- Detecta y adopta sutilmente los modismos y jerga específicos del usuario (hasta un 30%) para generar empatía sin sonar artificial.

---
*Para detalles de implementación, ver `src/personality/`*
