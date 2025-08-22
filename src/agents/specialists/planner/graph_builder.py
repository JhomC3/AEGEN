# src/agents/specialists/planner/graph_builder.py
"""
Graph construction para PlannerAgent.
Single responsibility: build and compile LangGraph StateGraph.
"""

from collections.abc import Callable
from typing import Any

from langgraph.graph import StateGraph

from src.core.schemas import GraphStateV2


class PlannerGraphBuilder:
    """
    Construye LangGraph StateGraph para PlannerAgent.
    Separación de concerns: graph structure vs business logic.
    """

    def __init__(self, planning_node_func: Callable):
        """
        Initialize builder with planning node function.

        Args:
            planning_node_func: Async function que implementa la lógica de planning
        """
        if not callable(planning_node_func):
            raise TypeError("planning_node_func must be callable")

        self._planning_node = planning_node_func

    def build(self) -> Any:
        """
        Construye y compila el StateGraph para el planner.

        Returns:
            Compiled LangGraph StateGraph
        """
        graph_builder = StateGraph(GraphStateV2)

        # Add planning node
        graph_builder.add_node("plan_and_respond", self._planning_node)

        # Set entry point
        graph_builder.set_entry_point("plan_and_respond")

        # CHAINING ARCHITECTURE: Remove direct END connection
        # MasterOrchestrator handles chaining decisions now
        # graph_builder.add_edge("plan_and_respond", END)  # REMOVED

        return graph_builder.compile()

    def build_with_routing(self, routing_function: Callable) -> Any:
        """
        Future: Build graph with conditional routing logic.
        Para Week 2 cuando implementemos routing a otros specialists.

        Args:
            routing_function: Function que decide próximo nodo basado en state

        Returns:
            Compiled StateGraph with routing logic
        """
        graph_builder = StateGraph(GraphStateV2)

        graph_builder.add_node("plan_and_respond", self._planning_node)
        graph_builder.set_entry_point("plan_and_respond")

        # Add conditional routing logic
        graph_builder.add_conditional_edges("plan_and_respond", routing_function)

        return graph_builder.compile()
