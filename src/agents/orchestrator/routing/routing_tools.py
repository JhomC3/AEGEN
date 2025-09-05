# src/agents/orchestrator/routing/routing_tools.py
"""
Function calling tools para routing decisions.

Reemplaza structured output con function calling approach para 
eliminar bottleneck de performance (36+s → <2s).
"""

from langchain_core.tools import tool
from typing import Literal, List, Dict, Any, Optional


@tool
async def route_user_message(
    intent: Literal[
        "chat", 
        "file_analysis", 
        "search", 
        "help", 
        "task_execution", 
        "information_request", 
        "planning",
        "document_creation"
    ], 
    confidence: float,
    target_specialist: str,
    entities: List[str] = None,
    requires_tools: bool = False,
    subintent: Optional[str] = None,
    next_actions: List[str] = None
) -> Dict[str, Any]:
    """
    Fast routing decision using function calling instead of structured output.
    
    Esta función reemplaza llm.with_structured_output(RoutingDecision) 
    que causaba 36+ segundos de latencia con Gemini.
    
    Args:
        intent: Primary intent detected from user message
        confidence: Confidence level (0.0-1.0) in the classification  
        target_specialist: Target specialist for routing
        entities: List of entities extracted from message
        requires_tools: Whether specialized tools are required
        subintent: Specific sub-intention if applicable
        next_actions: Suggested actions after routing
        
    Returns:
        Dict containing routing decision data compatible with RoutingDecision
    """
    # Default values para optional parameters
    entities = entities or []
    next_actions = next_actions or []
    
    return {
        "intent": intent,
        "confidence": confidence,
        "target_specialist": target_specialist,
        "entities": entities,
        "requires_tools": requires_tools,
        "subintent": subintent,
        "next_actions": next_actions,
        "processing_metadata": {
            "method": "function_calling",
            "latency_optimized": True,
            "performance_fix": "ADR-0009"
        }
    }