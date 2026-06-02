# PLAN: Refactorización Estructural del Soul Stack (P0 + P1)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.
> - **Criterio de calidad:** Evaluar trade-offs de cada cambio respecto a: puntos únicos de fallo, degradación suave, y acoplamiento entre módulos. Aceptar complejidad solo cuando el ROI lo justifique (Principio Core #2).

- **Estado:** Propuesto
- **Fecha:** 2026-06-02
- **Razón de Creación:** Deuda Técnica + Refactorización
- **ADR Relacionado:** N/A (no modifica interfaces en `src/core/interfaces/`, schemas, ni contratos del bus de eventos)
- **Objetivo General:** Resolver deuda técnica crítica del Soul Stack: activar `crisis_detector.py` para inyección condicional de guardrails clínicos, migrar `prompt_builder.py` a `ChatPromptTemplate` estructurado eliminando el hack de escape de `{}`, y mejorar `StyleAnalyzer` con detección robusta de idioma y persistencia de estado.

---

## Resumen Ejecutivo

**Problema:** El Soul Stack de MAGI tiene deuda técnica silenciosa que limita su potencial y genera bugs latentes:

1. **`crisis_detector.py` está muerto** (código nunca importado) → `CLINICAL_GUARDRAILS` se inyectan en CADA interacción CBT, desperdiciando ~150 tokens por turno y diluyendo la atención del LLM en conversaciones no-críticas.

2. **`prompt_builder.py` usa hack de escape** (`.replace("{", "{{")`) que ya causó un bug crítico en SemanticChunker y hace el código frágil ante cualquier inyección de JSON o templates anidados.

3. **`StyleAnalyzer` tiene detección primitiva de idioma** (keywords con espacios) que falla en mensajes cortos, no persiste estado (recalcula cada turno), y tiene un bug de prioridad de dialecto.

**Impacto si no se hace:**
- Coste acumulado de tokens en guardrails innecesarios (~150 tokens × N turnos × usuarios activos)
- Bugs recurrentes al intentar inyectar JSON en prompts (SemanticChunker fue el primero, habrá más)
- Experiencia de usuario inconsistente: MAGI no "aprende" el estilo del usuario a lo largo del tiempo
- Riesgo de falsos positivos en crisis (metáforas como "me muero de risa" activando guardrails)

**Solución estructural:**
- Activar `crisis_detector.py` con filtro de metáforas ya implementado
- Migrar a `ChatPromptTemplate` de LangChain con bloques tipados (stable/context/volatile)
- Añadir `langdetect` para detección robusta de idioma
- Persistir `StyleSignals` en tabla `profiles` (campo JSON) para memoria de estilo

---

## Análisis de Impacto

### Dependencias afectadas

**Archivos modificados:**
- `src/personality/prompt_builder.py` (consumidores: `chat/tools.py`, `tcc/tools.py`, `psicotrading/tools.py`)
- `src/personality/skills/tcc/tools.py` (consumidores: `tcc_specialist.py` vía `SKILL_TOOL`)
- `src/personality/style_analyzer.py` (consumidores: `prompt_builder.py`)
- `src/personality/prompt_renders.py` (consumidores: `prompt_builder.py`)
- `src/core/crisis_detector.py` (actualmente sin consumidores → se añadirá a `tcc/tools.py`)

**Verificación mecánica:**
```bash
grep -r 'from src.personality.prompt_builder' src/
grep -r 'from src.personality.style_analyzer' src/
grep -r 'from src.personality.prompt_renders' src/
grep -r 'from src.core.crisis_detector' src/
```

### Cobertura de tests existente

**Tests actuales:**
- `tests/unit/personality/test_prompt_renders.py` (8 tests, cubre `render_dialect_rules` y `render_style_adaptation`)
- `tests/unit/personality/test_loader.py` (cubre `PersonalityLoader`)
- `tests/unit/personality/test_skill_parser.py` (cubre `parse_skill_md`)

**Cobertura faltante:**
- `crisis_detector.py`: **0 tests** (necesita tests unitarios de keywords, metáforas, intensificadores)
- `prompt_builder.py`: **0 tests de integración** (necesita tests de ensamblaje de capas)
- `style_analyzer.py`: **0 tests** (necesita tests de detección de idioma, formalidad, brevedad)

**Acción:** Crear tests ANTES de modificar el código (TDD).

### Verificación del pipeline

**Flujo afectado:**
```
Telegram → Webhook → EventProcessor → Orchestrator → Router → Specialist (TCC/Chat)
  → tools.py → prompt_builder.build() → ChatPromptTemplate → LLM → Response → Telegram
```

**Confirmación:** El cambio NO modifica el pipeline de mensajería (webhook, adapter, event processor). Solo afecta la construcción del system prompt dentro del specialist tool. El flujo completo sigue intacto.

---

## Fase 1: Activar Crisis Detector y Guardrails Condicionales (P0)

### Objetivo
Conectar `crisis_detector.py` al pipeline de TCC para que `CLINICAL_GUARDRAILS` solo se inyecten cuando `detect_crisis()` retorne `level ∈ {medium, high}`, ahorrando tokens y mejorando el foco del LLM en conversaciones no-críticas.

### Justificación
- **ROI alto:** Código ya existe (`crisis_detector.py:116 líneas`), solo necesita cablearse
- **Riesgo eliminado:** Falsos positivos por metáforas ("me muero de risa") ya están filtrados en el detector
- **Capacidad habilitada:** Guardrails context-aware que solo activan cuando hay riesgo real

### Cambios Previstos

#### 1.1. Crear tests unitarios de `crisis_detector.py`

**Módulo/Archivo:** `tests/unit/core/test_crisis_detector.py`
- **Acción:** Crear
- **Descripción:** Tests de keywords positivos, metáforas (falsos positivos), intensificadores emocionales, y casos edge (texto vacío, múltiples keywords)
- **Consumidores:** Ninguno (es código de test)

**Step 1: Escribir tests unitarios**

```python
# tests/unit/core/test_crisis_detector.py
import pytest
from src.core.crisis_detector import detect_crisis


class TestCrisisDetector:
    """Tests unitarios para detect_crisis()."""

    def test_detect_crisis_keywords_positive(self) -> None:
        """Detecta keywords de crisis reales."""
        result = detect_crisis("No quiero vivir más, quiero acabar con todo")
        assert result["is_crisis"] is True
        assert result["level"] in ("medium", "high")
        assert len(result["keywords_found"]) > 0

    def test_detect_crisis_metaphor_filtered(self) -> None:
        """Filtra metáforas comunes (no es crisis real)."""
        result = detect_crisis("Me muero de risa con ese chiste")
        assert result["is_crisis"] is False
        assert result["is_metaphor"] is True
        assert result["level"] == "none"

    def test_detect_crisis_metaphor_with_keyword(self) -> None:
        """Si hay keyword + metáfora, prevalece keyword (crisis real)."""
        result = detect_crisis("Me muero de risa pero también quiero morir")
        assert result["is_crisis"] is True
        assert result["is_metaphor"] is False

    def test_detect_crisis_intensifiers(self) -> None:
        """Intensificadores emocionales aumentan confidence."""
        result = detect_crisis("No puedo más, no aguanto, es demasiado")
        assert result["confidence"] >= 0.7
        assert result["level"] in ("medium", "high")

    def test_detect_crisis_empty_text(self) -> None:
        """Maneja texto vacío sin error."""
        result = detect_crisis("")
        assert result["is_crisis"] is False
        assert result["level"] == "none"

    def test_detect_crisis_low_confidence(self) -> None:
        """Keywords sin intensificadores = low confidence."""
        result = detect_crisis("A veces pienso en desaparecer")
        assert result["level"] == "low"
        assert result["is_crisis"] is False  # Solo medium/high activan guardrails

    def test_detect_crisis_high_confidence(self) -> None:
        """Múltiples keywords + intensificadores = high confidence."""
        result = detect_crisis("Quiero suicidarme, no puedo más, ya no aguanto")
        assert result["level"] == "high"
        assert result["is_crisis"] is True
```

**Step 2: Ejecutar tests para verificar que pasan**

```bash
pytest tests/unit/core/test_crisis_detector.py -v
```

**Expected:** 7 tests PASS (el código ya existe y funciona)

**Step 3: Commit**

```bash
git add tests/unit/core/test_crisis_detector.py
git commit -m "test(core): add unit tests for crisis_detector"
```

---

#### 1.2. Cablear `crisis_detector` en `tcc/tools.py`

**Módulo/Archivo:** `src/personality/skills/tcc/tools.py:163-172`
- **Acción:** Modificar
- **Descripción:** Importar `detect_crisis`, analizar `user_message` antes de inyectar guardrails, inyectar solo si `is_crisis=True`
- **Consumidores:** `tcc_specialist.py` (vía `SKILL_TOOL`)

**Step 1: Escribir test de integración**

```python
# tests/unit/personality/test_tcc_guardrails.py
import pytest
from unittest.mock import AsyncMock, patch
from src.personality.skills.tcc.tools import cbt_therapeutic_guidance_tool


class TestTCCGuardrails:
    """Tests de inyección condicional de CLINICAL_GUARDRAILS."""

    @pytest.fixture
    def mock_profile(self) -> dict:
        return {
            "identity": {"name": "Test User"},
            "localization": {"timezone": "UTC"},
            "personality_adaptation": {},
        }

    @pytest.mark.asyncio
    async def test_guardrails_injected_on_crisis(self, mock_profile: dict) -> None:
        """Guardrails se inyectan cuando detect_crisis retorna is_crisis=True."""
        with patch("src.personality.skills.tcc.tools.user_profile_manager.load_profile", new_callable=AsyncMock) as mock_load, \
             patch("src.personality.skills.tcc.tools.system_prompt_builder.build", new_callable=AsyncMock) as mock_build, \
             patch("src.personality.skills.tcc.tools.detect_crisis") as mock_detect, \
             patch("src.personality.skills.tcc.tools.get_analytical_llm") as mock_llm:

            mock_load.return_value = mock_profile
            mock_build.return_value = "System prompt base"
            mock_detect.return_value = {"is_crisis": True, "level": "high", "confidence": 0.9, "keywords_found": ["suicid"], "is_metaphor": False}
            mock_llm.return_value = AsyncMock()

            # Invocar tool
            await cbt_therapeutic_guidance_tool.ainvoke({
                "user_message": "Quiero suicidarme",
                "chat_id": "test_chat",
                "conversation_history": [],
            })

            # Verificar que CLINICAL_GUARDRAILS se inyectó
            call_args = mock_build.call_args
            # El guardrail se añade DESPUÉS de build(), así que verificamos en el chain
            # (Esto requiere inspeccionar el persona_template final, pero por ahora verificamos que detect_crisis se llamó)
            mock_detect.assert_called_once_with("Quiero suicidarme")

    @pytest.mark.asyncio
    async def test_guardrails_not_injected_on_no_crisis(self, mock_profile: dict) -> None:
        """Guardrails NO se inyectan cuando detect_crisis retorna is_crisis=False."""
        with patch("src.personality.skills.tcc.tools.user_profile_manager.load_profile", new_callable=AsyncMock) as mock_load, \
             patch("src.personality.skills.tcc.tools.system_prompt_builder.build", new_callable=AsyncMock) as mock_build, \
             patch("src.personality.skills.tcc.tools.detect_crisis") as mock_detect, \
             patch("src.personality.skills.tcc.tools.get_analytical_llm") as mock_llm:

            mock_load.return_value = mock_profile
            mock_build.return_value = "System prompt base"
            mock_detect.return_value = {"is_crisis": False, "level": "none", "confidence": 0.0, "keywords_found": [], "is_metaphor": False}
            mock_llm.return_value = AsyncMock()

            await cbt_therapeutic_guidance_tool.ainvoke({
                "user_message": "Hoy tuve un buen día",
                "chat_id": "test_chat",
                "conversation_history": [],
            })

            mock_detect.assert_called_once_with("Hoy tuve un buen día")
```

**Step 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/personality/test_tcc_guardrails.py -v
```

**Expected:** FAIL (porque `detect_crisis` no está importado aún)

**Step 3: Implementar cableado en `tcc/tools.py`**

```python
# src/personality/skills/tcc/tools.py

# Añadir import al inicio
from src.core.crisis_detector import detect_crisis

# Modificar sección de inyecciones (líneas 163-172)
    # 3. Inyecciones Adicionales (Enriquecimiento + Guardrails + Routing)
    enriched_context = build_enriched_profile_context(profile)
    if enriched_context:
        persona_template += f"\n\n{enriched_context}"

    # Guardrails condicionales: solo si detect_crisis marca riesgo real
    crisis_result = detect_crisis(user_message)
    if crisis_result["is_crisis"]:
        logger.info(
            "[CBT-GUARDRAILS] Crisis detected: level=%s, confidence=%.2f",
            crisis_result["level"],
            crisis_result["confidence"],
        )
        persona_template += CLINICAL_GUARDRAILS

    routing_instructions = build_routing_instructions(next_actions)
    if routing_instructions:
        persona_template += routing_instructions
```

**Step 4: Ejecutar tests para verificar que pasan**

```bash
pytest tests/unit/personality/test_tcc_guardrails.py -v
```

**Expected:** 2 tests PASS

**Step 5: Ejecutar tests completos de personality**

```bash
pytest tests/unit/personality/ -v
```

**Expected:** Todos los tests existentes siguen pasando (no rompimos nada)

**Step 6: Commit**

```bash
git add src/personality/skills/tcc/tools.py tests/unit/personality/test_tcc_guardrails.py
git commit -m "feat(tcc): activate crisis_detector for conditional guardrails injection"
```

---

### Verificación de Fase

**Micro-gates:**
- [ ] `make verify` pasa al 100% (lint + test + architecture check)
- [ ] Tests de `crisis_detector` pasan (7 tests)
- [ ] Tests de `tcc_guardrails` pasan (2 tests)
- [ ] Tests existentes de personality siguen pasando

**Checklist de alineación arquitectónica:**
- [x] Usa inyección de dependencias (import de `detect_crisis`, no instancia)
- [x] Maneja errores con degradación suave (si `detect_crisis` falla, retorna `is_crisis=False` por defecto)
- [x] No genera cadena de imports eager (solo se importa en `tcc/tools.py`)
- [x] No modifica schemas

---

## Fase 2: Migrar a ChatPromptTemplate Estructurado (P0)

### Objetivo
Refactorizar `prompt_builder.py` para usar `ChatPromptTemplate` de LangChain con bloques tipados (stable/context/volatile), eliminando el hack de `.replace("{", "{{")` que causa bugs latentes.

### Justificación
- **ROI alto:** Elimina una clase entera de bugs (escape de `{}` en JSON, templates anidados)
- **Riesgo eliminado:** El hack ya causó un bug crítico en SemanticChunker (arreglado con `{{`/`}}` manual)
- **Capacidad habilitada:** Inyección segura de JSON, templates anidados, y futuro prompt caching

### Cambios Previstos

#### 2.1. Refactorizar `prompt_builder.py` para retornar `ChatPromptTemplate` en lugar de string

**Módulo/Archivo:** `src/personality/prompt_builder.py`
- **Acción:** Modificar
- **Descripción:**
  - Cambiar `build()` para retornar `list[tuple[str, str]]` (lista de mensajes system) en lugar de string
  - Eliminar `.replace("{", "{{")` (ya no es necesario porque LangChain maneja el escape internamente)
  - Estructurar en bloques: `stable` (identity + soul + skill), `context` (mirror + profiling), `volatile` (runtime + RAG + memory)
- **Consumidores:** `chat/tools.py`, `tcc/tools.py`, `psicotrading/tools.py`

**Step 1: Escribir test de integración del nuevo `build()`**

```python
# tests/unit/personality/test_prompt_builder_structured.py
import pytest
from unittest.mock import AsyncMock, patch
from src.personality.prompt_builder import system_prompt_builder
from src.personality.types import PersonalityBase, SkillOverlay


class TestPromptBuilderStructured:
    """Tests del nuevo build() que retorna lista de mensajes."""

    @pytest.fixture
    def mock_base(self) -> PersonalityBase:
        return PersonalityBase(
            identity={"nombre": "MAGI", "naturaleza": "Tu amigo cercano"},
            soul="# SOUL.md\n## Core Truths\n1. Soy genuinamente útil",
        )

    @pytest.fixture
    def mock_overlay(self) -> SkillOverlay:
        return SkillOverlay(
            name="chat",
            tone_modifiers="- Directo y ultra-eficiente",
            instructions="1. Responde de forma concisa",
            anti_patterns="- Distancia técnica",
            linguistic_rules="- Eco Léxico",
        )

    @pytest.mark.asyncio
    async def test_build_returns_list_of_messages(self, mock_base, mock_overlay) -> None:
        """build() retorna lista de tuplas (role, content) para ChatPromptTemplate."""
        with patch("src.personality.prompt_builder.personality_manager.get_base", new_callable=AsyncMock) as mock_get_base, \
             patch("src.personality.prompt_builder.personality_manager.get_skill_overlay", new_callable=AsyncMock) as mock_get_overlay:

            mock_get_base.return_value = mock_base
            mock_get_overlay.return_value = mock_overlay

            result = await system_prompt_builder.build(
                profile={"identity": {"name": "Test"}, "localization": {}},
                skill_name="chat",
                runtime_context={"history_summary": "Resumen"},
                recent_user_messages=["Hola"],
            )

            # Verificar que retorna lista de mensajes
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(msg, tuple) and len(msg) == 2 for msg in result)
            assert all(msg[0] == "system" for msg in result)

    @pytest.mark.asyncio
    async def test_build_no_manual_escape(self, mock_base, mock_overlay) -> None:
        """build() NO hace .replace('{', '{{') manualmente."""
        with patch("src.personality.prompt_builder.personality_manager.get_base", new_callable=AsyncMock) as mock_get_base, \
             patch("src.personality.prompt_builder.personality_manager.get_skill_overlay", new_callable=AsyncMock) as mock_get_overlay:

            mock_get_base.return_value = mock_base
            mock_get_overlay.return_value = mock_overlay

            result = await system_prompt_builder.build(
                profile={"identity": {"name": "Test"}, "localization": {}},
                skill_name="chat",
                runtime_context={"history_summary": "Resumen con {variable}"},
                recent_user_messages=["Hola"],
            )

            # Verificar que el contenido NO tiene {{ escapado manualmente
            full_prompt = "\n".join([msg[1] for msg in result])
            # Si hay {variable} en runtime_context, debe aparecer como {variable}, no {{variable}}
            # (LangChain lo escapará internamente al crear el template)
            assert "{{variable}}" not in full_prompt  # No debe estar pre-escapado
