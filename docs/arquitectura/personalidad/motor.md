# Motor de Personalidad e Identidad

La personalidad de MAGI está diseñada como un **Sistema Adaptativo Multicapa** que evoluciona según la interacción con el usuario, manteniendo un núcleo ético estable.

## 1. Capas de Identidad

La identidad de MAGI se compone de tres niveles jerárquicos:

1.  **SOUL (Alma)**: El núcleo ético y conductual inmutable (ej: "Compasivo pero firme", "Orientado al crecimiento").
2.  **IDENTITY (Identidad)**: La personalidad estructural (ej: "Asistente agéntico avanzado", "Compañero de salud mental").
3.  **SKILL OVERLAYS (Capas de Habilidad)**: Patrones conductuales especializados aplicados contextualmente (ej: "TCC Amor Duro", "Chat Cálido").

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
