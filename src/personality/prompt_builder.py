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
from src.personality.types import LinguisticProfile

logger = logging.getLogger(__name__)


class SystemPromptBuilder:
    """
    Construye el system prompt de MAGI de forma modular y adaptativa.
    """

    async def build(
        self,
        chat_id: str,
        profile: dict[str, Any],
        skill_name: str = "chat",
        runtime_context: dict[str, Any] | None = None,
        recent_user_messages: list[str] | None = None,
    ) -> str:
        """
        Compone el prompt final ensamblando las 5 capas del Soul Stack.
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

        # Composición Final (Ensamblaje Raw)
        prompt = f"""
{identity_section}

{soul_section}

{user_section}

{skill_section}

{runtime_section}
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

    def _build_skill_section(self, overlay: Any) -> str:
        section = f"# MODO ACTIVO: {overlay.name.upper()}\n"
        if overlay.tone_modifiers:
            section += f"## Modificadores de Tono\n{overlay.tone_modifiers}\n"
        if overlay.instructions:
            section += f"## Instrucciones Específicas\n{overlay.instructions}\n"
        if overlay.anti_patterns:
            section += f"## Anti-Patterns del Skill\n{overlay.anti_patterns}\n"
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
