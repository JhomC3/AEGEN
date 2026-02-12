# Plan A.3: Overhaul de Personalidad y Coherencia de MAGI

> **Fecha Original:** 11 de Febrero, 2026
> **Fecha Revisión:** 12 de Febrero, 2026
> **Estado:** Finalizado (12 de Febrero, 2026)
> **Fase:** Bloque A.3 del Plan Maestro `v0.7.0-saneamiento-y-evolucion.md`
> **ADR Asociado:** `adr/ADR-0023-overhaul-personalidad-reflejo-natural.md`
> **Referencia:** `docs/investigacion/investigacion_identidad_openclaw.md`

---

## 1. Diagnóstico del Estado Actual

### Problemas Identificados

| #   | Problema                                                 | Ubicación                            | Impacto                                                                               |
| --- | -------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------- |
| P1  | **Dialecto hard-coded con if/elif**                      | `prompt_builder.py:111-120`          | Rígido, no escala, no diferencia entre "confirmado" y "asumido"                       |
| P2  | **Mirroring estático (~30%)**                            | `prompt_builder.py:123-126`          | Instrucción vaga que invita al LLM a inventar jerga de regiones incorrectas           |
| P3  | **Regla de Oro rígida**                                  | `prompt_builder.py:63`               | "casual, directa, con opinión" se aplica siempre, incluso en TCC donde no corresponde |
| P4  | **SOUL.md sin principio de adaptabilidad**               | `personality/base/SOUL.md`           | No establece que MAGI se adapta al usuario; solo define su esencia fija               |
| P5  | **IDENTITY.md contradictorio**                           | `personality/base/IDENTITY.md`       | Promete "apoyo incondicional" que choca con la "firmeza" del TCC                      |
| P6  | **Sin análisis de estilo conversacional**                | No existe                            | MAGI no detecta si el usuario es formal/informal, breve/verboso                       |
| P7  | **EvolutionDetector no detecta preferencia lingüística** | `memory/evolution_detector.py:26-38` | No rastrea cambios en cómo el usuario prefiere que le hablen lingüísticamente         |
| P8  | **Lógica duplicada en Callers**                          | `chat_tool.py` / `cbt_tool.py`       | Extracción de mensajes recientes duplicada en cada especialista                       |

### Lo que Funciona Bien (Mantener)

- Arquitectura de capas (Identity → Soul → Adaptation → Skill → Runtime)
- `PersonalityLoader` y `PersonalityManager` con cache
- Pipeline de localización pasiva/activa (`ProfilingManager` + `profile_localization.py`)
- Sistema de evolución incremental (`EvolutionDetector` → `EvolutionApplier`)
- `COUNTRY_DATA` en `localization.py` con regiones granulares

---

## 2. Principio Rector

> **El dialecto de MAGI es una PREFERENCIA del usuario, NO una inferencia ni una imposición geográfica.**
> La ubicación define el contexto (hora, noticias), pero no la identidad.
> Si no hay preferencia explícita → **Neutralidad Cálida** (Latinoamericano Estándar) + **Eco Léxico**.
> Si hay preferencia confirmada → Dialecto específico.

La instrucción de "Mirroring (~30%)" se reemplaza por **Eco Léxico**: MAGI no imita acentos, pero sí adopta el vocabulario específico (sustantivos/verbos) del usuario para reducir la fricción cognitiva.

---

## 3. Arquitectura Propuesta (Soul Stack Simplificado)

Se descarta el "PersonaSynthesizer" (LLM Meta-Prompting) por complejidad injustificada en esta fase. Se opta por un ensamblaje determinista robusto.

```
┌─────────────────────────────────────────────────┐
│            PROMPT FINAL AL LLM                   │
├─────────────────────────────────────────────────┤
│ Capa 5: RUNTIME                                  │
│   Hora local, canal, RAG, memoria               │
├─────────────────────────────────────────────────┤
│ Capa 4: SKILL OVERLAY                            │
│   Tono + instrucciones + reglas lingüísticas     │
│   del skill activo (chat, tcc, futuro...)        │
├─────────────────────────────────────────────────┤
│ Capa 3: ESPEJO (The Mirror) ← NUEVA             │
│   Dialecto PREFERIDO + Eco Léxico + Estilo       │
│   Datos concretos desde StyleAnalyzer            │
├─────────────────────────────────────────────────┤
│ Capa 2: ALMA (The Soul) ← MEJORADA              │
│   Core Truths + Adaptabilidad + Anti-Patterns    │
│   INMUTABLE en runtime                           │
├─────────────────────────────────────────────────┤
│ Capa 1: IDENTIDAD (The Identity) ← MEJORADA     │
│   Quién soy, nombre, emoji, estilo base          │
│   INMUTABLE en runtime                           │
└─────────────────────────────────────────────────┘
```

---

## 4. Pasos de Implementación

### Paso 0: Migración de Datos (Legacy Fix) ← NUEVO

**Archivo a crear:** `scripts/migrate_dialects.py`

