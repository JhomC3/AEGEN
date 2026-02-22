# PLAN: Corrección de Cadena de Imports y Renders de Personalidad

- **Estado:** Completado
- **Fecha:** 2026-02-18
- **Razón de Creación:** Informe de Errores (Fallo de Despliegue)
- **Objetivo General:** Restaurar archivos faltantes tras refactorización y desacoplar el arranque del sistema para evitar bloqueos por errores en especialistas.

---

## Resumen Ejecutivo
Un error en el proceso de commit dejó fuera el archivo `prompt_renders.py`, lo que impidió el arranque en producción. Además, se identificó una fragilidad estructural: fallos en un especialista bloqueaban toda la aplicación debido a imports eagerly cargados en el nivel superior.

---

## Fase 1: Restauración de Funcionalidad
### Objetivo
Recuperar el módulo de renderizado y solucionar el `ModuleNotFoundError`.

### Justificación
Indispensable para el despliegue funcional de la versión actual.

### Cambios Previstos
- **Módulo/Archivo:** `src/personality/prompt_renders.py`
  - **Acción:** Crear
  - **Descripción:** Motor de renderizado de dialectos y adaptación de estilo.

---

## Fase 2: Robustez de Arranque
### Objetivo
Implementar registro diferido de especialistas en el evento `lifespan`.

### Justificación
Garantiza que el sistema arranque incluso si un especialista individual tiene errores, permitiendo una degradación suave.

### Cambios Previstos
- **Módulo/Archivo:** `src/agents/specialists/__init__.py`
  - **Acción:** Modificar
  - **Descripción:** Reemplazar imports eager por función `register_all_specialists()`.

---

## Seguimiento de Tareas
- [x] Crear `prompt_renders.py`. ✅ (2026-02-18)
- [x] Desacoplar imports en `src/agents/`. ✅ (2026-02-18)
- [x] Modificar `lifespan` en `main.py`. ✅ (2026-02-18)
- [x] Validar consistencia de esquema en Telegram tools. ✅ (2026-02-18)

---

## Notas y Riesgos
- Se normalizó el parámetro `message` a `text` en las herramientas de Telegram para evitar errores de validación.
