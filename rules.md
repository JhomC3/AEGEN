# AEGEN Technical Rules (Reglas Técnicas de AEGEN)

## 1. Estándares de Código
- **Async First (Primero Asíncrono):** Todo I/O (Entrada/Salida) de Red, Base de Datos o Archivos DEBE ser `async`.
- **Tipado Estricto:** Uso obligatorio de `typing` y Pydantic para modelos.
- **Formateado:** Ruff es el estándar. `make format` antes de cada commit.
- **Logging (Registro):** Usar el registrador configurado en `src.core.logging_config`. Nunca usar `print()`.
- **Límites de Tamaño:**
    - Los archivos no deben superar las **100 líneas de código (LOC)**.
    - Las funciones no deben superar las **20 líneas**.
    - Si se excede, se debe refactorizar y dividir responsabilidades.

## 2. Gestión de Errores
- **Excepciones Granulares:** Usar las excepciones definidas en `src.core.exceptions`.
- **Graceful Degradation (Degradación Suave):** Los especialistas deben fallar de forma aislada sin tumbar el Orchestrator (Orquestador).
- **Resiliencia:** Implementar reintentos en llamadas a LLMs externos.

## 3. Arquitectura y Estado
- **Stateless Agents (Agentes sin Estado):** Los agentes no deben guardar estado local. Usar `RedisMessageBuffer` y `LongTermMemory` (Memoria a Largo Plazo).
- **Dependency Injection (Inyección de Dependencias):** Usar los mecanismos de `dependencies.py` para inyectar configuraciones y clientes.
- **Tools (Herramientas):** Deben ser funciones puras o clases con interfaz `Tool` (Herramienta).

## 4. Seguridad
- **Secrets (Secretos):** NUNCA subir al repositorio el archivo `.env` o llaves. Usar `.env.example`.
- **Validación:** Todo input (entrada) de usuario debe ser validado mediante Schemas (Esquemas) de Pydantic.

## 5. Documentación
- **Idioma:** Toda la documentación debe estar en **Español**. Términos técnicos en inglés deben ir entre paréntesis (English).
- **Única Fuente de Verdad:** `PROJECT_OVERVIEW.md` es el documento rector.
- **Arquitectura Detallada:** Los detalles de subsistemas residen en `docs/architecture/`.
- **Planes de Desarrollo:** Cada nueva funcionalidad requiere un plan detallado en `docs/plans/YYYY-MM-DD-nombre-feature.md`.
- **Decisiones Técnicas:** Cambios significativos deben registrarse como un ADR en `adr/`.
- **Registro de Cambios:** Nueva versión funcional se registra en `CHANGELOG.md`.
- **Historial:** Informes de hitos y documentos obsoletos residen en `docs/reports/` o `docs/archive/`.