**Razón:** Usuarios existentes con `confirmed_by_user=True` perderían su personalización si no migramos ese dato a `preferred_dialect`.

```python
# Lógica de migración:
# Para cada perfil en DB:
#   Si localization.confirmed_by_user IS True AND personality_adaptation.preferred_dialect IS None:
#       personality_adaptation.preferred_dialect = localization.dialect
#       Guardar perfil
```

---

### Paso 1: Refinar Tipos en `types.py`

**Archivo:** `src/personality/types.py`

(Ya implementado parcialmente, confirmar estructura final)

```python
@dataclass
class StyleSignals:
    """Señales de estilo detectadas en mensajes recientes."""
    detected_language: str  # "es", "en", "pt", etc.
    formality_indicator: str  # "muy_formal", "formal", "casual", "muy_casual"
    brevity: str  # "telegrafico", "conciso", "verboso"
    uses_emoji: bool

@dataclass
class LinguisticProfile:
    """Perfil lingüístico procesado para inyección en el prompt."""
    dialect: str  # "neutro", "colombiano", "mexicano", "argentino", etc.
    preferred_dialect: str | None # Preferencia explicita o migrada
    dialect_confirmed: bool  # Si la ubicación fue confirmada (útil como hint)
    formality_level: float  # 0.0-1.0
    preferred_style: str  # "casual", "formal"
```

---

### Paso 2: Mejorar `StyleAnalyzer` (Fixes Técnicos) ← CORREGIDO

**Archivo:** `src/personality/style_analyzer.py`

**Correcciones sobre la versión actual:**
1.  **NO usar `.lower()` antes de detectar formalidad:** Las mayúsculas son señal de formalidad.
2.  **Mejorar detección de idioma:** Evitar falsos positivos de portugués (usar trigramas o stopwords más específicas).

```python
class StyleAnalyzer:
    def analyze(self, recent_messages: list[str]) -> StyleSignals:
        full_text_raw = " ".join(recent_messages)
        full_text_lower = full_text_raw.lower()

        # Detectar formalidad usando raw text (para ver Capitalization)
        formality = self._detect_formality(full_text_raw, full_text_lower)

        return StyleSignals(
            detected_language=self._detect_language(full_text_lower),
            formality_indicator=formality,
            # ... resto igual
        )
```

---

### Paso 3: Refactorizar `SOUL.md` (The Soul)

