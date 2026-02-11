# AEGEN Technical Rules (Reglas Técnicas de AEGEN)

## 1. Estándares de Código
- **Async First (Primero Asíncrono):** Todo I/O (Entrada/Salida) de Red, Base de Datos o Archivos DEBE ser `async`.
- **Tipado Estricto:** Uso obligatorio de `typing` y Pydantic para modelos.
- **Formateado:** Ruff es el estándar. `make format` antes de cada commit.
- **Logging (Registro):** Usar el registrador configurado en `src.core.logging_config`. Nunca usar `print()`.
- **Límites de Tamaño (ESTRICTOS):**
    - Los archivos no deben superar las **100 líneas de código (LOC)**.
    - Las funciones/métodos no deben superar las **20 líneas**.
    - Si se excede cualquiera de estos límites, el código **DEBE** ser refactorizado inmediatamente.

## 5. Documentación y Flujo de Trabajo
- **Máxima de Desarrollo:** NINGUNA modificación o creación de código puede iniciar sin un plan detallado previo aprobado por el usuario.
- **Planes de Desarrollo:** Cada funcionalidad o refactorización requiere un archivo en `docs/planes/YYYY-MM-DD-nombre-descriptivo.md`. Este archivo debe guiar la implementación paso a paso (Tareas pequeñas).
- **Hoja de Ruta:** El título y descripción general de cada plan activo debe registrarse en el Roadmap de `PROJECT_OVERVIEW.md`.
- **Única Fuente de Verdad:** `PROJECT_OVERVIEW.md` es el documento rector.
- **Idioma:** Toda la documentación (comentarios, ADRs, guías) debe estar en **Español**. Términos técnicos en inglés se permiten entre paréntesis ().
- **Ubicación:** Los detalles de arquitectura residen en `docs/arquitectura/`, las guías operativas en `docs/guias/` y los reportes en `docs/reportes/`.
