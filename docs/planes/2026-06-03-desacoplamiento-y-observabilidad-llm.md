# PLAN: Desacoplamiento de Proveedores LLM y Sistema de Medición de Prompts

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evitar acoplamiento directo entre el código de negocio (skills, agentes) y los SDKs de proveedores. Asegurar que la rotación de keys (`RoundRobinKeyProvider`) proteja todas las llamadas de Gemini.

- **Estado:** En Ejecución
- **Fecha:** 2026-06-03
- **Razón de Creación:** Solución de raíz al rate limit HTTP 413 (8k TPM limit de Groq) mediante migración a Gemini (multi-key) e instrumentación de prompts para medición de tamaño exacta.
- **ADR Relacionado:** [adr/ADR-0040-desacoplamiento-proveedores-llm-inventario.md](adr/ADR-0040-desacoplamiento-proveedores-llm-inventario.md)
- **Informe Forense de Referencia:** [docs/reportes/2026-06-04-forense-y-diseno-llm-registry.md](../reportes/2026-06-04-forense-y-diseno-llm-registry.md)
- **Objetivo General:** Abstraer el motor de llamadas LLM en un proveedor configurable por YAML que soporte composición LCEL mediante `get_llm()` y decoradores `@llm_call`, e instrumentar un sistema de auditoría y medición de prompts completo en runtime para los 22 call sites del sistema.

---

## Resumen Ejecutivo

Actualmente, AEGEN sufre fallas por rate limits al procesar prompts de más de 30,000 caracteres debido a la cuota gratuita restrictiva de Groq (8,000 TPM). Adicionalmente, no existe forma de medir con precisión el contenido exacto y la composición de los prompts que se envían en producción, forzando a realizar suposiciones sobre el consumo de tokens.

Este plan resuelve ambos problemas de forma estructural:
1. **Desacopla** las llamadas LLM del código de negocio mediante una interfaz dual compatible con LCEL: la función `get_llm("nombre")` para cadenas de tubería pipe (`|`) y el decorador `@llm_call("nombre")` para inyección de dependencias.
2. **Centraliza** la configuración en `config/llm_inventory.yaml`, permitiendo cambiar el proveedor (Gemini, Groq, OpenRouter) y modelos en caliente.
3. **Multiplica** la cuota gratuita usando Gemini Flash como motor primario respaldado por la infraestructura de rotación de múltiples keys (`RoundRobinKeyProvider`), aplicando esta protección a todos los call sites de forma perezosa (lazy).
4. **Instrumenta** el sistema para capturar y exponer de forma segura (redactada) el contenido real de los prompts en producción mediante endpoints REST.

Si no se implementa, el sistema continuará fallando bajo uso terapéutico real y los intentos de optimizar el tamaño de prompt se realizarán a ciegas.

---

## Análisis de Impacto

### Dependencias afectadas

El análisis forense identificó 22 call sites distribuidos en 17 archivos del sistema. Los módulos clave que requieren adaptación inmediata son:
- `src/core/engine.py` (Se refactoriza como puente de compatibilidad para evitar regresiones de importación).
- `src/personality/skills/chat/tools.py` (Usa el singleton `llm`, migrará a `get_llm("chat_response")`).
- `src/personality/skills/tcc/tools.py` (Usa `get_analytical_llm()`, migrará a `get_llm("cbt_therapeutic_response")`).
- `src/personality/skills/psicotrading/tools.py` (Usa `get_analytical_llm()`, migrará a `get_llm("psicotrading_response")`).
- `src/agents/orchestrator/routing/routing_analyzer.py` (Usa `llm`, migrará a `get_llm("routing_analysis")`).
- `src/memory/semantic_chunker.py` (Usa `get_rag_llm_async()`, migrará a `get_llm("rag_chunking")`).
- `src/memory/consolidation_worker.py` (Usa factorías, migrará a `get_llm("rag_fact_extraction")`).
- `src/memory/reranker.py` & `src/memory/fact_extractor.py` (Modificados para evitar inicializaciones estáticas en import-time).

### Cobertura de tests existente
- `tests/unit/core/test_metrics_processor.py` (deberá validar la detección del nuevo esquema)
- `tests/unit/personality/test_tcc_guardrails.py` (mocks de LLM deben adaptarse)
- Se crearán tests unitarios específicos para `llm_registry.py` y los nuevos providers.

