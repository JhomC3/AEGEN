# ADR-0040 - Desacoplamiento de Proveedores LLM, Rotación Multi-Key y Registro de Llamadas

- **Fecha:** 2026-06-03
- **Estado:** Aceptado
- **ADRs Relacionados:** ADR-0027 (Inteligencia Asimétrica), ADR-0035 (Observabilidad Multi-Provider y Key Rotation).

## Contexto

El sistema AEGEN interactúa con modelos de lenguaje en 22 puntos de llamada (call sites) distribuidos en 17 archivos de especialistas (CBT, Psicotrading, Chat) y servicios de fondo (MemorySummarizer, FactExtractor, SemanticChunker).

Actualmente, estos puntos están acoplados a funciones en `src/core/engine.py` como `get_fast_llm()` o `get_analytical_llm()`, las cuales instancian modelos de Groq (primario) y OpenRouter (fallback) con parámetros hardcodeados en el archivo de configuración global `src/core/config/base.py`.

Este diseño presenta cuatro limitaciones críticas:
1. **Instabilidad de Cuotas:** El motor primario (Groq Free Tier) tiene un límite rígido de 8,000 TPM. Los prompts acumulativos en CBT/Chat (que incluyen `evolution_note` y `learned_preferences` del usuario) superan habitualmente los 30,000 caracteres (~8,500 tokens), disparando errores HTTP 413 de cuota y bloqueando el sistema.
2. **Sub-utilización de Recursos:** Google AI Studio provee una cuota gratuita más generosa por API Key (15 RPM / 1M TPM para Gemini 2.5 Flash), y el proyecto cuenta con soporte para rotación multi-key (`RoundRobinKeyProvider`), pero este solo se implementó para RAG asíncrono, dejando el Chat y la terapia CBT vulnerables.
3. **Opacidad (Falta de Medición):** No existe un mecanismo sistemático para inspeccionar la estructura completa, contenido y tamaño exacto de los prompts enviados en producción, lo que dificulta optimizar la eficiencia de tokens sin destruir la memoria del sistema.
4. **Peligro en Tiempo de Importación:** Módulos de memoria como `reranker.py` y `fact_extractor.py` realizan la invocación de creación de LLM en tiempo de carga del módulo (import time), lo que congela las conexiones con keys estáticas.

## Decisión

Se adopta una arquitectura desacoplada basada en la simplificación del motor de LLMs en dos capas lógicas y una herramienta operativa:

### 1. Capa de Proveedores Abstractos (Provider Layer)
Refactorizar la inicialización en `src/core/engine.py` bajo una estructura de proveedores abstractos:
- **`GeminiProvider` (Primario):** Consume todas las API keys configuradas en el entorno (rotación automática mediante `RoundRobinKeyProvider`). Será el motor principal para Chat, CBT, Psicotrading y tareas analíticas.
- **`GroqProvider` (Respaldo):** Configurado como fallback automático secundario para absorber peticiones si Gemini agota sus cuotas.
- **`OpenRouterProvider` (Catastrófico):** Fallback final de emergencia.

### 2. Capa de Registro y Configuración Declarativa (Registry Layer)
- Introducir un sistema dual compatible con LangChain Expression Language (LCEL):
  1. **La interfaz `ManagedLLM(Runnable)`:** Un objeto perezoso que hereda de `Runnable` de LangChain. Permite usar el operador de tubería pipe (`|`) y métodos como `bind_tools()` de forma nativa resolviendo el modelo y las llaves en runtime en cada invocación de `.invoke()` o `.ainvoke()`.
  2. **El decorador `@llm_call(name="call_name")`:** Para inyectar una instancia de `ManagedLLM` en funciones de invocación imperativa directa.
- El registro interactúa con un `CallRegistry` centralizado y resuelve dinámicamente qué proveedor y modelo instanciar basándose en un manifiesto YAML.
- **Manifiesto YAML (`config/llm_inventory.yaml`):** Archivo de configuración que mapea nombres de llamadas (ej: `cbt_therapeutic_response`) a su proveedor primario, modelo, parámetros de temperatura, límites de tokens de entrada y lista de fallbacks en orden de precedencia. La edición del YAML altera el enrutamiento de modelos en caliente sin modificar el código Python.
- **Limpieza de engine.py (Sin Fachada Bridge):** Se descartan los puentes de compatibilidad intermedia. Las factorías obsoletas de `src/core/engine.py` se eliminarán definitivamente. Todos los 17 archivos consumidores se migran directamente a `src/core/llm_registry.py`.
- **Invocaciones perezosas (lazy):** Convertir las llamadas estáticas de `reranker.py` y `fact_extractor.py` a resoluciones perezosas en el constructor.

### 3. Herramienta de Visibilidad (Telemetría Numérica Estructural Segura - Retención Cero de Texto)
Aprovechar la interceptación de `ManagedLLM` para:
- Medir los tamaños de caracteres por sección constituyente del prompt (`identity`, `soul`, `mirror`, `rag_context`, `history`, `user_message`) y enviarlos a la metadata en runtime.
- **Queda estrictamente prohibido** el almacenamiento en RAM, logs o persistencia en disco de cualquier fragmento de texto de entrada crudo de los usuarios.
- Exponer dos nuevos endpoints en FastAPI bajo control de acceso de autenticación de administrador (`access_controller.py`):
  - `GET /system/llm-inventory`: Devuelve la lista de llamadas declaradas, su estado, configuraciones de modelos activos y telemetría de rendimiento.
  - `GET /system/llm-telemetry`: Permite auditar latencias, consumo de tokens, costos estimados en USD y composición numérica de caracteres por sección de prompt para análisis cuantitativo.

## Consecuencias

### Positivas:
- **Resiliencia de Rate Limits:** Al usar Gemini Flash como primario con rotación de múltiples keys, el sistema puede procesar prompts de más de 30k caracteres de manera gratuita y concurrente.
- **Intercambiabilidad:** Cambiar un especialista de Gemini a Llama 3 o GPT-4 se reduce a editar una línea en `config/llm_inventory.yaml`, eliminando deploys de código para experimentos de modelos.
- **Cumplimiento de Privacidad Absoluto:** Al no guardar texto crudo del usuario, no hay riesgo de exfiltración de información sensible (terapéutica/financiera).
- **Cero Overhead por Regex:** No se procesan expresiones regulares complejas sobre textos grandes de prompts, eliminando consumo de CPU inútil y bloqueos de I/O.

### Negativas:
- **Consistencia en Local:** El desarrollo local requiere configurar al menos una API Key de Gemini o tener Groq activo para que el inventario funcione con su cadena de fallback.