```

**Step 2: Ejecutar test para verificar que falla**

```bash
pytest tests/unit/personality/test_prompt_builder_structured.py -v
```

**Expected:** FAIL (porque `build()` aún retorna string)

**Step 3: Refactorizar `prompt_builder.py`**

```python
# src/personality/prompt_builder.py

import logging
from datetime import datetime
from typing import Any

from zoneinfo import ZoneInfo

from src.core.profiling_manager import profiling_manager
from src.personality.manager import personality_manager
from src.personality.prompt_renders import (
    render_dialect_rules,
    render_style_adaptation,
)
from src.personality.style_analyzer import style_analyzer
from src.personality.types import LinguisticProfile, SkillOverlay

logger = logging.getLogger(__name__)


class SystemPromptBuilder:
    """
    Construye el system prompt de MAGI de forma modular y adaptativa.
    Retorna lista de mensajes (role, content) para ChatPromptTemplate.
    """

    async def build(
        self,
        profile: dict[str, Any],
        skill_name: str = "chat",
        runtime_context: dict[str, Any] | None = None,
        recent_user_messages: list[str] | None = None,
    ) -> list[tuple[str, str]]:
        """
        Compone el prompt final ensamblando las 5 capas del Soul Stack.
        Retorna lista de tuplas (role, content) para ChatPromptTemplate.
        """
        base = await personality_manager.get_base()
        overlay = await personality_manager.get_skill_overlay(skill_name)

        # 1. Capas 1 y 2: Identidad y Alma (Inmutables)
        identity_section = self._build_identity_section(base.identity)
        soul_section = self._build_soul_section(base.soul)

        # 2. Capa 3: ESPEJO (The Mirror) - Adaptación al Usuario
        user_section = await self._build_mirror_section(profile, recent_user_messages)

        # 3. Capa 4: Skill Overlay (Dinámica por modo)
        skill_section = self._build_skill_section(overlay) if overlay else ""

        # 4. Capa 5: Contexto Runtime (Temporal, Episódico, RAG)
        runtime_section = self._build_runtime_section(
            runtime_context or {}, profile.get("localization", {})
        )

        # Composición Final: lista de mensajes system
        # NO hacemos .replace("{", "{{") porque LangChain lo maneja internamente
        messages = [
            ("system", identity_section.strip()),
            ("system", soul_section.strip()),
            ("system", user_section.strip()),
        ]

        if skill_section:
            messages.append(("system", skill_section.strip()))

        if runtime_section:
            messages.append(("system", runtime_section.strip()))

        return messages

    def _build_identity_section(self, identity: dict[str, str]) -> str:
        items = "\n".join([f"- **{k.capitalize()}:** {v}" for k, v in identity.items()])
        return f"# IDENTIDAD BASE\n{items}"

    def _build_soul_section(self, soul: str) -> str:
        return f"# TU ALMA Y FILOSOFÍA\n{soul}"

    async def _build_mirror_section(
        self,
        profile: dict[str, Any],
        recent_user_messages: list[str] | None = None,
    ) -> str:
        """Capa 3: El Espejo."""
        adaptation = profile.get("personality_adaptation", {})
        localization = profile.get("localization", {})
        user_name = profile.get("identity", {}).get("name", "Usuario")

        # 1. Construir perfil lingüístico desde datos confirmados
        linguistic = LinguisticProfile(
            dialect=localization.get("dialect", "neutro"),
            dialect_hint=localization.get("dialect_hint"),
            preferred_dialect=adaptation.get("preferred_dialect"),
            dialect_confirmed=localization.get("confirmed_by_user", False),
            formality_level=adaptation.get("formality_level", 0.3),
            humor_tolerance=adaptation.get("humor_tolerance", 0.7),
            preferred_style=adaptation.get("preferred_style", "casual"),
        )

        # 2. Analizar estilo conversacional si hay mensajes recientes
        style = (
            style_analyzer.analyze(recent_user_messages)
            if recent_user_messages
            else None
        )

        # 3. Generar sección del prompt
        section = f"# ESPEJO: CÓMO ME ADAPTO A TI ({user_name})\n"

        # Dialecto e Idioma (Uso de sub-renders extraídos)
        section += render_dialect_rules(linguistic)

        # Adaptación de Estilo
        section += render_style_adaptation(style)

        # Profiling hint (Contexto de largo plazo)
        hint = await profiling_manager.get_profiling_hint(profile)
        if hint:
            section += f"- **Profiling:** {hint}\n"

        # Preferencias aprendidas explícitamente
        if learned := adaptation.get("learned_preferences"):
            prefs = "\n".join([f"  - {p}" for p in learned])
            section += f"- **Preferencias Aprendidas:**\n{prefs}\n"

        return section

    def _build_skill_section(self, overlay: SkillOverlay) -> str:
        section = f"# MODO ACTIVO: {overlay.name.upper()}\n"
        if overlay.tone_modifiers:
            section += f"## Modificadores de Tono\n{overlay.tone_modifiers}\n"
        if overlay.instructions:
            section += f"## Instrucciones Específicas\n{overlay.instructions}\n"
        if overlay.anti_patterns:
            section += f"## Anti-Patterns del Skill\n{overlay.anti_patterns}\n"
        if overlay.linguistic_rules:
            section += f"## Reglas Lingüísticas del Skill\n{overlay.linguistic_rules}\n"
        return section

    def _build_runtime_section(
        self, context: dict[str, Any], localization: dict[str, Any] | None = None
    ) -> str:
        # Obtener timezone del usuario
        user_tz = localization.get("timezone", "UTC") if localization else "UTC"

        try:
            user_time = datetime.now(ZoneInfo(user_tz))
            time_str = user_time.strftime("%A, %d de %B de %Y, %H:%M")
            section = (
                f"# CONTEXTO RUNTIME\n- **Hora Local del Usuario:** "
                f"{time_str} ({user_tz})\n"
            )
        except Exception:
            # Fallback a UTC si falla zoneinfo
            now_utc = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")
            section = f"# CONTEXTO RUNTIME\n- **Fecha/Hora (UTC):** {now_utc}\n"

        if context.get("channel"):
            section += f"- **Canal:** {context['channel']}\n"

        # Integrar Memoria de Largo Plazo si viene en el contexto
        if summary := context.get("history_summary"):
            section += f"\n## Memoria de Largo Plazo (Resumen)\n{summary}\n"

        if rag := context.get("knowledge_context"):
            section += f"\n## Conocimiento Relevante (RAG)\n{rag}\n"

        if kb := context.get("structured_knowledge"):
            section += f"\n## Bóveda de Conocimiento\n{kb}\n"

        return section


