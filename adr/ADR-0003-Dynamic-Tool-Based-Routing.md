# ADR-0003 - Enrutamiento Dinámico Basado en Herramientas y Registro de Especialistas

- **Fecha:** 2025-08-13
- **Estado:** Aceptado

## Contexto

La implementación inicial del `MasterRouter` (ADR-0001) proponía un enrutamiento basado en una clasificación de LLM con un prompt estático y una lógica de `if/else` para dirigir el flujo. Este enfoque presenta dos problemas de escalabilidad críticos:
1.  **Fragilidad del Prompt:** Un prompt que lista explícitamente todos los agentes disponibles es inviable y propenso a errores a medida que el número de agentes crece.
2.  **Acoplamiento Fuerte:** El orquestador estaría fuertemente acoplado a los especialistas, requiriendo modificaciones manuales para añadir, eliminar o cambiar agentes.

## Decisión

Se ha decidido refactorizar la arquitectura del `MasterOrchestrator` para adoptar un modelo de **enrutamiento dinámico basado en herramientas y un registro de especialistas**.

1.  **Registro de Especialistas (`SpecialistRegistry`):**
    - Se creará un registro central en `src/core/registry.py`.
    - Cada agente especialista será responsable de registrarse a sí mismo, proporcionando su grafo de LangGraph y una "herramienta" de descripción (un objeto `Tool` de LangChain). Esta herramienta describe la capacidad del agente en lenguaje natural (ej. "Usa esta herramienta para transcribir audio").

2.  **Enrutamiento Basado en Herramientas:**
    - El `MasterRouter` ya no clasificará la intención en una de N categorías. En su lugar, se le presentará la lista de herramientas registradas y se le pedirá que elija la más apropiada para la solicitud del usuario.
    - LangGraph puede enrutar el flujo de forma nativa basándose en la herramienta seleccionada por el LLM.

3.  **Construcción Dinámica del Grafo:**
    - Al iniciarse, el `MasterOrchestrator` consultará el `SpecialistRegistry`.
    - Añadirá dinámicamente un nodo y una arista por cada especialista registrado. Esto elimina la necesidad de definir nodos y aristas estáticas en el código del orquestador.

## Consecuencias

**Positivas:**
- **Desacoplamiento Total:** El orquestador es completamente agnóstico a los especialistas que existen. Su única dependencia es el registro.
- **Arquitectura Plug-and-Play:** Añadir un nuevo agente al sistema se reduce a crear el especialista y registrarlo. No se requiere ninguna modificación en el `MasterOrchestrator`.
- **Escalabilidad Real:** El sistema puede escalar a cientos de agentes sin que la complejidad del código del orquestador aumente.
- **Robustez del Prompt:** El prompt del enrutador es más robusto, ya que se basa en descripciones de herramientas, un patrón bien establecido y soportado por los LLMs.

**Negativas:**
- **Complejidad Inicial:** Introduce una capa de indirección (el registro) que añade una ligera complejidad conceptual al inicio.
- **Dependencia en el Inicio:** El descubrimiento de agentes ocurre en tiempo de arranque, lo que significa que para añadir un nuevo agente se requiere un reinicio del servicio (un comportamiento estándar para la mayoría de aplicaciones web).
