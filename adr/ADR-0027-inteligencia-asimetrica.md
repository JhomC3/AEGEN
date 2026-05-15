# ADR-0027 - Inteligencia Asimétrica y Resiliencia Activa de LLMs

- **Fecha:** 2026-05-13
- **Estado:** Implementado
- **Autor:** MAGI (Asistente)
- **Aprobado por:** Usuario (JhomC3)

## Contexto

Con la migración a la arquitectura de Agentic Hub (ADR-0026), AEGEN cuenta con múltiples especialistas y un enrutador (Router) dinámico. Hasta ahora, el sistema dependía de un "LLM global" (una cadena de fallbacks lineal y monolítica) para todas las tareas.

Los modelos disponibles en el mercado (mayo 2026) presentan trade-offs drásticos:
- **Groq (`openai/gpt-oss-120b`):** Extremadamente rápido (baja latencia) pero con capacidades de razonamiento generalistas.
- **OpenRouter (`minimax/minimax-m2.5:free`):** Alta capacidad analítica para tareas complejas, pero sujeto a alta latencia, límites de cuota (rate limits) y caídas esporádicas.
- **Google Gemini (`gemini-2.5-flash`):** Óptimo para contexto masivo (RAG) pero menos adecuado para el motor de diálogo principal en términos de latencia vs Groq.

Forzar un modelo de "alta calidad pero lento" (Minimax) en la entrada del pipeline (Router y Chat casual) degrada severamente la Experiencia de Usuario (UX). Por el contrario, notificar al usuario final de cada fallo técnico genera "fatiga de alertas".

## Decisión

Se adopta una arquitectura de **Inteligencia Asimétrica y Alertas Fuera de Banda (Out-of-band)**:

1. **Enrutamiento Asimétrico de Modelos:**
   - **Router y Chat General:** Se asigna Groq (`gpt-oss-120b`) como modelo principal. Garantiza decisiones de ruteo y respuestas conversacionales en milisegundos (< 1s).
   - **Especialistas Complejos (TCC, Psicotrading):** Se asigna OpenRouter (`minimax-m2.5:free`) como modelo principal, dado que el usuario tolera mayor latencia a cambio de alta fidelidad analítica.

2. **Cadenas de Resiliencia Locales:**
   - Si el modelo de alta fidelidad (OpenRouter) falla por cuota o latencia, el sistema hace fallback automático a la red rápida (Groq), asegurando que el bot nunca quede inoperativo.

3. **Alertas Fuera de Banda (Admin Routing):**
   - Los fallos de modelos (404, 503, Timeouts) ya no se manejan silenciosamente ni se reportan al usuario final.
   - El motor LLM publicará un evento `system.llm_failure` en el `RedisEventBus`.
   - Un nuevo servicio (`admin_notifier.py`) escuchará estos eventos y enviará un mensaje de diagnóstico por Telegram *exclusivamente* a un `ADMIN_CHAT_ID` preconfigurado.

## Consecuencias

### Positivas
- **UX Óptima:** Latencia casi cero para interacciones cotidianas y navegación de menús/ruteo.
- **Calidad Analítica:** Profundidad técnica reservada para cuando realmente importa (terapia, trading).
- **Observabilidad Proactiva:** El administrador sabe inmediatamente si un proveedor retiró un modelo (ej. 404 de Kimi) sin tener que leer logs del servidor.

### Negativas / Riesgos
- **Complejidad de Configuración:** `src/core/engine.py` se vuelve más complejo al gestionar múltiples cadenas de instanciación.
- **Dependencia del Event Bus:** La observabilidad profunda ahora depende de que Redis esté en línea. Si Redis cae, las alertas se registran solo en los logs locales de archivo.
