# src/agents/specialists/planner/__init__.py
"""
PlannerAgent module following Clean Architecture principles.

Exposes:
- PlannerAgent: Main agent class implementing SpecialistInterface
- Supporting utilities available for testing/extension

Architecture:
- agent.py: Main business logic (SpecialistInterface implementation)
- graph_builder.py: LangGraph construction (Factory pattern)
- prompt_manager.py: Prompt loading/management (Single responsibility)
- state_utils.py: Pure functions for state manipulation
- tool.py: Tool definition for registry exposure
"""

from .agent import PlannerAgent

# Main export for registry
__all__ = ["PlannerAgent"]

# Version info
__version__ = "1.0.0"
__description__ = "Deep Agents Planning Tool implementation with Clean Architecture"
