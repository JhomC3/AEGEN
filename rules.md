# AEGEN Technical Rules (rules.md)

## 1. Estándares de Código
- **Async First:** Todo I/O (Red, DB, Archivos) DEBE ser `async`.
- **Tipado Estricto:** Uso obligatorio de `typing` y Pydantic para modelos.
- **Formateado:** Ruff es el estándar. `make format` antes de cada commit.
- **Logging:** Usar el logger configurado en `src.core.logging_config`. Nunca usar `print()`.

## 2. Gestión de Errores
- **Excepciones Granulares:** Usar las excepciones definidas en `src.core.exceptions`.
- **Graceful Degradation:** Los especialistas deben fallar de forma aislada sin tumbar el Orchestrator.
- **Resiliencia:** Implementar reintentos en llamadas a LLMs externos.

## 3. Arquitectura y Estado
- **Stateless Agents:** Los agentes no deben guardar estado local. Usar `RedisMessageBuffer` y `LongTermMemory`.
- **Dependency Injection:** Usar los mecanismos de `dependencies.py` para inyectar configuraciones y clientes.
- **Tools:** Deben ser funciones puras o clases con interfaz `Tool` (ver `src.core.interfaces.tool`).

## 4. Seguridad
- **Secrets:** NUNCA commitear `.env` o llaves. Usar `.env.example`.
- **Validación:** Todo input de usuario debe ser validado mediante Schemas de Pydantic.
