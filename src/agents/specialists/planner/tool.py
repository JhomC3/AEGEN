# src/agents/specialists/planner/tool.py
"""
Tool definition para PlannerAgent.
Single responsibility: define la herramienta que expone PlannerAgent al registry.
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def planner_tool(context: str) -> str:
    """
    Herramienta de planificación y coordinación para Deep Agents workflows.

    Esta herramienta se usa para análisis de contexto y planificación de próximas
    acciones en workflows multi-step complejos.

    Args:
        context: Contexto actual que necesita análisis y planificación

    Returns:
        String indicating planning action initiated
    """
    logger.info(f"PlannerTool: Iniciando análisis de contexto: {context[:50]}...")
    return f"Planificación iniciada para contexto: {context[:50]}..."
