# AEGEN Technical Rules (Reglas Técnicas de AEGEN)

## 1. Filosofía de Desarrollo (Zen de Python)
Como guía fundamental, seguimos los principios de PEP 20:
- **Lo bello es mejor que lo feo.**
- **Explícito es mejor que implícito.**
- **Simple es mejor que complejo.**
- **Plano es mejor que anidado.**
- **La legibilidad cuenta.**

## 2. Estándares de Código
- **Async First (Primero Asíncrono):** Todo I/O (Entrada/Salida) de Red, Base de Datos o Archivos DEBE ser `async`.
- **Tipado Estricto:** Uso obligatorio de `typing` y Pydantic para modelos.
- **Formateado:** Ruff es el estándar. `make format` antes de cada commit.
- **Logging (Registro):** Usar el registrador configurado en `src.core.logging_config`. Nunca usar `print()`.
- **Inmutabilidad:** Preferir el paso de datos inmutables entre agentes.
- **Límites de Tamaño (Arquitectura Evolutiva):**
    - **Funciones/Métodos:** Máximo **20-30 líneas**. Lo que garantiza que cada pieza haga una sola cosa (SRP).
    - **Archivos de Lógica:** Objetivo **150 líneas**, máximo **200 líneas**. (Servicios, Routers, Agentes).
    - **Archivos de Definición:** Máximo **300 líneas**. (Esquemas Pydantic, Configuraciones, Modelos).
    - **Acción:** Si se excede el máximo, se debe evaluar una división lógica en el siguiente ciclo de refactorización.

## 3. Prácticas de Ingeniería
- **TDD (Desarrollo Guiado por Pruebas):** Escribir la prueba antes del código siempre que sea posible. Cobertura mínima aceptable: 85%.
- **Inyección de Dependencias:** No instanciar clientes (Redis, SQLite) dentro de las funciones; recibirlos como argumentos.
- **Gestión de Errores:** Usar excepciones granulares y garantizar una degradación suave (Graceful Degradation).

## 4. Seguridad
- **Secrets (Secretos):** NUNCA subir al repositorio el archivo `.env` o llaves. Usar `.env.example`.
- **Validación:** Todo input (entrada) de usuario debe ser validado mediante Schemas (Esquemas) de Pydantic.

## 5. Documentación y Flujo de Trabajo
- **Máxima de Desarrollo:** NINGUNA modificación o creación de código puede iniciar sin un plan detallado previo aprobado por el usuario en `docs/planes/`.
- **Única Fuente de Verdad:** `PROJECT_OVERVIEW.md` es el documento rector.
- **Ubicación:**
    - Arquitectura detallada: `docs/arquitectura/`.
    - Guías operativas: `docs/guias/`.
    - Registro de cambios: `CHANGELOG.md`.
- **Idioma:** Toda la documentación debe estar en **Español**. Términos técnicos en inglés se permiten entre paréntesis ().

---
*Cualquier violación de estos estándares será rechazada automáticamente por la suite de verificación.*
