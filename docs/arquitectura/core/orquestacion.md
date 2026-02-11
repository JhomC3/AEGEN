# Orquestación del Sistema (MasterOrchestrator)

AEGEN utiliza un sistema de orquestación basado en grafos de estado para gestionar flujos de trabajo complejos y la delegación de tareas entre especialistas.

## 1. El Grafo de Orquestación

La orquestación se implementa mediante **LangGraph**, permitiendo una ejecución declarativa y cíclica si es necesario.

### Componentes Principales
- **Nodos**: Representan a los especialistas o herramientas (ej: `cbt_specialist`, `chat_specialist`).
- **Aristas (Edges)**: Definen el flujo entre nodos basado en decisiones de enrutamiento.
- **Estado (State)**: Un objeto `GraphStateV2` que viaja a través del grafo manteniendo el contexto.

## 2. Ciclo de Vida de una Petición

1. **Entrada**: El evento canónico entra al orquestador.
2. **Enrutamiento Inicial**: El `EnhancedRouter` decide a qué especialista delegar.
3. **Ejecución**: El especialista procesa la tarea y actualiza el estado.
4. **Encadenamiento (Chaining)**: Se evalúa si se requiere un segundo especialista (ej: transcripción -> chat).
5. **Salida**: Se genera la respuesta final y se persiste la sesión.

---
*Para detalles de implementación, ver `src/agents/orchestrator/`*
