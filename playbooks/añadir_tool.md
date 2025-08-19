# Playbook: Cómo Añadir una Nueva Herramienta (Tool)

> **Propietario:** @TechLead
> **Frecuencia:** Ocasional
> **Complejidad:** Baja

Este playbook describe el proceso estándar para añadir una nueva `Tool` al sistema AEGEN, asegurando que cumple con los estándares de calidad y diseño del proyecto.

## Pasos

### 1. Crear el Archivo de la Herramienta

- **Ubicación:** `src/tools/`
- **Nombre:** `nombre_descriptivo.py`
- **Principio de Diseño:** Sigue el arquetipo de `speech_processing.py`.
    - **Singleton Manager:** Usa un manager para encapsular la lógica y el estado (si es necesario).
    - **Lazy Loading:** Carga los recursos pesados (modelos, clientes de API) de forma perezosa en el primer uso, no en la importación.
    - **Async Wrapper:** Envuelve las llamadas bloqueantes de I/O en `asyncio.to_thread` para no bloquear el event loop.

### 2. Definir la Interfaz con `@tool`

- Usa el decorador `@tool` de LangChain para definir la interfaz de la herramienta.
- **Docstring Obligatorio:** El docstring debe ser claro y conciso, explicando qué hace la herramienta, cuáles son sus argumentos y qué retorna. Este docstring es usado por los agentes LLM para decidir cuándo usar la herramienta.
- **Tipado Estricto:** Usa Pydantic `BaseModel` para definir los argumentos de entrada (`args_schema`).

### 3. Implementar Pruebas Unitarias

- **Ubicación:** `tests/unit/tools/`
- **Nombre:** `test_nombre_descriptivo.py`
- **Contenido:**
    - Mockea cualquier dependencia externa (APIs, librerías).
    - Prueba el caso de éxito.
    - Prueba los casos de error esperados (ej. entrada inválida, fallo de la API mockeada).

### 4. Registrar la Herramienta (si es necesario)

- Si la herramienta debe ser accesible globalmente, añádela al `ToolRegistry` en `src/core/registry.py`.

### 5. Verificar la Implementación

- Ejecuta `make verify` para asegurar que el nuevo código cumple con todos los estándares de linting, tipado y pruebas.

### 6. Actualizar la Documentación

- Si la herramienta introduce un nuevo concepto o dependencia importante, asegúrate de que esté reflejado en `README.md` o `PROJECT_OVERVIEW.md`.
