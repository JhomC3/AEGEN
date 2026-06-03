# Forense de Latencia — Despliegue Soul Stack v0.8.5

- **Fecha:** 2026-06-02
- **ChatID:** 6095416210
- **Correlation IDs analizados:** `ede5e01`, `d1d6626`, `32d6ee1`, `1f5eb32`
- **Archivos modificados:** `prompt_builder.py`, `chat/tools.py`, `tcc/tools.py`

---

## Timeline Comparativo (4 runs)

| Fase | Run #1 (cold) | Run #2 (warm) | Run #3 (hot) | Run #4 (hot) |
|------|--------------|--------------|-------------|-------------|
| Telegram → Adapter | +882.1s | +328.2s | +3.0s | +2.0s |
| Debounce → EventProcessor | 0.0s | 0.0s | 0.0s | 0.0s |
| Orchestrator creation | 4.0s | 6.0s | 0.0s* | 0.0s* |
| Router LLM | 2.4s / 2532t | 1.7s / 1953t | 1.2s / 1799t | 1.1s / 1805t |
| Context Retrieval + RAG | 9.1s | 2.0s | 2.7s | 2.2s |
| Reranker | 0.0s | 6.0s | 1.0s | 1.0s |
| [CBT-RAG] → LLM init gap | **51.9s** | **69.0s** | **0.0s** | 0.0s |
| Groq/OpenRouter init | 1.0s | 2.0s | 0.0s | 1.0s |
| Main LLM call | ❌ (template bug) | 3.1s / 8249t | 2.5s / 8643t | ❌ (rate limit) |
| Chain routing → END | 3.0s | 1.0s | 1.0s | 1.0s |
| Session save | 1.0s | 1.0s | 1.0s | 1.0s |
| **Total processing** | **con error** | **91.1s** | **8.0s** | **con fallback** |

---

## Hallazgos

### 🔴 F1: Gap sin telemetría en [CBT-RAG] → LLM init (52-69s en cold start)

En Runs 1-2 hubo una brecha de 52 y 69 segundos entre el log `[CBT-RAG]` y `Initializing Groq`, sin ningún log intermedio. El código entre ambos puntos ejecuta:
- `system_prompt_builder.build()` → `PersonalityManager.get_base()` → lectura archivos `.md`
- `style_analyzer.analyze()` → `langdetect.detect()` (carga perfiles de idioma)
- `profiling_manager.get_profiling_hint()` → carga perfil desde SQLite/Redis

En Runs 3-4 (warm) la brecha fue 0.0s. **Conclusión:** cold start de módulos de personalidad sin logs de trazabilidad. Imposible saber cuál operación fue la lenta sin añadir telemetría.

### 🟡 F2: Rate limit de Groq free tier (Run #4)

```
Error code: 413 - Request too large for model openai/gpt-oss-120b
Limit 8000 TPM, Requested 9312
```

El prompt creció a 9312 tokens porque la conversación acumuló 16 mensajes. El `except` del tool devolvió el fallback correctamente. **No es regresión de nuestros cambios.**

### 🟡 F3: RAG global persistentemente lento (1.7-9.0s)

| Run | Latencia RAG global | Fragmentos |
|-----|---------------------|------------|
| #1 | 9030ms | 1 |
| #2 | 1767ms | 0 |
| #3 | 2616ms | 0 |
| #4 | 2237ms | 0 |

El embedding search contra `models/gemini-embedding-001` tarda 1.7-9 segundos incluso cuando retorna 0 fragmentos. Problema de infraestructura (API de Google), no de código.

### 🟡 F4: `get_analytical_llm()` crea clientes nuevos en cada tool call

En todos los runs se observa:
```
Initializing Groq with model: openai/gpt-oss-120b
Initializing OpenRouter with model: minimax/minimax-m2.5:free
```

La función se llama dentro del tool (no es singleton), re-creando clientes HTTP cada vez. En warm runs no impacta (clientes subyacentes usan connection pooling), pero es un antipatrón.

### 🟢 F5: Sistema estable post warm-up (Run #3)

Procesamiento completo en **8 segundos** con el nuevo crisis detector, `SystemMessage` fix, y `langdetect` funcionando. Sin errores.

---

## Recomendaciones

| # | Acción | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 1 | Añadir logs en `system_prompt_builder.build()` para diagnosticar cold starts | Medio | 2 líneas |
| 2 | Mover `get_analytical_llm()` a singleton en `engine.py` | Medio | 5 líneas |
| 3 | Reducir `history_limit` de 5 a 3 en `tcc/tools.py:149` (evitar rate limit Groq) | Alto | 1 línea |
| 4 | Investigar lentitud RAG global con Google embedding | Medio | Investigación |
