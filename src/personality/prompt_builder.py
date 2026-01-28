import logging
from datetime import datetime
from typing import Any, Optional

from src.personality.manager import personality_manager

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
        runtime_context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Compone el prompt final.
        """
        base = await personality_manager.get_base()
        overlay = await personality_manager.get_skill_overlay(skill_name)

        # 1. Capa de Identidad y Alma
        identity_section = self._build_identity_section(base.identity)
        soul_section = self._build_soul_section(base.soul)

        # 2. Capa de Adaptación al Usuario
        adaptation = profile.get("personality_adaptation", {})
        user_section = self._build_user_adaptation_section(profile, adaptation)

        # 3. Capa de Skill Overlay
        skill_section = self._build_skill_section(overlay) if overlay else ""

        # 4. Capa de Contexto Runtime
        runtime_section = self._build_runtime_section(runtime_context or {})

        # Composición Final
        prompt = f"""
{identity_section}

{soul_section}

{user_section}

{skill_section}

{runtime_section}

---
REGLA DE ORO: Mantén tu esencia MAGI (casual, directa, con opinión) incluso cuando apliques las instrucciones del skill activo.
"""
        return prompt.strip()

    def _build_identity_section(self, identity: dict[str, str]) -> str:
        items = "\n".join([f"- **{k.capitalize()}:** {v}" for k, v in identity.items()])
        return f"# IDENTIDAD BASE\n{items}"

    def _build_soul_section(self, soul: str) -> str:
        return f"# TU ALMA Y FILOSOFÍA\n{soul}"

    def _build_user_adaptation_section(
        self, profile: dict[str, Any], adaptation: dict[str, Any]
    ) -> str:
        user_name = profile.get("identity", {}).get("name", "Usuario")
        style = adaptation.get("preferred_style", "casual")

        section = f"""# ADAPTACIÓN AL USUARIO: {user_name}
- **Estilo Preferido:** {style}
- **Nivel de Comunicación:** {adaptation.get("communication_level", "intermediate")}
- **Tolerancia al Humor:** {adaptation.get("humor_tolerance", 0.7)}
- **Nivel de Formalidad:** {adaptation.get("formality_level", 0.3)}
"""
        if adaptation.get("learned_preferences"):
            prefs = "\n".join([f"  - {p}" for p in adaptation["learned_preferences"]])
            section += f"- **Preferencias Aprendidas:**\n{prefs}"

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

    def _build_runtime_section(self, context: dict[str, Any]) -> str:
        now = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")
        section = f"# CONTEXTO RUNTIME\n- **Fecha/Hora:** {now}\n"
        if context.get("channel"):
            section += f"- **Canal:** {context['channel']}\n"

        # Integrar Memoria de Largo Plazo si viene en el contexto
        if context.get("history_summary"):
            section += (
                f"\n## Memoria de Largo Plazo (Resumen)\n{context['history_summary']}\n"
            )

        if context.get("knowledge_context"):
            section += (
                f"\n## Conocimiento Relevante (RAG)\n{context['knowledge_context']}\n"
            )

        return section


# Instancia global
system_prompt_builder = SystemPromptBuilder()