---

## Fase 1: Capa de Proveedores Desacoplados (Provider Layer)

### Objetivo
Abstraer la creación de modelos de LangChain bajo una interfaz común que soporte fallback automático y rotación de llaves para Gemini.

### Cambios Previstos
- **Módulo/Archivo:** `src/core/providers/base.py`
  - **Acción:** Crear
  - **Descripción:** Definir la interfaz abstracta `LLMProvider` con métodos `invoke` y `ainvoke`.
- **Módulo/Archivo:** `src/core/providers/gemini.py`
  - **Acción:** Crear
  - **Descripción:** Implementación de `GeminiProvider` usando `RoundRobinKeyProvider` para inyectar keys en rotación en cada llamada a `ChatGoogleGenerativeAI`.
- **Módulo/Archivo:** `src/core/providers/groq.py`
  - **Acción:** Crear
  - **Descripción:** Implementación de `GroqProvider` encapsulando la lógica de `ChatGroq`.

### Verificación de Fase
- Test unitario instanciando `GeminiProvider` con múltiples llaves y verificando que rota secuencialmente las llaves de API en llamadas concurrentes.

---

## Fase 2: Registro e Inventario Declarativo (Registry Layer)

### Objetivo
Construir el cargador de manifiesto YAML, la clase `ManagedLLM` (LCEL-compatible) y el decorador `@llm_call` para enrutar modelos dinámicamente y habilitar la rotación de keys y fallbacks.

### Cambios Previstos
- **Módulo/Archivo:** `config/llm_inventory.yaml`
  - **Acción:** Crear
  - **Descripción:** Definir el catálogo inicial de llamadas del sistema (chat, cbt, psicotrading, routing, rag) mapeados a su proveedor primario, modelo por defecto, temperatura, key_rotation y fallbacks.
- **Módulo/Archivo:** `src/core/llm_registry.py`
  - **Acción:** Crear
  - **Descripción:**
    1. Implementar la clase `CallRegistry` para cargar el manifiesto YAML en memoria con soporte para recarga en caliente (hot reload).
    2. Implementar `ManagedLLM(Runnable)` que intercepta las llamadas en runtime, resuelve el proveedor/keys correctas y expone interfaz LCEL (hereda de `Runnable` de LangChain) con soporte para `bind_tools()`.
    3. Implementar el decorador `@llm_call(name: str)` para inyectar una instancia de `ManagedLLM` como argumento `_llm`.

### Verificación de Fase
- Test unitario de `llm_registry.py` validando que:
  - Carga correctamente el archivo YAML.
  - Sobrescribe la configuración por defecto si el YAML contiene overrides.
  - `ManagedLLM` puede componerse en una tubería LCEL (`prompt | managed_llm`) y resolver el proveedor en runtime.
  - El fallback de Gemini a Groq funciona si Gemini lanza un error de red o rate limit.

---

## Fase 3: Migración Simultánea de Call Sites (17 Archivos) & Refactor de Singletons

### Objetivo
Migrar simultáneamente los 22 call sites clave al nuevo sistema de registro para activar el enrutamiento de Gemini con rotación y Groq como fallback, resolver el problema de inicializaciones estáticas en import-time, y eliminar el código obsoleto de factorías legacy y envolvedores huérfanos.

### Cambios Previstos
- **Módulo/Archivo:** `src/core/engine.py`
  - **Acción:** Modificar
  - **Descripción:** Limpiar por completo eliminando las factorías legacy obsoletas (`get_fast_llm()`, `get_analytical_llm()`, `get_rag_llm()`, `get_rag_llm_async()`) y el singleton global `llm`. Conservar únicamente funciones auxiliares de observabilidad/diagnóstico si es necesario.
- **Módulo/Archivo:** `src/core/observability/llm_wrapper.py`
  - **Acción:** Borrar
  - **Descripción:** Eliminar la clase obsoleta `ObservableLLM` para sanear el código muerto y evitar colisiones de diseño con `ManagedLLM`.
