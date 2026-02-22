import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import aiofiles
import yaml

from src.core.dependencies import get_sqlite_store
from src.core.profiling_manager import profiling_manager
from src.personality.manager import personality_manager
from src.personality.prompt_renders import (
    render_dialect_rules,
    render_style_adaptation,
)
from src.personality.style_analyzer import style_analyzer
from src.personality.types import LinguisticProfile

logger = logging.getLogger(__name__)


class SystemPromptBuilder:
    """
    Construye el system prompt de MAGI de forma modular y adaptativa.
    Implementa aislamiento de personalidad para tareas técnicas.
    """

    _gold_standards_cache: dict[str, str] = {}

    async def _get_gold_standards(self, category: str = "chat") -> str:
        """Carga y formatea los ejemplos de Few-Shot filtrados por categoría."""
        if category in self._gold_standards_cache:
            return self._gold_standards_cache[category]

        path = Path("src/personality/base/gold_standards.yaml")
        if not path.exists():
            return ""

        try:
            async with aiofiles.open(path, encoding="utf-8") as f:
                content = await f.read()
            data = yaml.safe_load(content)

            anchors = data.get("conversational_anchors", [])
            if not anchors:
                return ""

            examples = ["## Interacciones Gold Standard (Ejemplos a imitar)\n"]
            found = False
            for anchor in anchors:
                if anchor.get("category") == category or category == "all":
                    found = True
                    example = (
                        f"**Situación:** {anchor.get('situation')}\n"
                        f'**Usuario:** "{anchor.get("user_message")}"\n'
                        f'**Respuesta Ideal (MAGI):** "{anchor.get("ideal_response")}"\n'
                        f"*(Nota: {anchor.get('explanation')})*\n"
                    )
                    examples.append(example)

            if not found:
                return ""

            result = "\n".join(examples)
            self._gold_standards_cache[category] = result
            return result
        except Exception as e:
            logger.error(f"Error loading gold standards for {category}: {e}")
            return ""

    async def build_technical(self, task_name: str, instructions: str) -> str:
        """
        Construye un prompt puramente técnico sin personalidad.
        Ideal para Milestone Extraction, Reflection, etc.
        """
        return f"""
# MODO OPERACIONAL: {task_name.upper()}
Componente técnico especializado en datos estructurados.

## INSTRUCCIONES CRÍTICAS
- Tu única misión es: {instructions}
- NO uses lenguaje natural, NO saludes, NO des consejos.
- NO inyectes personalidad, humor ni empatía.
- Tu salida DEBE ser estrictamente JSON válido según el esquema solicitado.
- Si no puedes realizar la tarea, devuelve el objeto JSON vacío correspondiente.

# CONTEXTO DE EJECUCIÓN
- Fecha/Hora Actual: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
""".strip()

    async def build(
        self,
        chat_id: str,
        profile: dict[str, Any],
        skill_name: str = "chat",
        runtime_context: dict[str, Any] | None = None,
        recent_user_messages: list[str] | None = None,
        include_personality: bool = True,
    ) -> str:
        """
        Compone el prompt final ensamblando las capas del Soul Stack.
        """
        if not include_personality:
            return await self.build_technical(
                task_name=skill_name,
                instructions=runtime_context.get(
                    "technical_instructions", "Procesar datos."
                )
                if runtime_context
                else "Procesar datos.",
            )

        base = await personality_manager.get_base()
        overlay = await personality_manager.get_skill_overlay(skill_name)

        # 1. Capas 1 y 2: Identidad y Alma (Inmutables)
        identity_section = self._build_identity_section(base.identity)
        soul_section = self._build_soul_section(base.soul)

        # 2. Capa 3: ESPEJO (The Mirror) - Adaptación al Usuario
        user_section = await self._build_mirror_section(profile, recent_user_messages)

        # 3. Capa 4: Skill Overlay (Dinámica por modo)
        skill_section = self._build_skill_section(overlay) if overlay else ""

        # Inyectar Gold Standards SELECTIVOS
        gold_standards = await self._get_gold_standards(category=skill_name)
        if gold_standards:
            skill_section += f"\n{gold_standards}\n"

        # 4. Capa 5: Contexto Runtime (Temporal, Episódico, RAG)
        runtime_section = await self._build_runtime_section(
            runtime_context or {}, profile.get("localization", {}), chat_id=chat_id
        )

        # Composición Final (Ensamblaje Raw)
        prompt = f"""
{identity_section}

{soul_section}

{user_section}

{skill_section}

{runtime_section}

# MANDATO FINAL DE IDENTIDAD
[SISTEMA: EXTREMA PRIORIDAD]
- Usa tuteo neutro.
- PROHIBIDO el voseo ("vos", "tenés") y regionalismos de España ("tío", "vale").
- Tu prioridad es ser útil y empático sin perder la coherencia lingüística.
"""
        # ESCAPADO DE SEGURIDAD PARA LANGCHAIN
        return prompt.strip().replace("{", "{{").replace("}", "}}")

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

        linguistic = LinguisticProfile(
            dialect=localization.get("dialect", "neutro"),
            dialect_hint=localization.get("dialect_hint"),
            preferred_dialect=adaptation.get("preferred_dialect"),
            dialect_confirmed=localization.get("confirmed_by_user", False),
            formality_level=adaptation.get("formality_level", 0.3),
            humor_tolerance=adaptation.get("humor_tolerance", 0.7),
            preferred_style=adaptation.get("preferred_style", "casual"),
        )

        style = (
            style_analyzer.analyze(recent_user_messages)
            if recent_user_messages
            else None
        )

        section = f"# ESPEJO: CÓMO ME ADAPTO A TI ({user_name})\n"
        section += render_dialect_rules(linguistic)
        section += render_style_adaptation(style)

        hint = await profiling_manager.get_profiling_hint(profile)
        if hint:
            section += f"- **Profiling:** {hint}\n"

        if learned := adaptation.get("learned_preferences"):
            prefs = "\n".join([f"  - {p}" for p in learned])
            section += f"- **Preferencias Aprendidas:**\n{prefs}\n"

        return section

    def _build_skill_section(self, overlay: Any) -> str:
        section = f"# MODO ACTIVO: {overlay.name.upper()}\n"
        if overlay.tone_modifiers:
            section += f"## Modificadores de Tono\n{overlay.tone_modifiers}\n"
        if overlay.instructions:
            section += f"## Instrucciones Específicas\n{overlay.instructions}\n"
        if overlay.anti_patterns:
            section += f"## Anti-Patterns del Skill\n{overlay.anti_patterns}\n"
        return section

    async def _build_runtime_section(
        self,
        context: dict[str, Any],
        localization: dict[str, Any] | None = None,
        chat_id: str | None = None,
    ) -> str:
        user_tz = localization.get("timezone", "UTC") if localization else "UTC"

        try:
            user_time = datetime.now(ZoneInfo(user_tz))
            time_str = user_time.strftime("%A, %d de %B de %Y, %H:%M")
            section = (
                f"# CONTEXTO RUNTIME\n- **Hora Local del Usuario:** "
                f"{time_str} ({user_tz})\n"
            )
        except Exception:
            now_utc = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")
            section = f"# CONTEXTO RUNTIME\n- **Fecha/Hora (UTC):** {now_utc}\n"

        if context.get("channel"):
            section += f"- **Canal:** {context['channel']}\n"

        if summary := context.get("history_summary"):
            section += f"\n## Memoria de Largo Plazo (Resumen)\n{summary}\n"

        if rag := context.get("knowledge_context"):
            section += f"\n## Conocimiento Relevante (RAG)\n{rag}\n"

        if kb := context.get("structured_knowledge"):
            section += f"\n## Bóveda de Conocimiento\n{kb}\n"

        if chat_id:
            try:
                store = get_sqlite_store()
                milestones = await store.state_repo.get_recent_milestones(
                    chat_id, limit=3
                )
                if milestones:
                    section += "\n## Hitos Recientes del Usuario\n"
                    for m in milestones:
                        action = m.get("action")
                        status = m.get("status")
                        emotion = m.get("emotion")
                        desc = (
                            f" ({m.get('description')})" if m.get("description") else ""
                        )
                        section += (
                            f"- **{action}**: {status}. Emoción: {emotion}{desc}\n"
                        )
                    section += "\n*(Úsalo para dar seguimiento al usuario)*\n"
            except Exception as e:
                logger.debug(f"Error fetching milestones: {e}")

        if pending := context.get("pending_intents"):
            intents_str = "\n".join([f"- {intent}" for intent in pending])
            section += "\n## Intenciones Proactivas Pendientes\n"
            section += "Tú (MAGI) tenías programado hablar de estos temas:\n"
            section += f"{intents_str}\n\n"
            section += "**INSTRUCCIÓN:** Si el tema permite, sácalos sutilmente.\n"

        if context and context.get("is_proactive"):
            section += "\n## INSTRUCCIÓN DEL SISTEMA (MENSAJE PROACTIVO)\n"
            section += "El usuario no ha hablado. Inicia tú la charla.\n"

        return section


# Instancia global
system_prompt_builder = SystemPromptBuilder()
