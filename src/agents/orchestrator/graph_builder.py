# src/agents/orchestrator/graph_builder.py
"""
OrchestratorGraphBuilder implementation.

Responsabilidad única: construcción del grafo LangGraph para orquestación.
Extraído del MasterOrchestrator monolítico para cumplir SRP.
"""

import logging
from typing import Any, cast

from langgraph.graph import StateGraph

from src.core.registry import SpecialistRegistry
from src.core.schemas import GraphStateV2

from .strategies import GraphBuilder

logger = logging.getLogger(__name__)


class OrchestratorGraphBuilder(GraphBuilder):
    """
    Construye el grafo de orquestación dinámicamente.

    Responsabilidades:
    - Construcción del StateGraph de LangGraph
    - Registro dinámico de nodos de especialistas
    - Configuración de edges y conditional routing
    - Chain architecture setup

    Dependencies inyectadas via constructor para testing.
    """

    def __init__(self, specialist_registry: SpecialistRegistry):
        """
        Initialize graph builder with injected dependencies.

        Args:
            specialist_registry: Registry de especialistas disponibles
        """
        self._specialist_registry = specialist_registry

    def build(self, routing_functions: dict[str, Any]) -> Any:
        """
        Construye dinámicamente el grafo de enrutamiento principal.

        Chain Architecture implementada:
        meta_router → specialist → chain_router → next_specialist → ... → END

        Args:
            routing_functions: Dict con funciones de routing a inyectar:
                - meta_router_fn: Función para meta routing
                - chain_router_fn: Función para chaining
                - initial_router_fn: Función de routing inicial
                - chain_router_decision_fn: Función de decisión chaining

        Returns:
            Compiled LangGraph StateGraph
        """
        logger.info("Construyendo grafo de orquestación dinámico...")

        graph_builder = StateGraph(GraphStateV2)

        # 1. Nodo de entrada: Meta-enrutador basado en capacidades
        graph_builder.add_node("meta_router", routing_functions["meta_router_fn"])

        # 2. Nodos de especialistas: un nodo por cada especialista registrado
        all_specialists = self._specialist_registry.get_all_specialists()

        for specialist in all_specialists:
            compiled_graph = cast(Any, specialist.graph)
            graph_builder.add_node(specialist.name, compiled_graph.ainvoke)

            # Chain architecture: Especialistas van a chain_router, no a END
            graph_builder.add_edge(specialist.name, "chain_router")

        logger.info(f"Registrados {len(all_specialists)} especialistas en el grafo")

        # 3. Chain router para determinar siguiente especialista
        graph_builder.add_node("chain_router", routing_functions["chain_router_fn"])

        # 4. Nodo de reflexión final (Life Reflection)
        from .nodes.reflection import life_reflection_node

        graph_builder.add_node("life_reflection", life_reflection_node.run)

        # 4. Configuración de routing points
        graph_builder.set_entry_point("meta_router")

        # 5. Conditional edges para routing dinámico
        graph_builder.add_conditional_edges(
            "meta_router",
            routing_functions["initial_router_fn"],
        )

        graph_builder.add_conditional_edges(
            "chain_router",
            routing_functions["chain_router_decision_fn"],
        )

        # 6. El nodo de reflexión es el punto final absoluto
        from langgraph.graph import END

        graph_builder.add_edge("life_reflection", END)

        compiled_graph = graph_builder.compile()
        logger.info("Grafo de orquestación compilado exitosamente")

        return compiled_graph