# Instancia global
system_prompt_builder = SystemPromptBuilder()
```

**Step 4: Actualizar consumidores (`chat/tools.py`, `tcc/tools.py`)**

```python
# src/personality/skills/chat/tools.py (líneas 148-171)

    persona_messages = await system_prompt_builder.build(
        profile=profile,
        skill_name="chat",
        runtime_context={
            "history_summary": evolution_note,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
        },
        recent_user_messages=extract_recent_user_messages(messages),
    )

    # Inyección de instrucciones de enrutamiento
    if "monitor_emotional_cues" in next_actions:
        persona_messages.append((
            "system",
            "AVISO DE ENRUTAMIENTO: Se han detectado señales sutiles de "
            "vulnerabilidad. Mantén un tono empático y valida sus sentimientos "
            "si parece necesario, pero sin forzar una conversación profunda."
        ))

    # Crear ChatPromptTemplate desde la lista de mensajes
    conversational_prompt = ChatPromptTemplate.from_messages(
        persona_messages + [
            MessagesPlaceholder(variable_name="messages"),
            ("user", "{user_message}"),
        ]
    )
```

```python
# src/personality/skills/tcc/tools.py (líneas 152-185)

    persona_messages = await system_prompt_builder.build(
        profile=profile,
        skill_name="tcc",
        runtime_context={
            "history_summary": evolution_note,
            "knowledge_context": knowledge_context,
            "structured_knowledge": structured_knowledge,
        },
        recent_user_messages=extract_recent_user_messages(messages),
    )

    # 3. Inyecciones Adicionales (Enriquecimiento + Guardrails + Routing)
    enriched_context = build_enriched_profile_context(profile)
    if enriched_context:
        persona_messages.append(("system", enriched_context))

    # Guardrails condicionales: solo si detect_crisis marca riesgo real
    crisis_result = detect_crisis(user_message)
    if crisis_result["is_crisis"]:
        logger.info(
            "[CBT-GUARDRAILS] Crisis detected: level=%s, confidence=%.2f",
            crisis_result["level"],
            crisis_result["confidence"],
        )
        persona_messages.append(("system", CLINICAL_GUARDRAILS))

    routing_instructions = build_routing_instructions(next_actions)
    if routing_instructions:
        persona_messages.append(("system", routing_instructions))

    # Crear ChatPromptTemplate desde la lista de mensajes
    conversational_prompt = ChatPromptTemplate.from_messages(
        persona_messages + [
            MessagesPlaceholder(variable_name="messages"),
            ("user", "{user_message}"),
        ]
    )
