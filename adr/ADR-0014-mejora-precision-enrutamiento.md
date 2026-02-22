# ADR-0014: Routing Precision Improvement

## Estado
**ACEPTADO** - Implementación completada para mejorar precisión en detección de vulnerabilidad

## Contexto

### Problema Identificado
El sistema de routing (migrado a function calling en ADR-0009) presentaba desincronizaciones críticas y falta de precisión en la detección de estados emocionales vulnerables:
1. **Desincronización de Intents**: `vulnerability` y `topic_shift` existían en el Enum pero no en el Literal del tool, impidiendo que el LLM los retornara.
2. **Confusión en Prompts**: Uso de términos no definidos como `chatter`.
3. **Thresholds Rígidos**: Confianza de 0.7 causaba fallbacks excesivos a Chat.
4. **Patterns Débiles**: Detección de vulnerabilidad basada en palabras muy genéricas sin exclusión de contexto (ej: trading).
5. **Falta de Contexto**: El router no conocía el intent o especialista previo.

## Decisión

### 1. Sincronización de Esquemas
Se sincronizó `routing_tools.py` con `IntentType`, permitiendo al LLM retornar todos los intents soportados. Se corrigieron inconsistencias semánticas en `routing_prompts.py`.

### 2. Sistema de Confianza Multi-nivel
Se implementó una lógica de decisión de 3 niveles en `enhanced_router.py` para el intent de vulnerabilidad:
- **Nivel 1 (>85%)**: Routing directo a `cbt_specialist` con acciones de empatía profunda.
- **Nivel 2 (60-85%)**: Routing a `cbt_specialist` con instrucciones de clarificación emocional.
- **Nivel 3 (50-60%)**: Routing a `chat_specialist` para monitoreo pasivo de señales emocionales.

### 3. Refinamiento de Pattern Matching TCC
Se actualizaron los `INTENT_PATTERNS` en `routing_patterns.py` incluyendo categorías basadas en Terapia Cognitivo-Conductual (TCC):
- Emociones negativas (básicas y secundarias).
- Distorsiones cognitivas (catastrofización, personalización, etc.).
- Pensamientos automáticos negativos.
- **Exclusiones Negativas**: Se añadieron patterns para ignorar frustración técnica de trading que no constituye vulnerabilidad clínica.

### 4. Enriquecimiento de Contexto
Se modificó `routing_utils.py` y `routing_analyzer.py` para inyectar `previous_intent` y `previous_specialist` en el prompt del LLM, permitiendo decisiones informadas por el flujo de la conversación.

### 5. Flexibilización de Fast Path
Se ajustaron las regex de saludos y cortesía para permitir puntuación, evitando llamadas innecesarias al LLM por simples saludos con exclamaciones.

## Consecuencias

### Positivas
- ✅ **Precisión**: Mejora drástica en la detección de crisis emocionales.
- ✅ **Resiliencia**: Sistema de 3 niveles evita falsos positivos agresivos.
- ✅ **Coherencia**: El LLM ahora conoce la historia inmediata del routing.
- ✅ **Performance**: Fast path más robusto ahorra tokens y latencia.

### Negativas
- ❌ **Complejidad**: La lógica de `apply_routing_decision` es ahora más sofisticada.
- ❌ **Mantenimiento**: Los patterns de TCC requieren revisión periódica.

## Validación
Se crearon y validaron los siguientes tests:
1. `tests/unit/test_routing_intent_sync.py`: Valida sincronización de esquemas.
2. `tests/integration/test_vulnerability_routing.py`: Valida lógica de 3 niveles y patterns de TCC (incluyendo exclusiones de trading).

---
**Fecha**: 2026-01-29
**Autor**: Antigravity (IA)