- **Módulo/Archivo:** `src/memory/reranker.py` & `src/memory/fact_extractor.py`
  - **Acción:** Modificar
  - **Descripción:** Convertir la inicialización del LLM en el constructor a modo dinámico (lazy) usando `get_llm("rag_reranking")` y `get_llm("rag_fact_extraction")` respectivamente, eliminando las llamadas a factorías en tiempo de importación del módulo.
- **Módulo/Archivo:** los 17 archivos consumidores detectados en el informe forense.
  - **Acción:** Modificar
  - **Descripción:** Reemplazar las importaciones viejas de `src/core/engine.py` por la importación y consumo directo de `get_llm("nombre_llamada")` o el decorador `@llm_call("nombre_llamada")` desde `src/core/llm_registry.py`.

### Verificación de Fase
- Ejecución de `make test` cubriendo los tests unitarios del sistema completo, validando que no existan regresiones de importación cíclica ni fallos conversacionales.

---

## Fase 4: Telemetría Numérica Estructural Segura (Retención Cero de Texto)

### Objetivo
Capturar de forma transparente los metadatos de tamaño y consumo de las llamadas a la IA sin almacenar ni persistir un solo byte de texto de entrada crudo de los usuarios.

### Cambios Previstos
- **Módulo/Archivo:** `src/core/llm_registry.py` (método `_capture_metadata`)
  - **Acción:** Modificar
  - **Descripción:** Implementar la medición de caracteres por cada bloque constituyente del prompt (`identity`, `soul`, `mirror/preferences`, `rag_context`, `history`, `user_message`) y adjuntarlo al diccionario `config["metadata"]` en runtime.
- **Módulo/Archivo:** `src/api/routers/system_llm.py`
  - **Acción:** Crear
  - **Descripción:** Definir endpoints `/system/llm-inventory` (lista y estado del YAML) y `/system/llm-telemetry` (retorno de estadísticas estructuradas numéricas de las últimas 50 llamadas, protegido con `access_controller.py`).
- **Módulo/Archivo:** `src/main.py`
  - **Acción:** Modificar
  - **Descripción:** Montar el nuevo router `system_llm` bajo el prefijo correspondiente.

### Verificación de Fase
- Realizar una llamada de prueba de chat, inspeccionar `/system/llm-telemetry` y verificar que devuelve el reporte estructurado con latencia, costos en USD y conteo de tokens de entrada y salida, sin ningún fragmento de prompt en texto plano.

---

## Fase 5: Pruebas de Integración, Cobertura y Validación de Fallbacks

### Objetivo
Validar la resiliencia del sistema completo simulando errores de API y rate-limits, y confirmar cobertura de telemetría.

### Cambios Previstos
- **Prueba de Fallback Activo:** Inyectar un mock que simule fallos de red o rate limit (HTTP 429) en Gemini y verificar en logs que la llamada se enruta a Groq (o a OpenRouter) de forma transparente sin lanzar excepciones al usuario.
- **Verificación de Cobertura de Observabilidad:** Confirmar que el 100% de las llamadas interceptadas por el `ManagedLLM` inyectan el callback `LLMObservabilityHandler` de forma exitosa y registran telemetría en Prometheus/Grafana.
- **MyPy & Ruff Validation:** Ejecutar `make verify` para asegurar que las nuevas clases de registro y decoradores cumplan con tipado estricto y estándares del proyecto.

---

## Seguimiento de Tareas

- [ ] Fase 1: Abstracción de Proveedores (`LLMProvider`, `GeminiProvider`, `GroqProvider`)
- [ ] Fase 2: Registro e Inventario (`llm_registry.py` + `llm_inventory.yaml` + `ManagedLLM`)
- [ ] Fase 3: Migración Simultánea de Call Sites (17 Archivos) & Eliminación de Código Obsoleto en engine.py
- [ ] Fase 4: Endpoint `/system/llm-inventory` y telemetría estructurada segura
- [ ] Fase 5: Pruebas de integración, simulación de rate-limit y validación de observabilidad en Prometheus

---

## Notas y Riesgos

- **Rate limits en tests:** Las pruebas automáticas de integración deben mockear las llamadas reales a los providers para evitar agotar las cuotas de desarrollo.
- **Seguridad en Endpoints:** Todos los endpoints de telemetría e inventario deben pasar obligatoriamente por el middleware de seguridad existente para evitar exposición pública.