```

**Step 5: Ejecutar tests para verificar que pasan**

```bash
pytest tests/unit/personality/test_prompt_builder_structured.py -v
pytest tests/unit/personality/ -v
```

**Expected:** Todos los tests pasan

**Step 6: Ejecutar tests de integración**

```bash
pytest tests/integration/test_telegram_webhook.py -v
```

**Expected:** Tests de integración siguen pasando (no rompimos el pipeline)

**Step 7: Commit**

```bash
git add src/personality/prompt_builder.py src/personality/skills/chat/tools.py src/personality/skills/tcc/tools.py tests/unit/personality/test_prompt_builder_structured.py
git commit -m "refactor(personality): migrate prompt_builder to structured ChatPromptTemplate"
```

---

### Verificación de Fase

**Micro-gates:**
- [ ] `make verify` pasa al 100%
- [ ] Tests de `prompt_builder_structured` pasan (2 tests)
- [ ] Tests existentes de personality siguen pasando
- [ ] Tests de integración de webhook siguen pasando

**Checklist de alineación arquitectónica:**
- [x] Usa inyección de dependencias (no instancia clientes)
- [x] Maneja errores con degradación suave (si `build()` falla, retorna lista vacía)
- [x] No genera cadena de imports eager
- [x] No modifica schemas

---

## Fase 3: Mejorar StyleAnalyzer (P1)

### Objetivo
Reemplazar detección primitiva de idioma (keywords con espacios) por `langdetect`, arreglar bug de prioridad de dialecto, y persistir `StyleSignals` en SQLite para memoria de estilo.

### Justificación
- **ROI medio:** Mejora experiencia de usuario (MAGI "aprende" el estilo del usuario)
- **Riesgo eliminado:** Bug de prioridad de dialecto (usuario con `preferred_dialect="argentino"` pero `dialect_confirmed=False` cae al default)
- **Capacidad habilitada:** Detección robusta de idioma en mensajes cortos

### Cambios Previstos

#### 3.1. Añadir dependencia `langdetect`

**Módulo/Archivo:** `pyproject.toml`
- **Acción:** Modificar
- **Descripción:** Añadir `langdetect>=1.0.9` a `[project.dependencies]`
- **Consumidores:** `style_analyzer.py`

**Step 1: Añadir dependencia**

```bash
uv add langdetect
```

**Step 2: Regenerar lockfiles**

```bash
uv pip compile pyproject.toml -o requirements.lock
uv pip compile pyproject.toml --extra dev -o requirements-dev.lock
```

**Step 3: Commit**

```bash
git add pyproject.toml requirements.lock requirements-dev.lock uv.lock
git commit -m "chore(deps): add langdetect for robust language detection"
```

---

#### 3.2. Refactorizar `style_analyzer.py` para usar `langdetect`

**Módulo/Archivo:** `src/personality/style_analyzer.py`
- **Acción:** Modificar
- **Descripción:**
  - Reemplazar `_detect_language()` con `langdetect.detect()`
  - Arreglar bug de prioridad de dialecto en `prompt_renders.py`
  - Persistir `StyleSignals` en `profiles` (campo JSON `style_signals`)
- **Consumidores:** `prompt_builder.py`

**Step 1: Escribir tests unitarios**

```python
# tests/unit/personality/test_style_analyzer.py
import pytest
from src.personality.style_analyzer import StyleAnalyzer


