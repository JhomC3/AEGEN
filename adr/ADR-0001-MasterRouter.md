# ADR-0001 - Adopción de un Orquestador Central (MasterRouter)

- **Fecha:** 2025-08-13
- **Estado:** Aceptado

## Contexto

A medida que el proyecto evoluciona más allá de un único agente de transcripción, surge la necesidad de gestionar múltiples agentes especialistas (ej. `InventoryAgent`, `ChatAgent`). Se requiere un mecanismo para recibir una solicitud de usuario y dirigirla al especialista adecuado sin crear una lógica monolítica y frágil. La alternativa de que cada agente decida si puede manejar una tarea no es escalable.

## Decisión

Se ha decidido implementar un **`MasterRouter`**, un grafo de LangGraph especializado que actúa como el único punto de entrada para todas las solicitudes de usuario después del `webhook`.

Su responsabilidad exclusiva es:
1. Recibir el `CanonicalEventV1`.
2. Usar un LLM para clasificar la intención del usuario.
3. Enrutar el estado (`GraphStateV1`) al grafo del agente especialista apropiado.

El `MasterRouter` no realiza trabajo de negocio. Delega el 100% de la ejecución de la tarea a los especialistas.

## Consecuencias

**Positivas:**
- **Separación de Preocupaciones:** La lógica de enrutamiento está completamente aislada de la lógica de ejecución de los especialistas.
- **Extensibilidad:** Añadir un nuevo agente al sistema se convierte en un proceso claro: crear el agente y registrarlo en el `MasterRouter`.
- **Control Centralizado:** El flujo de alto nivel es explícito y observable en un solo lugar.
- **Especialistas Simplificados:** Los agentes especialistas no necesitan contener lógica para decidir si una tarea es para ellos.

**Negativas:**
- **Latencia Adicional:** Introduce una llamada de red (al LLM de clasificación) al inicio de cada flujo, añadiendo una pequeña latencia.
- **Punto de Entrada Único:** Aunque no es un cuello de botella de rendimiento, debe ser extremadamente robusto, ya que un fallo en el enrutamiento detiene todo el procesamiento.
