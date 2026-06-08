# INVESTIGACIÓN: Justificación de Desacoplamiento y Sistema de Medición LLM

- **Fecha:** 2026-06-03
- **Estado:** Completado
- **Autores:** Antigravity (AI Agent) y Operador de AEGEN
- **Contexto:** Incidente de Límite de Tokens (Groq 413) y Degradación de Latencia en Producción.

---

## 1. Antecedentes del Incidente

Durante las pruebas y auditorías en el entorno de producción (VM GCP, rama `develop`, versión `v0.8.4` / `v0.9.0`), se experimentaron fallos intermitentes de tipo HTTP 413 (Rate Limit) al interactuar con el especialista en TCC (CBT) y el chat general.

### Diagnóstico Numérico Inicial (`[CBT-PROMPT-SIZE]`)
Para entender la causa, se inyectaron logs temporales de medición de tamaño en `src/personality/skills/tcc/tools.py`. Los resultados arrojaron mediciones empíricas exactas:
- **Total de caracteres de prompt:** Entre `31,959` y `34,214` caracteres (~8,000 a 8,500 tokens).
- **Límite de Groq (Free Tier):** 8,000 TPM (Tokens Por Minuto).
- **Desglose de sub-componentes:**
  - `IDENTITY`: 16 caracteres.
  - `SOUL.md`: 2,574 caracteres.
  - `MIRROR` (Preferencias Aprendidas): **10,393 caracteres** (100% compuesto por `learned_preferences` del perfil de usuario, acumulando 139 ítems sin deduplicar).
  - `SKILL`: 1,623 caracteres.
  - `RUNTIME`: **12,008 caracteres** (91% compuesto por el documento clínico `evolution_note` de Redis, con 10,970 bytes).
  - `ENRICHED_CONTEXT`: 143 caracteres.

### Conclusión del Diagnóstico
El 62% del prompt del sistema en cada turno de conversación estaba compuesto por dos llaves de estado acumulativas (`learned_preferences` y `evolution_note`). Esto causaba que una sola llamada excediera los límites de la cuota gratuita de Groq.

---

## 2. Reevaluación Crítica y la Conversación

### El Error de la Propuesta Inicial (Parche Ciego)
Inicialmente, el agente propuso dos soluciones rápidas y destructivas:
1. Truncar el `evolution_note` clínico a un tamaño fijo de 2,000 caracteres.
2. Limitar la lista de `learned_preferences` a los últimos 20 elementos.

El operador solicitó una **reevaluación profunda**.

Al analizar el código y el negocio, descubrimos que **estas propuestas eran destructivas**:
- El `evolution_note` contiene un historial clínico estructurado de intervenciones, estado emocional y de riesgo del usuario. Cortarlo arbitrariamente ciega al terapeuta digital sobre el historial del paciente.
- Las `learned_preferences` son instrucciones operativas y reglas de estilo aprendidas. Descartar las anteriores a las últimas 20 haría que MAGI olvidara decisiones que el usuario tomó meses atrás, frustrándolo al cometer errores ya superados.

### La Causa Raíz Arquitectónica
El problema real no era el volumen de datos, sino **la falta de desacoplamiento y visibilidad**:
1. Los proveedores y modelos de LLM están acoplados directamente en código Python (`src/core/engine.py`). Cambiar de proveedor requiere modificar código en múltiples archivos.
2. Volamos a ciegas. No existía un inventario centralizado de las llamadas LLM que realiza el sistema, ni de los prompts reales (con contenido completo) que se envían.
3. La rotación de API keys (`RoundRobinKeyProvider`) solo estaba disponible para la búsqueda RAG asíncrona, dejando al motor principal de chat desprotegido ante rate-limits.

---

## 3. Decisiones Tomadas

Para solucionar esto de raíz ("hacerlo bien", sin parches) y bajo la directiva del operador de usar **exclusivamente el free-tier de Google AI Studio (Gemini)** como primario y **Groq** como respaldo, se acordó el siguiente diseño simplificado:

### Capa A: Proveedores Desacoplados (Provider Layer)
- Mover la conexión del LLM a proveedores abstractos (`GeminiProvider` y `GroqProvider`).
- El `GeminiProvider` usará el `RoundRobinKeyProvider` con **todas las API keys de Google AI Studio disponibles** configuradas en el entorno. Esto escala la cuota gratuita (15 RPM / 1M TPM por key) multiplicada por el número de keys.
- `GroqProvider` se mantendrá operativo y configurado como el motor de respaldo automático (`fallback`).

### Capa B: Registro e Inventario de Llamadas (Registry Layer)
- Introducir el decorador `@llm_call(call_type="nombre_llamada")` en cada uno de los call sites.
- Crear un manifiesto de configuración editable en `config/llm_inventory.yaml`. El YAML definirá qué modelo, qué temperatura y qué orden de fallbacks usa cada llamada identificada. El YAML sobrescribe el comportamiento por defecto del decorador sin requerir tocar código.
- Cada función decorada se registra automáticamente a nivel de runtime en un catálogo global.

### Herramienta de Visibilidad (Medición y Observabilidad)
- **Dumps de prompts completos:** Capturar de forma sistemática y transparente el contenido completo que sale de `prompt_builder.py` y se envía al LLM. Implementar un mecanismo de redacción para proteger datos personales en logs.
- **Endpoints de administración:**
  - `GET /system/llm-inventory`: Devuelve el catálogo completo de llamadas registradas, sus configuraciones activas y telemetría histórica (latencia, tokens consumidos, tasa de error).
  - `GET /system/prompts/recent`: Devuelve el historial de prompts reales y completos procesados por el sistema para auditoría forense instantánea.

---

## 4. Alineación Arquitectónica y Beneficios

1. **ROI Alto:** La complejidad añadida de la capa de registro se justifica al habilitar el desacoplamiento total y la visibilidad sin suposiciones de prompts.
2. **Degradación Suave:** Si Gemini falla o agota todas las keys configuradas, el sistema degrada automáticamente a Groq y luego a OpenRouter de forma transparente, registrando el evento de fallback en las métricas.
3. **Mantenibilidad:** El inventario permite a desarrolladores futuros e IAs entender de un vistazo cómo interactúa el sistema con los modelos de lenguaje.

*Este documento sirve como justificación histórica oficial y base técnica para el plan de ejecución `docs/planes/2026-06-03-desacoplamiento-y-observabilidad-llm.md` y el registro de decisión de arquitectura `adr/ADR-0040-desacoplamiento-proveedores-llm-inventario.md`.*