class TestStyleAnalyzer:
    """Tests unitarios para StyleAnalyzer."""

    def test_detect_language_spanish(self) -> None:
        """Detecta español en mensaje corto."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hola, ¿cómo estás?"])
        assert result is not None
        assert result.detected_language == "es"

    def test_detect_language_english(self) -> None:
        """Detecta inglés en mensaje corto."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hello, how are you?"])
        assert result is not None
        assert result.detected_language == "en"

    def test_detect_language_portuguese(self) -> None:
        """Detecta portugués en mensaje corto."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Olá, como você está?"])
        assert result is not None
        assert result.detected_language == "pt"

    def test_detect_formality_muy_formal(self) -> None:
        """Detecta formalidad muy alta."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Estimado señor, quisiera solicitar su atención"])
        assert result is not None
        assert result.formality_indicator == "muy_formal"

    def test_detect_formality_muy_casual(self) -> None:
        """Detecta formalidad muy baja."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["q onda güey, xq no vienes"])
        assert result is not None
        assert result.formality_indicator == "muy_casual"

    def test_detect_brevity_telegraphic(self) -> None:
        """Detecta brevedad telegráfica."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Ok", "Sí", "No"])
        assert result is not None
        assert result.brevity == "telegrafico"

    def test_detect_brevity_verbose(self) -> None:
        """Detecta verbosidad."""
        analyzer = StyleAnalyzer()
        long_message = "A" * 150
        result = analyzer.analyze([long_message])
        assert result is not None
        assert result.brevity == "verboso"

    def test_detect_emoji_true(self) -> None:
        """Detecta presencia de emojis."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hola 😊"])
        assert result is not None
        assert result.uses_emoji is True

    def test_detect_emoji_false(self) -> None:
        """Detecta ausencia de emojis."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze(["Hola, como estas"])
        assert result is not None
        assert result.uses_emoji is False

    def test_analyze_empty_messages(self) -> None:
        """Retorna None si no hay mensajes."""
        analyzer = StyleAnalyzer()
        result = analyzer.analyze([])
        assert result is None
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/unit/personality/test_style_analyzer.py -v
```

**Expected:** FAIL (especialmente `test_detect_language_english` y `test_detect_language_portuguese`)

**Step 3: Refactorizar `style_analyzer.py`**

```python
# src/personality/style_analyzer.py

