# Evidencia de fallos preexistentes (2026-10-21)

Objetivo: demostrar que los fallos de test no los introduce la reparación 002.
No se usó `git stash` ni `git worktree`; se trabajó en directorios temporales
fuera del árbol y no se modificó el checkout.

## 1. Código de `HEAD` puro

```bash
TMP=$(mktemp -d /private/var/folders/.../opencode/aegen-head.XXXXXX)
git archive HEAD | tar -x -C "$TMP"
cd "$TMP"
set -a; source /Users/jhomc/Proyectos/AEGEN/.env; set +a
PYTHONPATH="$TMP" /Users/jhomc/Proyectos/AEGEN/.venv/bin/python -m pytest \
  tests/unit/orchestrator/test_context_retriever.py::test_context_retriever_analytical_intent \
  tests/unit/memory/test_atomic_knowledge.py::test_save_knowledge_atomic \
  tests/unit/memory/test_hierarchical_ingestion.py::test_hierarchical_ingestion_flow \
  tests/integration/test_telegram_webhook.py::test_telegram_webhook_success_flow \
  -q -p no:cacheprovider --tb=line
```

Salida relevante:

```text
tests/unit/orchestrator/test_context_retriever.py:112: assert 0 == 1
tests/unit/memory/test_atomic_knowledge.py:66: KeyError: 'user_name'
.../google/api_core/grpc_helpers.py:77: google.api_core.exceptions.InvalidArgument:
  400 API key not valid. Please pass a valid API key. [reason: "API_KEY_INVALID"]
tests/integration/test_telegram_webhook.py:126: AssertionError:
  Expected ainvoke to have been awaited once. Awaited 0 times.
=========================== short test summary info ============================
FAILED tests/unit/orchestrator/test_context_retriever.py::test_context_retriever_analytical_intent
FAILED tests/unit/memory/test_atomic_knowledge.py::test_save_knowledge_atomic
FAILED tests/unit/memory/test_hierarchical_ingestion.py::test_hierarchical_ingestion_flow
FAILED tests/integration/test_telegram_webhook.py::test_telegram_webhook_success_flow
4 failed
```

## 2. `HEAD` + cambios locales del dueño, sin la reparación

El test de bienestar y su skill son archivos locales sin seguimiento, por lo que
no existen en `HEAD`. Para el contrafactual correcto se construyó un baseline:
`git archive HEAD` y encima los cambios locales del dueño, excluyendo los 8
módulos y los tests de esta reparación. Así se reproduce el estado anterior a la
reparación sin tocar el checkout.

```bash
BASE=$(mktemp -d /private/var/folders/.../opencode/aegen-baseline.XXXXXX)
git archive HEAD | tar -x -C "$BASE"
rsync -a \
  --exclude='.git/' --exclude='.venv/' --exclude='.env' \
  --exclude='apps/' --exclude='storage/' --exclude='entrega-senda/' \
  --exclude='ops/' --exclude='.tmp-gcp/' --exclude='logs/' \
  --exclude='.pytest_cache/' --exclude='__pycache__/' --exclude='specs/' \
  --exclude='src/api/services/event_processor.py' \
  --exclude='src/api/services/debounce_manager.py' \
  --exclude='src/api/routers/status.py' \
  --exclude='src/agents/specialists/skill_based_specialist.py' \
  --exclude='src/agents/orchestrator/master_orchestrator.py' \
  --exclude='src/personality/skills/chat/tools.py' \
  --exclude='src/memory/embeddings.py' \
  --exclude='src/memory/hybrid_search.py' \
  --exclude='tests/unit/api/test_event_response.py' \
  --exclude='tests/unit/api/test_debounce_lock.py' \
  --exclude='tests/unit/api/test_health_llm.py' \
  --exclude='tests/unit/memory/test_embedding_degradation.py' \
  --exclude='tests/unit/orchestrator/test_skill_error_state.py' \
  --exclude='tests/unit/personality/test_chat_tool_errors.py' \
  --exclude='tests/integration/test_telegram_webhook.py' \
  /Users/jhomc/Proyectos/AEGEN/ "$BASE/"
cd "$BASE"
set -a; source /Users/jhomc/Proyectos/AEGEN/.env; set +a
PYTHONPATH="$BASE" /Users/jhomc/Proyectos/AEGEN/.venv/bin/python -m pytest \
  tests/unit/orchestrator/test_context_retriever.py::test_context_retriever_analytical_intent \
  tests/unit/memory/test_atomic_knowledge.py::test_save_knowledge_atomic \
  tests/unit/memory/test_hierarchical_ingestion.py::test_hierarchical_ingestion_flow \
  tests/unit/personality/test_bienestar_skill.py::test_undo_aborta_si_lectura_de_huella_falla \
  tests/integration/test_telegram_webhook.py::test_telegram_webhook_success_flow \
  -q -p no:cacheprovider --tb=line
```

Salida relevante:

```text
tests/unit/orchestrator/test_context_retriever.py:112: assert 0 == 1
tests/unit/memory/test_atomic_knowledge.py:66: KeyError: 'user_name'
.../google/api_core/grpc_helpers.py:77: google.api_core.exceptions.InvalidArgument:
  400 API key not valid. Please pass a valid API key. [reason: "API_KEY_INVALID"]
tests/unit/personality/test_bienestar_skill.py:232: AssertionError: assert True is False
tests/integration/test_telegram_webhook.py:126: AssertionError:
  Expected ainvoke to have been awaited once. Awaited 0 times.
=========================== short test summary info ============================
FAILED tests/unit/orchestrator/test_context_retriever.py::test_context_retriever_analytical_intent
FAILED tests/unit/memory/test_atomic_knowledge.py::test_save_knowledge_atomic
FAILED tests/unit/memory/test_hierarchical_ingestion.py::test_hierarchical_ingestion_flow
FAILED tests/unit/personality/test_bienestar_skill.py::test_undo_aborta_si_lectura_de_huella_falla
FAILED tests/integration/test_telegram_webhook.py::test_telegram_webhook_success_flow
5 failed
```

## 3. Sensibilidad de las regresiones nuevas

En una copia temporal se restauró el comportamiento anterior (si el cerrojo está
ocupado, la tarea vuelve sin esperar) y se ejecutaron las regresiones nuevas:

```text
test_rafaga_durante_procesamiento_se_atiende_despues:
  AssertionError: assert ['hola'] == ['hola', 'segundo']
test_rafaga_durante_procesamiento_llega_a_telegram:
  AssertionError: assert [('1', 'eco:hola')] == [('1', 'eco:hola'), ('1', 'eco:segundo')]
```

En otra copia se mantuvo la espera pero se desactivó el latido de renovación:

```text
test_renovacion_evita_procesamiento_simultaneo_al_expirar_ttl:
  AssertionError: el mismo chat no debe procesarse dos veces a la vez
  assert 2 == 1
```

Es decir, las pruebas fallan con el defecto y pasan con la reparación.

## Conclusión

Los cinco fallos existen sin el código reparado. Los cinco son defectos de test
o de fixture; en `hierarchical_ingestion` la llamada real además choca con la
`GOOGLE_API_KEY` inválida. Ninguno se declara reparado en la spec 002. El único
que la reparación toca es el webhook de Telegram, porque su mock estaba
desalineado con el contrato real; se corrigió y ahora pasa.
