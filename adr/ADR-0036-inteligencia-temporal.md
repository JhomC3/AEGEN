# ADR-0036 - Inteligencia Temporal: Metadata en Facts y Patrones de Comportamiento

- **Fecha:** 2026-05-29
- **Estado:** Aceptado
- **Autor:** MAGI AI
- **ADR Relacionado:** ADR-0030 (Time Decay), ADR-0032 (facts atómicos)

## Contexto

El sistema ya inyecta la hora local del usuario en el prompt (Layer 5 del Soul Stack), y el Time Decay de ADR-0030 aplica un factor exponencial por antigüedad a los fragmentos de memoria. Sin embargo, hay tres capacidades temporales ausentes que degradan la calidad de las respuestas:

**1. Los hechos no llevan metadata temporal enriquecida**

ADR-0032 introdujo la ingesta atómica de facts. Cada fact tiene `created_at`, pero no tiene campos explícitos como `day_of_week`, `hour_of_day`, `week_number`. Esto hace imposible detectar patrones temporales del tipo "los lunes el usuario reporta más ansiedad".

**2. La antigüedad de los hechos es invisible para el LLM**

El Two-Stage Retrieval (ADR-0030) reordena los fragmentos por su score de decaimiento, pero el LLM recibe los fragmentos sin saber cuándo fueron registrados. No puede distinguir entre "esto lo dijo hace 3 días" vs "esto lo dijo hace 6 meses".

**3. Sin conciencia de calendario**

El sistema no sabe si hoy es un día festivo, el inicio de semana laboral, una fecha relevante para el usuario (cumpleaños, aniversario de evento importante). Esta información está en los facts, pero no se agrega como contexto de calendário.

## Decisión

### 1. Metadata temporal enriquecida en facts atómicos

Al ingestar un fact (vía `save_knowledge` o `IngestionPipeline`), añadir campos derivados de `created_at`:

```python
# En src/memory/sqlite_store.py o ingestion_pipeline.py
from datetime import datetime, timezone

def _enrich_temporal_metadata(fact: dict) -> dict:
    ts = datetime.fromisoformat(fact.get("created_at", datetime.now(timezone.utc).isoformat()))
    fact["day_of_week"] = ts.weekday()        # 0=lunes, 6=domingo
    fact["hour_of_day"] = ts.hour             # 0-23
    fact["week_of_year"] = ts.isocalendar()[1]
    fact["is_weekend"] = ts.weekday() >= 5
    return fact
```

Estos campos se almacenan en el campo `metadata` (JSON) del fact, no como columnas nuevas, para evitar una migración de schema.

### 2. Antigüedad visible de hechos en el prompt

Al formatear los fragmentos para el prompt (en `format_knowledge_for_prompt` o el context_retriever), añadir el delta temporal en lenguaje natural:

```python
from datetime import datetime, timezone

def _format_age(created_at: str) -> str:
    delta = datetime.now(timezone.utc) - datetime.fromisoformat(created_at)
    if delta.days == 0:
        return "hoy"
    elif delta.days <= 7:
        return f"hace {delta.days} día{'s' if delta.days > 1 else ''}"
    elif delta.days <= 30:
        weeks = delta.days // 7
        return f"hace {weeks} semana{'s' if weeks > 1 else ''}"
    elif delta.days <= 365:
        months = delta.days // 30
        return f"hace {months} mes{'es' if months > 1 else ''}"
    else:
        years = delta.days // 365
        return f"hace {years} año{'s' if years > 1 else ''}"
```

El fragmento en el prompt pasa de:

> `"Tiene deficit calórico sostenido de 400kcal."`

A:

> `"[hace 3 semanas] Tiene deficit calórico sostenido de 400kcal."`

Esto permite que el LLM razone sobre si la información sigue siendo relevante o es obsoleta.

### 3. Detección de patrones temporales en ConsolidationWorker

Añadir una fase al `ConsolidationWorker` que, cada 7 días (o cada N consolidaciones), agrupe los facts del usuario por `day_of_week` y `hour_of_day` del metadata, y genere un "insight temporal":

```python
# Pseudocódigo del análisis de patrones
facts_by_day = group_by(user_facts, key=lambda f: f["metadata"]["day_of_week"])
for day, facts in facts_by_day.items():
    anxiety_facts = [f for f in facts if "ansied" in f["content"].lower()]
    if len(anxiety_facts) > 3:
        save_knowledge({
            "content": f"Patrón detectado: el usuario reporta ansiedad con más frecuencia los {DAYS[day]}.",
            "type": "temporal_pattern",
            "confidence": 0.7,
        })
```

Los insights temporales se almacenan como facts de tipo `temporal_pattern` con `confidence=0.7` (provisional) y se van refinando conforme llegan más datos.

### 4. Conciencia de calendario (fase futura, v0.10+)

La detección de días festivos y fechas relevantes del usuario requiere:

- Una tabla de festivos por país (del perfil del usuario: Colombia, México, etc.)
- Extracción de fechas importantes de los facts (cumpleaños, aniversarios)

Esta fase se implementa en v0.10 cuando B.7 esté activo. No es bloqueante para las fases 1-4.

## Consecuencias

### Positivas

- **Hechos con contexto:** El LLM distingue entre información reciente y obsoleta sin depender solo del ranking de relevancia.
- **Patrones accionables:** Los insights temporales pueden aparecer en el resumen semanal: "Noté que los lunes sueles tener más energía — ¿quieres planificar las tareas más exigentes para esos días?"
- **Dependencia mínima:** Solo requiere cambios en `ingestion_pipeline.py`/`sqlite_store.py` y `consolidation_worker.py`. Sin nueva tabla de schema.

### Negativas / Riesgos

- **Ruido en patrones:** Con pocas semanas de datos, los patrones temporales pueden ser estadísticamente espurios. El campo `confidence=0.7` (provisional) y el umbral de `>3 ocurrencias` mitigan esto.
- **Overhead en formateo:** Añadir la edad de cada fragmento añade ~20-50 tokens al prompt por consulta. Aceptable dentro del límite de tokens de Layer 5.
- **Privacidad de patrones:** Los patrones temporales son datos de comportamiento sensibles. Deben almacenarse con el mismo nivel de protección que los facts médicos y solo ser accesibles para el usuario propietario.