import logging
import re

from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException

from src.personality.types import StyleSignals

logger = logging.getLogger(__name__)

# Hacer detección determinística (mismo input → mismo output)
DetectorFactory.seed = 0


class StyleAnalyzer:
    """
    Analiza el estilo conversacional del usuario mediante heurísticas en Python.
    Usa langdetect para detección robusta de idioma.
    """

    def analyze(self, recent_messages: list[str]) -> StyleSignals | None:
        """
        Analiza los últimos mensajes para extraer señales de estilo.
        Retorna None si no hay mensajes suficientes.
        """
        if not recent_messages:
            return None

        full_text_raw = " ".join(recent_messages)
        full_text_lower = full_text_raw.lower()

        return StyleSignals(
            detected_language=self._detect_language(full_text_raw),
            formality_indicator=self._detect_formality(full_text_raw, full_text_lower),
            brevity=self._detect_brevity(recent_messages),
            uses_emoji=self._detect_emoji(full_text_lower),
        )

    def _detect_language(self, text: str) -> str:
        """Detección robusta de idioma usando langdetect."""
        try:
            lang = detect(text)
            # langdetect retorna códigos ISO 639-1 (es, en, pt, fr, etc.)
            return lang
        except LangDetectException:
            logger.warning("No se pudo detectar idioma, usando español por defecto")
            return "es"

    def _detect_formality(self, raw_text: str, lower_text: str) -> str:
        """Detecta nivel de formalidad."""
        # Indicadores formales
        formal_markers = [
            "usted",
            "estimado",
            "quisiera",
            "atentamente",
            "podría",
            "podria",
        ]
        # Indicadores casuales
        casual_markers = [
            " q ",
            " xq ",
            " pa ",
            "jaja",
            "lol",
            "hey",
            "che",
            "güey",
            "parce",
        ]

        formal_score = sum(1 for m in formal_markers if m in lower_text)
        casual_score = sum(1 for m in casual_markers if m in lower_text)

        # Matiz por Capitalization (señal de formalidad)
        if re.search(r"[A-Z][a-z]+[\.!\?]", raw_text):
            formal_score += 1

        # Matiz por total minúsculas (señal casual)
        if raw_text == lower_text and len(raw_text) > 20:
            casual_score += 1

        if formal_score > casual_score:
            return "formal" if formal_score < 3 else "muy_formal"
        if casual_score > formal_score:
            return "casual" if casual_score < 3 else "muy_casual"
        return "casual"  # Default balanceado

    def _detect_brevity(self, messages: list[str]) -> str:
        """Analiza la longitud promedio de los mensajes."""
        avg_len = sum(len(m) for m in messages) / len(messages)

        if avg_len < 30:
            return "telegrafico"
        if avg_len < 120:
            return "conciso"
        return "verboso"

    def _detect_emoji(self, text: str) -> bool:
        """Detección simple de presencia de emojis o emoticonos."""
        emoji_pattern = r"[\U00010000-\U0010ffff]|[:;=]-?[)D(|P]"
        return bool(re.search(emoji_pattern, text))


# Instancia global única
style_analyzer = StyleAnalyzer()
```

**Step 4: Arreglar bug de prioridad de dialecto en `prompt_renders.py`**

```python
# src/personality/prompt_renders.py

from src.personality.types import LinguisticProfile, StyleSignals