(Ya implementado, verificar alineación con Core Truth #6 "Espejo Inteligente")

---

### Paso 4: Corregir `IDENTITY.md` ← CORREGIDO

**Archivo:** `src/personality/base/IDENTITY.md`

**Razón:** "Apoyo incondicional" genera conflicto con la terapia TCC (que cuestiona distorsiones). Cambiar a "Apoyo Honesto".

```markdown
- **Naturaleza:** Tu amigo cercano y apoyo honesto.
- **Vibe:** (...) Soy cercano, honesto y mi prioridad absoluta es serte útil, diciéndote la verdad que necesitas oír.
```

---

### Paso 5: Mejorar Skill Overlays

**Archivos:** `chat_overlay.md` y `tcc_overlay.md`

Implementar las secciones de "Reglas Lingüísticas" definidas en el plan original, asegurando que TCC enfatice la "Firmeza Benevolente".

---

### Paso 6: Refactorizar `prompt_builder.py`

**Archivo:** `src/personality/prompt_builder.py`

Eliminar el if/elif hard-coded y reemplazar `_build_user_adaptation_section` por la lógica modular.

#### 6a. Método `_build_mirror_section`

```python
async def _build_mirror_section(
    self,
    profile: dict[str, Any],
    recent_user_messages: list[str] | None = None,
) -> str:
    # 1. Obtener datos
    adaptation = profile.get("personality_adaptation", {})
    localization = profile.get("localization", {})

    # 2. Analizar estilo (StyleAnalyzer mejorado)
    style = style_analyzer.analyze(recent_user_messages) if recent_user_messages else None

    # 3. Construir perfil lingüístico
    linguistic = LinguisticProfile(
        dialect=localization.get("dialect", "neutro"),
        preferred_dialect=adaptation.get("preferred_dialect"),
        dialect_confirmed=localization.get("confirmed_by_user", False),
        # ...
    )

    # 4. Renderizar
    section = f"# ESPEJO: CÓMO ME ADAPTO A TI\n"
    section += self._render_dialect_rules(linguistic)     # Dialecto/Idioma
    section += self._render_style_adaptation(style)       # Estilo (Formalidad/Brevedad)

    return section
```

#### 6b. Método `_render_dialect_rules` ← CORREGIDO (Sin caminos muertos)

```python
def _render_dialect_rules(self, linguistic: LinguisticProfile) -> str:
    base = "- **Idioma:** Responde SIEMPRE en el idioma del usuario.\n"

    # Prioridad 1: Preferencia Explícita
    if linguistic.preferred_dialect:
        return base + f"- **Dialecto ACTIVO:** {linguistic.preferred_dialect}. Úsalo con naturalidad.\n"

    # Prioridad 2: Ubicación Confirmada (Sugerencia suave)
    if linguistic.dialect_confirmed and linguistic.dialect != "neutro":
        return base + (
            f"- **Contexto Regional:** El usuario está en {linguistic.dialect}. "
            "Puedes usar modismos locales suaves si él los usa primero, pero NO fuerces el acento.\n"
        )

    # Default: Neutralidad Cálida
    return base + (
        "- **Dialecto Base:** Neutralidad Cálida (Español Latinoamericano Estándar).\n"
        "- **ECO LÉXICO:** Adopta el vocabulario específico del usuario (sustantivos/verbos) "
        "para generar cercanía, pero mantén la gramática neutra.\n"
    )
```

#### 6c. Método `_render_style_adaptation` ← NUEVO (Faltaba en plan original)

```python
def _render_style_adaptation(self, style: StyleSignals | None) -> str:
    if not style:
        return ""

    rules = ["- **Adaptación de Estilo:**"]

    # Formalidad
    if style.formality_indicator == "muy_formal":
        rules.append("  * El usuario es MUY FORMAL. Elimina coloquialismos y sé profesional.")
    elif style.formality_indicator == "casual":
        rules.append("  * El usuario es casual. Puedes relajarte y ser cercano.")

    # Brevedad
    if style.brevity == "telegrafico":
        rules.append("  * El usuario es telegráfico. Sé ULTRA-CONCISO.")
    elif style.brevity == "verboso":
        rules.append("  * El usuario se extiende. Puedes dar respuestas más desarrolladas.")

    return "\n".join(rules) + "\n"
```

---

### Paso 7: Crear Utilidad Compartida `message_utils.py` ← NUEVO

**Archivo:** `src/core/message_utils.py`

**Razón:** Evitar duplicación de código en `chat_tool` y `cbt_tool` (DRY).

```python
def extract_recent_user_messages(messages: list[Any], limit: int = 10) -> list[str]:
    """Extrae el contenido de texto de los últimos mensajes humanos."""
    return [
        m.content for m in messages
        if isinstance(m, HumanMessage) and m.content
    ][-limit:]
```

---

### Paso 8: Actualizar Callers (`chat_tool.py` y `cbt_tool.py`)

Importar `extract_recent_user_messages` y pasar el resultado al `system_prompt_builder`.

---

### Paso 9: Enriquecer `EvolutionDetector` con Normalización

**Archivo:** `src/memory/evolution_detector.py`

Actualizar el prompt para detectar `linguistic_preference`.
**Importante:** Instruir al LLM para que `explicit_dialect_request` normalice valores (ej. "paisa" -> "colombiano", "madrid" -> "español").

---

### Paso 10: Actualizar `EvolutionApplier`

**Archivo:** `src/memory/evolution_applier.py`

Implementar la lógica de aplicación de cambios, asegurando que los deltas de formalidad/humor se apliquen sobre los valores existentes con `clamp(0.0, 1.0)`.

---

### Paso 11: Tests y Verificación

1.  **Test Unitario `StyleAnalyzer`:** Verificar detección correcta de formalidad con/sin mayúsculas.
2.  **Test Integración Prompt:** Verificar que `preferred_dialect` sobrescribe la neutralidad.
3.  **Verificación Manual:** Ejecutar `scripts/migrate_dialects.py` en entorno local.

---

## 5. Archivos Afectados (Resumen Final)

| Archivo | Acción | Descripción |
| :--- | :--- | :--- |
| `src/core/message_utils.py` | **CREAR** | Utilidad DRY para extracción de mensajes. |
| `scripts/migrate_dialects.py` | **CREAR** | Script de migración de datos legacy. |
| `src/personality/style_analyzer.py` | **EDITAR** | Mejoras en lógica de detección (fix P2). |
| `src/personality/prompt_builder.py` | **REFACTORIZAR** | Nueva lógica modular + `_render_style_adaptation`. |
| `src/personality/base/IDENTITY.md` | **EDITAR** | "Apoyo Honesto" en lugar de "Incondicional". |
| `src/personality/skills/*_overlay.md` | **EDITAR** | Reglas lingüísticas específicas por skill. |
| `src/agents/specialists/**` | **EDITAR** | Usar `message_utils` y pasar mensajes al builder. |
| `src/memory/evolution_*.py` | **EDITAR** | Detectar y persistir preferencias lingüísticas. |

---

## 6. Orden de Ejecución

1.  **Core Utils:** Crear `message_utils.py`.
2.  **Style Logic:** Mejorar `style_analyzer.py`.
3.  **Markdown Content:** Actualizar `IDENTITY.md` y Overlays.
4.  **Builder Refactor:** Modificar `prompt_builder.py` (el cambio más grande).
5.  **Integration:** Actualizar `chat_tool.py` y `cbt_tool.py`.
6.  **Evolution:** Actualizar Detector y Applier.
7.  **Migration:** Crear y ejecutar script de migración.
8.  **Verify:** Correr tests.
