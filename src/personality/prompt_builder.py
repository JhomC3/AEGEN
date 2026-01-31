import logging
from datetime import datetime
from typing import Any

from zoneinfo import ZoneInfo

from src.core.profiling_manager import profiling_manager
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
        runtime_context: dict[str, Any] | None = None,
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
        localization = profile.get("localization", {})
        user_section = await self._build_user_adaptation_section(
            profile, adaptation, localization
        )

        # 3. Capa de Skill Overlay
        skill_section = self._build_skill_section(overlay) if overlay else ""

        # 4. Capa de Contexto Runtime
        runtime_section = self._build_runtime_section(
            runtime_context or {}, localization
        )

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

    async def _build_user_adaptation_section(
        self,
        profile: dict[str, Any],
        adaptation: dict[str, Any],
        localization: dict[str, Any] | None = None,
    ) -> str:
        user_name = profile.get("identity", {}).get("name", "Usuario")
        style = adaptation.get("preferred_style", "casual")

        section = f"""# ADAPTACIÓN AL USUARIO: {user_name}
- **Estilo Preferido:** {style}
- **Nivel de Comunicación:** {adaptation.get("communication_level", "intermediate")}
- **Tolerancia al Humor:** {adaptation.get("humor_tolerance", 0.7)}
- **Nivel de Formalidad:** {adaptation.get("formality_level", 0.3)}
"""
        if localization:
            dialect = localization.get("dialect", "neutro")
            tz = localization.get("timezone", "UTC")
            section += f"- **Localización:** {dialect} (Zona Horaria: {tz})\n"

            if localization.get("dialect_hint"):
                section += f"- **Matiz Regional:** {localization['dialect_hint']}\n"

            # Reglas de jerga dinámicas y mimetismo
            section += "\n## REGLAS LINGÜÍSTICAS Y MIMETISMO\n"

            # 1. Baseline por dialecto
            if dialect == "argentino":
                section += "- **Base:** Usa español rioplatense (voseo: vos, che, tenés). Tono cercano y directo.\n"
            elif dialect == "español":
                section += "- **Base:** Usa español de España (tuteo, vosotros, modismos ibéricos).\n"
            elif dialect == "mexicano":
                section += "- **Base:** Usa español mexicano (tuteo, tono cálido y respetuoso).\n"
            elif dialect == "colombiano":
                section += "- **Base:** Usa español de Colombia (tuteo estándar, tono muy cálido y amable).\n"
            else:
                section += "- **Base:** Usa español neutro internacional. Vocabulario estándar comprensible en LatAm.\n"

            # 2. Instrucción de Espejo (Mirroring)
            section += """- **Mirroring (~30%):** Observa el vocabulario del usuario.
  * Si el usuario usa jerga local (ej: 'parce', 'pibe', 'güey'), siéntete libre de mimetizarla suavemente para crear afinidad.
  * Si el usuario es formal, mantén tu profesionalismo.
  * NUNCA copies exactamente; mantén tu esencia MAGI (casual, directa, con opinión).\n"""

            # 3. Profiling Hint (Dinámico)
            hint = await profiling_manager.get_profiling_hint(profile)
            if hint:
                section += f"- **Profiling:** {hint}\n"

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

    def _build_runtime_section(
        self, context: dict[str, Any], localization: dict[str, Any] | None = None
    ) -> str:
        # Obtener timezone del usuario
        user_tz = localization.get("timezone", "UTC") if localization else "UTC"

        try:
            user_time = datetime.now(ZoneInfo(user_tz))
            time_str = user_time.strftime("%A, %d de %B de %Y, %H:%M")
            section = f"# CONTEXTO RUNTIME\n- **Hora Local del Usuario:** {time_str} ({user_tz})\n"
        except Exception:
            # Fallback a UTC si falla zoneinfo
            now_utc = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")
            section = f"# CONTEXTO RUNTIME\n- **Fecha/Hora (UTC):** {now_utc}\n"

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