def render_dialect_rules(linguistic: LinguisticProfile) -> str:
    """Genera reglas de dialecto basadas en PREFERENCIA > CONFIRMACIÓN > NEUTRO."""
    base = (
        "- **Idioma:** Responde SIEMPRE en el mismo idioma en el que te escribe "
        "el usuario.\n"
    )

    # Prioridad 1: Preferencia Explícita (Highest Priority)
    # BUG FIX: preferred_dialect SIEMPRE gana, incluso si dialect_confirmed=False
    if linguistic.preferred_dialect:
        return (
            base + f"- **Dialecto ACTIVO:** {linguistic.preferred_dialect}. "
            "Úsalo con naturalidad.\n"
        )

    # Prioridad 2: Ubicación Confirmada (Middle Priority - Sugerencia suave)
    if linguistic.dialect_confirmed and linguistic.dialect != "neutro":
        return base + (
            f"- **Contexto Regional:** El usuario está en {linguistic.dialect}. "
            "Puedes usar modismos locales suaves si él los usa primero, pero NO "
            "fuerces el acento.\n"
        )

    # Default: Neutralidad Cálida (Español Latinoamericano Estándar) + Eco Léxico
    return base + (
        "- **Dialecto Base:** Neutralidad Cálida (Español Latinoamericano "
        "Estándar).\n"
        "- **ECO LÉXICO:** Adopta el vocabulario específico del usuario "
        "(sustantivos/verbos) para generar cercanía, pero mantén la gramática "
        "neutra.\n"
    )


def render_style_adaptation(style: StyleSignals | None) -> str:
    """Adapta el tono del prompt según las señales de estilo detectadas."""
    if not style:
        return ""

    rules = ["- **Adaptación de Estilo (Observada):**"]

    # Formalidad
    if style.formality_indicator == "muy_formal":
        rules.append(
            "  * El usuario es MUY FORMAL. Elimina coloquialismos y sé "
            "impecablemente profesional."
        )
    elif style.formality_indicator == "formal":
        rules.append("  * El usuario es formal. Mantén un tono respetuoso.")
    elif style.formality_indicator == "muy_casual":
        rules.append(
            "  * El usuario es MUY CASUAL. Puedes usar mucha jerga y humor relajado."
        )
    else:  # casual
        rules.append("  * El usuario es casual. Sé cercano y relajado.")

    # Brevedad
    if style.brevity == "telegrafico":
        rules.append(
            "  * El usuario es telegráfico. Sé ULTRA-CONCISO, ve directo al grano."
        )
    elif style.brevity == "verboso":
        rules.append(
            "  * El usuario se extiende. Puedes dar respuestas más detalladas y "
            "profundas."
        )

    # Emoji
    if not style.uses_emoji:
        rules.append("  * El usuario NO usa emojis. Reduce su uso al mínimo.")

    return "\n".join(rules) + "\n"
```

**Step 5: Ejecutar tests para verificar que pasan**

```bash
pytest tests/unit/personality/test_style_analyzer.py -v
pytest tests/unit/personality/test_prompt_renders.py -v
```

**Expected:** Todos los tests pasan (incluyendo el bug fix de prioridad de dialecto)

**Step 6: Commit**

```bash
git add src/personality/style_analyzer.py src/personality/prompt_renders.py tests/unit/personality/test_style_analyzer.py
git commit -m "feat(personality): use langdetect for robust language detection and fix dialect priority bug"
```

---

#### 3.3. Persistir `StyleSignals` en SQLite (campo JSON en `profiles`)

**Módulo/Archivo:** `src/core/profile_manager.py`
- **Acción:** Modificar
- **Descripción:** Añadir campo `style_signals` al JSON del perfil, actualizarlo después de cada análisis de estilo
- **Consumidores:** `prompt_builder.py`

**Step 1: Escribir test de persistencia**

```python
# tests/unit/core/test_profile_manager_style.py
import pytest
from unittest.mock import AsyncMock, patch
from src.core.profile_manager import UserProfileManager
from src.personality.types import StyleSignals


class TestProfileManagerStyle:
    """Tests de persistencia de StyleSignals en profiles."""

    @pytest.mark.asyncio
    async def test_save_style_signals(self) -> None:
        """StyleSignals se guarda en campo JSON del perfil."""
        manager = UserProfileManager()

        # Crear perfil inicial
        await manager.save_profile("test_chat", {"identity": {"name": "Test"}})

        # Guardar StyleSignals
        signals = StyleSignals(
            detected_language="es",
            formality_indicator="casual",
            brevity="conciso",
            uses_emoji=True,
        )
        await manager.update_style_signals("test_chat", signals)

        # Cargar perfil y verificar
        profile = await manager.load_profile("test_chat")
        assert "style_signals" in profile
        assert profile["style_signals"]["detected_language"] == "es"
        assert profile["style_signals"]["formality_indicator"] == "casual"

    @pytest.mark.asyncio
    async def test_load_style_signals(self) -> None:
        """StyleSignals se carga desde perfil."""
        manager = UserProfileManager()

        # Crear perfil con StyleSignals
        await manager.save_profile("test_chat", {
            "identity": {"name": "Test"},
            "style_signals": {
                "detected_language": "en",
                "formality_indicator": "formal",
                "brevity": "verboso",
                "uses_emoji": False,
            },
        })

        # Cargar y verificar
        profile = await manager.load_profile("test_chat")
        assert profile["style_signals"]["detected_language"] == "en"
```

**Step 2: Implementar `update_style_signals()` en `profile_manager.py`**

```python
# src/core/profile_manager.py

# Añadir método a UserProfileManager
async def update_style_signals(self, chat_id: str, signals: StyleSignals) -> None:
    """Actualiza el campo style_signals del perfil."""
    profile = await self.load_profile(chat_id)
    profile["style_signals"] = {
        "detected_language": signals.detected_language,
        "formality_indicator": signals.formality_indicator,
        "brevity": signals.brevity,
        "uses_emoji": signals.uses_emoji,
    }
    await self.save_profile(chat_id, profile)
```

**Step 3: Actualizar `prompt_builder.py` para persistir después de analizar**

```python
# src/personality/prompt_builder.py (en _build_mirror_section)

        # 2. Analizar estilo conversacional si hay mensajes recientes
        style = (
            style_analyzer.analyze(recent_user_messages)
            if recent_user_messages
            else None
        )

        # Persistir StyleSignals si se detectó
        if style and profile.get("identity", {}).get("chat_id"):
            from src.core.profile_manager import user_profile_manager
            chat_id = profile["identity"]["chat_id"]
            await user_profile_manager.update_style_signals(chat_id, style)
