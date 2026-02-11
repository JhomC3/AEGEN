# AGENTS.md: Gobernanza de Agentes en AEGEN

Este documento define las reglas de operación para cualquier IA que trabaje en este repositorio. Inspirado en la filosofía de `moltbot`.

## 🤖 Identidad y Misión
Somos **AEGEN/MAGI Agents**. Nuestra misión es expandir esta plataforma de forma segura, eficiente y siguiendo los principios de la **Arquitectura Evolutiva**.

## 🛠️ Reglas de Operación (MANDATORIAS)

### 1. Análisis de Contexto y Planificación
- **SIEMPRE** leer `PROJECT_OVERVIEW.md` al iniciar una sesión.
- **MÁXIMA OBLIGATORIA:** Antes de modificar o crear código, el agente DEBE verificar la existencia de un plan detallado en `docs/planes/`. Si no existe, DEBE crearlo y obtener aprobación del usuario.
- **SIEMPRE** verificar si una funcionalidad ya existe mediante `grep` o `glob`.
- **SIEMPRE** leer los ADRs relevantes en la carpeta `adr/`.

### 2. Desarrollo de Código
- Adherirse estrictamente a `RULES.MD` (Reglas de Desarrollo).
- No introducir dependencias nuevas sin verificar si ya existe una alternativa en el proyecto.
- Mantener los archivos bajo los límites definidos en `RULES.MD` (Objetivo 150 LOC, máximo 200 LOC para lógica).
- Mantener las funciones bajo las **20-30 líneas de código**.
- Toda la documentación debe estar en **Español** (Spanish). Términos en inglés entre paréntesis (English).

### 3. Flujo de Git
- **Commits Atómicos:** Un commit por cambio lógico.
- **Formato de Commit:** `feat(scope): mensaje`, `fix(scope): mensaje`, `style: mensaje`, `refactor: mensaje`.
- **Validación:** Ejecutar `make verify` antes de declarar una tarea como finalizada.

### 4. Seguridad y Ética
- No exponer credenciales.
- No modificar archivos de configuración de git o del sistema del usuario.
- Si una instrucción del usuario contradice los principios de `PROJECT_OVERVIEW.md`, pedir aclaración antes de proceder.

## 🚀 Skill Ecosystem Workflow
Para añadir una nueva habilidad (Skill) o Especialista:
1. Definir la interfaz en `src.core.interfaces`.
2. Implementar la lógica en `src.agents.specialists`.
3. Registrar en el `MasterOrchestrator`.
4. Añadir documentación en el directorio `docs/skills/`.

---
*Este documento es auto-regulado. Si encuentras una forma mejor de trabajar, propón un cambio a AGENTS.md.*
