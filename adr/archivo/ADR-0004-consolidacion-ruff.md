# ADR-0004: Consolidación de Herramientas de Formato y Linting en Ruff

**Fecha**: 2025-08-18

**Estado**: Aceptado

## Contexto

El proyecto utilizaba históricamente múltiples herramientas para asegurar la calidad del código: `ruff` para linting, `black` para formateo, y `mypy` para chequeo de tipos. Esta configuración estaba definida en `pyproject.toml` y se ejecutaba a través de comandos en el `makefile` y hooks en `.pre-commit-config.yaml`.

Durante la resolución de un problema con los hooks de `pre-commit`, se observó una inconsistencia y conflicto fundamental:
1.  **Superposición de Responsabilidades**: `ruff` es capaz de realizar tanto el linting como el formateo, haciendo que el uso de `black` fuera redundante.
2.  **Conflictos de Configuración**: Mantener dos herramientas de formateo requería una configuración delicada para evitar que compitieran o tuvieran reglas contradictorias.
3.  **Ineficiencia**: La ejecución de múltiples herramientas en serie es más lenta que la ejecución de una única herramienta optimizada.
4.  **Inconsistencia**: Había discrepancias entre los hooks de `pre-commit` y los comandos del `makefile`, llevando a que el código pasara localmente pero fallara en el commit, y viceversa.

## Decisión

Se ha decidido **eliminar `black` del proyecto y consolidar todas las responsabilidades de linting y formateo de código en `ruff`**.

`mypy` se mantiene como la herramienta designada para el chequeo de tipos estático, ya que `ruff` no cubre esta funcionalidad.

## Consecuencias

### Positivas

1.  **Simplificación del Toolchain**: Se reduce el número de dependencias de desarrollo, simplificando la configuración (`pyproject.toml`, `.pre-commit-config.yaml`) y los scripts (`makefile`).
2.  **Fuente Única de Verdad**: `ruff` se convierte en la única autoridad para el estilo y formato del código, eliminando toda ambigüedad.
3.  **Mejora de Rendimiento**: `ruff`, al estar escrito en Rust, es significativamente más rápido que `black`. Esto acelera la ejecución de los hooks de `pre-commit` y los flujos de CI/CD.
4.  **Consistencia Garantizada**: Al usar la misma herramienta en todas partes, se asegura que el comportamiento del formateo y linting sea idéntico en el entorno de desarrollo local y en el de integración continua.
5.  **Mantenimiento Simplificado**: La gestión de reglas de estilo se centraliza en la sección `[tool.ruff]` de `pyproject.toml`.

### Negativas

1.  **Pérdida de Familiaridad (Menor)**: Desarrolladores acostumbrados a `black` podrían necesitar un breve periodo de ajuste. Sin embargo, `ruff format` está diseñado para ser un reemplazo compatible con `black`, por lo que el impacto en el estilo del código es mínimo o nulo.

## Veredicto

Esta decisión representa una mejora neta en la gobernanza, eficiencia y mantenibilidad del proyecto. Se alinea con el principio de **Simplicidad Pragmática** de la doctrina de AEGEN.