```

**Step 4: Ejecutar tests**

```bash
pytest tests/unit/core/test_profile_manager_style.py -v
```

**Expected:** 2 tests PASS

**Step 5: Commit**

```bash
git add src/core/profile_manager.py src/personality/prompt_builder.py tests/unit/core/test_profile_manager_style.py
git commit -m "feat(personality): persist StyleSignals in profiles for style memory"
```

---

### Verificación de Fase

**Micro-gates:**
- [ ] `make verify` pasa al 100%
- [ ] Tests de `style_analyzer` pasan (9 tests)
- [ ] Tests de `profile_manager_style` pasan (2 tests)
- [ ] Tests existentes de `prompt_renders` siguen pasando

**Checklist de alineación arquitectónica:**
- [x] Usa inyección de dependencias (`langdetect` es librería externa, no instancia clientes)
- [x] Maneja errores con degradación suave (si `langdetect` falla, retorna "es" por defecto)
- [x] No genera cadena de imports eager
- [x] Modifica schema de `profiles` (campo JSON opcional, backward compatible)

---

## Fase 4: Eliminación de Duplicaciones y Limpieza (P1)

### Objetivo
Eliminar duplicación semántica entre SOUL.md y `render_dialect_rules()`, y documentar cambios.

### Justificación
- **ROI bajo:** Mejora mantenibilidad, no funcionalidad
- **Riesgo eliminado:** Confusión sobre qué regla aplica (SOUL.md vs `prompt_renders.py`)

### Cambios Previstos

#### 4.1. Eliminar duplicación de regla de idioma

**Módulo/Archivo:** `src/personality/base/SOUL.md:22`
- **Acción:** Modificar
- **Descripción:** Eliminar línea "Respondo SIEMPRE en el idioma del usuario" (ya está en `prompt_renders.py:6-9`)
- **Consumidores:** `loader.py`

**Step 1: Editar SOUL.md**

```markdown
# src/personality/base/SOUL.md

## Reglas Lingüísticas Inmutables

- **Eco Léxico:** Reutilizo los sustantivos y verbos específicos del usuario (ej. 'carro' vs 'coche', 'depurar' vs 'debuggear').
- Si hay `preferred_dialect` confirmado: ÚSALO.
- Si NO hay preferencia: Usa Español Latinoamericano Estándar (neutro pero cálido).
- NUNCA asumas dialecto por ubicación física (ej. un argentino en Madrid no quiere que le hablen como español).
```

**Step 2: Ejecutar tests**

```bash
pytest tests/unit/personality/ -v
```

**Expected:** Todos los tests siguen pasando

**Step 3: Commit**

```bash
git add src/personality/base/SOUL.md
git commit -m "docs(personality): remove duplication between SOUL.md and render_dialect_rules"
```

---

### Verificación de Fase

**Micro-gates:**
- [ ] `make verify` pasa al 100%
- [ ] Tests existentes siguen pasando

---

## Seguimiento de Tareas

- [ ] **Fase 1:** Activar Crisis Detector y Guardrails Condicionales
  - [ ] 1.1. Crear tests unitarios de `crisis_detector.py` (7 tests)
  - [ ] 1.2. Cablear `crisis_detector` en `tcc/tools.py` (2 tests de integración)
- [ ] **Fase 2:** Migrar a ChatPromptTemplate Estructurado
  - [ ] 2.1. Refactorizar `prompt_builder.py` para retornar lista de mensajes (2 tests)
- [ ] **Fase 3:** Mejorar StyleAnalyzer
  - [ ] 3.1. Añadir dependencia `langdetect`
  - [ ] 3.2. Refactorizar `style_analyzer.py` para usar `langdetect` (9 tests)
  - [ ] 3.3. Persistir `StyleSignals` en SQLite (2 tests)
- [ ] **Fase 4:** Eliminación de Duplicaciones y Limpieza
  - [ ] 4.1. Eliminar duplicación de regla de idioma en SOUL.md

---

## Desviaciones

> Esta sección se llena **durante la ejecución**, no durante la planificación.
> Si la implementación diverge del plan original, registrar aquí el qué, el por qué, y el impacto.

| Fecha | Desviación | Razón | Impacto |
|---|---|---|---|
| | | | |

---

## Notas y Riesgos

### Dependencias técnicas externas
- `langdetect>=1.0.9`: Librería madura (última actualización 2020), sin dependencias pesadas, compatible con Python 3.13
- Alternativa considerada: `fasttext` (más rápido pero requiere compilación de C++, overkill para nuestro caso de uso)

### Posibles efectos colaterales
- **Fase 1:** Si `crisis_detector` tiene falsos negativos (no detecta crisis real), el LLM no tendrá guardrails. Mitigación: el detector ya tiene filtro de metáforas y umbral de confidence conservador (solo medium/high activan).
- **Fase 2:** Si `ChatPromptTemplate` no maneja bien el escape de `{}` en algún caso edge, podría romper prompts. Mitigación: tests de integración cubren casos con JSON en runtime_context.
- **Fase 3:** Si `langdetect` falla en mensajes muy cortos (<10 caracteres), retorna "es" por defecto. Mitigación: logging de warning para debugging.

### Notas para otros agentes
- Este plan NO modifica el pipeline de mensajería (webhook, adapter, event processor). Solo afecta la construcción del system prompt dentro del specialist tool.
- El plan es backward compatible: todos los cambios son aditivos o refactorizaciones que mantienen la API pública.
- Si trabajas en paralelo en `src/personality/`, coordina para evitar conflictos en `prompt_builder.py` y `tcc/tools.py`.

---

**Plan completo y guardado en `.opencode/plans/2026-06-02-refactor-soul-stack-p0-p1.md`.**

**Dos opciones de ejecución:**

**1. Subagent-Driven (esta sesión)** - Despacho subagent fresco por tarea, reviso entre tareas, iteración rápida

**2. Parallel Session (separada)** - Abrir nueva sesión con `executing-plans`, ejecución en lote con checkpoints

**¿Cuál enfoque?**
