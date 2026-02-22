# PLAN: [Título Descriptivo]

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** [Propuesto | En Ejecución | Completado | Archivado]
- **Fecha:** YYYY-MM-DD
- **Razón de Creación:** [Nueva Funcionalidad | Corrección de Error | Refactorización | Deuda Técnica]
- **ADR Relacionado:** [adr/ADR-NNNN-titulo.md | N/A (justificar)] -- Ver criterios de obligatoriedad en `AGENTS.md`
- **Objetivo General:** [Resultado final esperado en una oración]

---

## Resumen Ejecutivo

[Qué problema existe, por qué existe, y cómo este plan lo resuelve de forma estructural (no como parche). Incluir el impacto si NO se hace nada.]

---

## Análisis de Impacto

Esta sección es **obligatoria**. Cada punto debe verificarse mecánicamente contra el código, no especulativamente.

### Dependencias afectadas
- [ ] Ejecutar `grep -r 'from <modulo_modificado>' src/` y listar todos los módulos que importan desde archivos modificados
- [ ] Identificar schemas Pydantic que son inputs/outputs de funciones modificadas
- [ ] Verificar si el cambio afecta alguna interfaz en `src/core/interfaces/`

### Cobertura de tests existente
- [ ] Ejecutar `grep -r '<funcion_o_clase>' tests/` para identificar qué tests cubren el código afectado
- [ ] Si cobertura es cero: crear tests ANTES de modificar el código

### Verificación del pipeline
- [ ] Si el cambio toca `src/api/`, `src/agents/`, o `src/tools/telegram/`: trazar el flujo completo y confirmar que sigue intacto

---

## Fase [N]: [Título de la Fase]

### Objetivo
[Resultado específico y verificable de esta fase.]

### Justificación
[Por qué es necesaria esta fase. Qué riesgo elimina o qué capacidad habilita.]

### Cambios Previstos
- **Módulo/Archivo:** `ruta/del/archivo`
  - **Acción:** [Crear | Modificar | Eliminar]
  - **Descripción:** [Detalle técnico del cambio]
  - **Consumidores:** [Módulos que importan o dependen de este archivo]

### Verificación de Fase
Aplicar micro-gates según `AGENTS.md` (sección "Verificación durante la ejecución").

Checklist de alineación arquitectónica (verificar después de implementar):
- [ ] Usa inyección de dependencias (no instancia clientes internamente)
- [ ] Maneja errores con degradación suave (no crea puntos únicos de fallo)
- [ ] Si crea un import nuevo: no genera cadena de imports eager que pueda fallar en cascada
- [ ] Si modifica un schema: todos los consumidores del schema son compatibles

---

## Seguimiento de Tareas

- [ ] [Tarea 1]
- [ ] [Tarea 2]

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.
> Si la implementación diverge del plan original, registrar aquí el qué, el por qué, y el impacto.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|
| | | | |

---

## Notas y Riesgos

[Dependencias técnicas externas, posibles efectos colaterales, o notas para otros agentes que puedan trabajar en paralelo.]
