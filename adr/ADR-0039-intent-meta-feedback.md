# ADR-0039 - IntentType META_FEEDBACK para feedback de estilo de respuesta

- **Fecha:** 2026-06-02
- **Estado:** Propuesto

## Contexto

El análisis forense de logs de producción (2026-05-31 a 2026-06-02) reveló un feedback loop negativo en el sistema de routing cuando un usuario en sesión terapéutica (CBT) intenta ajustar el estilo de respuesta de MAGI.

El flujo problemático observado:

1. Usuario en sesión CBT dice "tus respuestas son muy largas"
2. `RoutingAnalyzer` clasifica como `IntentType.VULNERABILITY` (confianza 0.95)
3. `therapeutic_session.should_maintain_therapeutic_session()` retorna True (el intent no es TOPIC_SHIFT)
4. `enhanced_router` fuerza `cbt_specialist` con acciones `["handle_resistance", "validate_frustration"]`
5. CBT genera respuesta larga (~7000 tokens) con formato checklist
6. Usuario se frustra, repite el feedback → ciclo se repite

La causa raíz: no existe un `IntentType` que distinga el meta-feedback sobre el estilo de respuesta de la vulnerabilidad emocional. Son categorías ortogonales que el sistema trata como la misma.

La infraestructura para persistir y aplicar preferencias de estilo ya existe en el codebase:
- `StyleAnalyzer` (`src/personality/style_analyzer.py`) detecta señales lingüísticas
- `SystemPromptBuilder` (`src/personality/prompt_builder.py`) renderiza preferencias aprendidas en el system prompt
- `UserProfileManager` (`src/core/profile_manager.py`) tiene `update_style_signals()` para persistir preferencias

Lo que falta es la pieza de routing que conecte el feedback del usuario con esta infraestructura.

## Decisión

1. **Añadir `IntentType.META_FEEDBACK`** al enum en `src/core/routing_models.py`. Este intent cubre mensajes donde el usuario se refiere al comportamiento o estilo de MAGI, no a su propio estado emocional.

2. **Añadir `META_FEEDBACK` a `SESSION_BREAKING_INTENTS`** en `therapeutic_session.py`. Esto permite que un usuario en sesión CBT ajuste el estilo sin ser forzado de vuelta al CBT. La protección terapéutica (ADR-0024) sigue activa para todos los demás intents.

3. **No crear un nuevo especialista.** El `chat_specialist` existente maneja el acknowledgment del feedback, y las preferencias se persisten via la infraestructura existente de `UserProfileManager`.

4. **No añadir un segundo LLM call** para reformatear respuestas. Las preferencias aprendidas se inyectan en el system prompt del especialista, que genera directamente en el formato preferido.

## Consecuencias

**Positivas:**
- Los usuarios en sesión CBT pueden ajustar el estilo de respuesta sin quedar atrapados
- Se reutiliza la infraestructura existente (StyleAnalyzer, prompt_builder, UserProfileManager) sin código nuevo
- El cambio es backward-compatible (añadir un valor a un enum no rompe consumers)
- Zero latencia adicional (no hay segundo LLM call)

**Negativas:**
- Debilita ligeramente la protección de sesión terapéutica de ADR-0024 al añadir una nueva puerta de salida. Mitigación: los patterns de META_FEEDBACK son suficientemente específicos para no confundirse con resistencia terapéutica real.
- Posibles falsos positivos si "muy largo" aparece en contexto no relacionado. Mitigación: el LLM router tiene contexto conversacional completo; los patterns solo boostean confianza.

**Riesgos nuevos:**
- Un usuario en crisis real podría usar frases que matcheen META_FEEDBACK para salir de la sesión CBT involuntariamente. La probabilidad es baja dado que los patterns son específicos al estilo de respuesta, no al estado emocional.
