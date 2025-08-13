# AEGEN - Reglas Técnicas
> Version: 0.1.0; Estado: Prescriptivo; Owner: Tech

## Severidad: MUST (Obligatorio, Forzado por CI), SHOULD (Recomendado), MAY (Opcional)

## 1. Código y Dependencias
- **[MUST]** Todo I/O debe ser `async`.
- **[MUST]** No se permiten secretos hardcodeados. Usar Pydantic Settings para cargar desde el entorno.
- **[MUST]** Logging debe ser JSON estructurado y contener un `correlation_id`.
- **[MUST]** No se debe registrar información PII. Usar un redactor para campos sensibles.

## 2. Diseño de Componentes
- **[MUST]** Las `Tools` deben ser sin estado y no gestionar el ciclo de vida de archivos.
- **[MUST]** Toda interfaz pública debe tener tipado estricto. `Any` solo con `TODO: [TICKET-ID]`.
- **[MUST]** Todo método/función pública debe tener un docstring con formato Numpy/Google y `LLM-hints`.

## 3. Testing y Calidad
- **[MUST]** Todo PR debe incluir tests para la nueva funcionalidad.
- **[MUST]** La cobertura de pruebas no puede disminuir.
- **[MUST]** Todo prompt en `prompts/` debe tener un test de snapshot.

## 4. Política de Errores
- **[SHOULD]** Usar la taxonomía de errores definida (`UserError`, `ToolError`, `TransientError`).
- **[SHOULD]** Implementar reintentos con backoff exponencial y jitter para errores transitorios.
