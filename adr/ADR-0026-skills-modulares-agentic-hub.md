# ADR-0026 - Sistema de Skills Modulares y Evolutivos (Agentic Skills Hub)

- **Fecha:** 2026-05-04
- **Estado:** Implementado (v0.8.5)

## Contexto

AEGEN ha evolucionado de un chatbot a un sistema orquestador de agentes. Sin embargo, la arquitectura actual de "Skills" presenta limitaciones críticas para el crecimiento a largo plazo y la diversidad de agentes requerida (TCC, Psicotrading, Quant Trading, Investigación):

1.  **Rigidez Estructural:** Los skills actuales son archivos Markdown estáticos (`_overlay.md`) limitados a modificar el prompt. No permiten definir metadatos, herramientas (tools) específicas o dependencias.
2.  **Acoplamiento Fuerte:** La lógica de los especialistas (`src/agents/specialists/`) está cableada en el código fuente. Añadir un nuevo agente requiere modificar múltiples archivos (`registry.py`, `schemas.py`, imports, etc.), lo que genera fricción y riesgo de errores.
3.  **Falta de Autonomía:** El sistema actual es mayoritariamente síncrono. Los agentes complejos (investigación de mercado, análisis de noticias) necesitan ejecutar tareas asíncronas en background que la estructura actual no facilita de forma nativa.
4.  **Inspiración Externa:** Se han tomado como referencia dos repositorios líderes en orquestación de agentes personales:
    -   **[OpenClaw](https://github.com/openclaw/openclaw):** Destaca por su arquitectura de Gateway local-first, gestión de nodos distribuidos y sistema de "Skills Hub" basado en directorios.
    -   **[Hermes-Agent](https://github.com/NousResearch/hermes-agent):** Aporta el concepto de "Closed Learning Loop" (creación autónoma de skills), memoria persistente mediante FTS5 y delegación de sub-agentes asíncronos.

## Decisión

Se adopta una arquitectura de **Skills Modulares Basados en Directorios**, transformando AEGEN en un "Agentic Hub" extensible. Los cambios clave y su origen de inspiración son:

### 1. Estructura de "Habilidad como Directorio"
*Inspiración: OpenClaw (`~/.openclaw/workspace/skills/`)*
Se abandona el archivo único por una estructura de carpeta:
`src/personality/skills/{skill_name}/`
-   `SKILL.md`: Archivo principal que combina un encabezado **YAML Frontmatter** (metadatos) y el cuerpo **Markdown** (instrucciones y tono).
-   `tools.py` (Opcional): Definición de herramientas LangChain específicas para ese skill.
-   `schemas.py` (Opcional): Schemas de Pydantic específicos para la entrada/salida de este agente.

### 2. Estándar de `SKILL.md` (Formato YAML + Markdown)
*Inspiración: Hermes-Agent y el estándar [agentskills.io](https://agentskills.io)*
Incluso la eliminación de muletillas de cierre (preguntas obligatorias) se adopta como una regla de "Gold Standard" en el cuerpo de las instrucciones del skill.
```yaml
---
name: "CBT Specialist"
id: "cbt_therapeutic"
version: "1.0.0"
capabilities: ["psicologia", "tcc", "apoyo_emocional"]
requirements:
  tools: ["cbt_therapeutic_guidance_tool"]
  memory_access: "full"
  priority: 10
---
## Tone Modifiers
[Instrucciones de tono...]
## Instructions
[Instrucciones operativas...]
```

### 3. Cargador Dinámico e Inversión de Control
*Inspiración: OpenClaw (Sistema de Registro de Skills)*
-   El `PersonalityLoader` y el `SpecialistRegistry` se refactorizan para escanear el sistema de archivos de forma recursiva.
-   AEGEN cargará habilidades tanto de `src/personality/skills/` (core) como de `storage/skills/` (usuario/dinámicas), permitiendo que el asistente "instale" nuevas capacidades sin tocar el código central.

### 4. Soporte para Operaciones Asíncronas y Delegación
*Inspiración: Hermes-Agent (Subagent Delegation) y OpenClaw (Event Gateway)*
-   Los skills podrán declarar si una tarea es asíncrona.
-   Se implementará un mecanismo de delegación donde el agente de chat (MAGI) pueda spawnear un "worker" (ej. `researcher_agent`) para tareas de larga duración (noticias, trading) que notifique al usuario vía el `RedisEventBus` al finalizar.

## Elementos Adicionales a Adaptar

Basado en la revisión profunda de ambos repositorios, se integrarán los siguientes elementos en fases posteriores:

1.  **Memoria Híbrida (FTS5 + Vectores):** Tomado de **Hermes-Agent**. Implementar búsqueda de texto completo en SQLite para recuperar detalles específicos de sesiones de trading o terapia que la búsqueda vectorial (semántica) suele ignorar.
2.  **Learning Loop (Autoinstalación):** Tomado de **Hermes-Agent**. Permitir que AEGEN, tras resolver una tarea compleja de trading o investigación, genere y guarde automáticamente un nuevo `SKILL.md` con los pasos exitosos en `storage/skills/`.
3.  **Unified Gateway Protocol:** Tomado de **OpenClaw**. Evolucionar AEGEN hacia un modelo de "Gateway" donde Telegram sea solo un cliente más, permitiendo conectar nodos locales (ej. tu PC ejecutando scripts quant dictados por AEGEN) vía WebSockets.
4.  **Scheduled Automations:** Tomado de **OpenClaw/Hermes**. Integrar un `CronScheduler` dentro del orquestador para que los agentes de "Investigación de Mercado" o "Noticias" entreguen reportes proactivos sin intervención del usuario.

## Consecuencias

### Positivas
-   **Escalabilidad Infinita:** Permite añadir agentes de trading, investigación o cualquier dominio simplemente moviendo una carpeta.
-   **Desacoplamiento:** El Core de AEGEN se mantiene limpio y agnóstico a la lógica de negocio.
-   **Mantenibilidad:** Facilita el testing aislado de cada habilidad.
-   **Eliminación de Muletillas:** El nuevo estándar de prompt prohíbe explícitamente las preguntas obligatorias al final de cada turno.

### Negativas / Riesgos
-   **Complejidad Inicial:** Requiere una refactorización profunda del cargador de personalidad y el registro de especialistas.
-   **Seguridad:** La carga dinámica de código (`tools.py`) requiere validación estricta o sandboxing (Docker) para evitar ejecución de código malicioso en skills no verificados.
-   **Rendimiento:** El parseo de YAML y escaneo de directorios añade un ligero overhead al arranque (mitigado con caching).
