# ADR-0015: Localización, Robustez RAG y Continuidad de Enrutamiento

## Estado
Aceptado (Enero 2026)

## Contexto
El sistema presentaba tres debilidades críticas identificadas durante pruebas de usuario:
1. **Pérdida de Contexto en Routing:** El router no recibía el contenido de los mensajes previos, causando saltos erráticos (ej: de TCC a Chat) cuando el usuario respondía a ejercicios.
2. **Inconsistencia Lingüística:** MAGI alternaba entre jergas de diferentes países (España, Argentina) sin un criterio claro, rompiendo la inmersión.
3. **Fragilidad Técnica:** Errores de parseo JSON por decoraciones de Markdown del LLM y timeouts frecuentes en la activación de archivos en Google File Search.

## Decisiones

### 1. Enrutamiento con Memoria de Diálogo (Continuidad)
Se modifica `RoutingAnalyzer` y `routing_utils.py` para extraer los últimos 5 mensajes de la sesión.
- **Formato:** Diálogo natural `Usuario: / Asistente:`.
- **Regla de Stickiness:** Se implementó una lógica de inercia en `enhanced_router.py` que aumenta la confianza de enrutamiento si el especialista sugerido coincide con el anterior (`last_specialist`), siempre que no haya un cambio de tema drástico.

### 2. Localización Multi-plataforma Automática
Se implementó un sistema de detección pasiva basado en metadatos:
- **Webhook:** Extracción de `language_code` (ej: `es-AR`) desde los eventos entrantes.
- **Perfil:** Almacenamiento de `localization` (país, jerga, zona horaria) en Redis.
- **PromptBuilder:** Inyección dinámica de reglas lingüísticas (voseo para AR, tuteo para ES) para asegurar consistencia absoluta en la personalidad de MAGI.

### 3. Robustez RAG y Consolidación
- **Exponential Backoff:** Se reemplazó el loop de espera fijo por una política de reintentos exponenciales (2s, 4s, 8s, 16s, 32s, 60s) para la activación de archivos en Google Cloud.
- **Regex JSON Extractor:** El `ConsolidationManager` ahora utiliza expresiones regulares para extraer el bloque JSON puro de la respuesta del LLM, ignorando bloques de código Markdown o texto explicativo.
- **Global Knowledge Filter:** Se ajustó la búsqueda de archivos para incluir explícitamente archivos con etiquetas `CORE`, `GLOBAL` o prefijo `knowledge/`.

## Consecuencias

### Positivas
- **Hilos Terapéuticos Estables:** Reducción drástica de saltos erráticos a ChatBot durante ejercicios.
- **Personalidad Coherente:** MAGI ahora mantiene el mismo dialecto durante toda la sesión.
- **Mayor Estabilidad:** Eliminación de fallos por `JSONDecodeError` y reducción de errores de "Archivo no encontrado" en el RAG.

### Negativas/Riesgos
- **Consumo de Tokens:** El enrutamiento ahora consume ~100-200 tokens adicionales por el historial inyectado.
- **Dependencia de Metadatos:** Si la plataforma (Telegram/WhatsApp) no provee el `language_code`, el sistema hace fallback a español neutro.
