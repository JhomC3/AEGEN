# src/agents/orchestrator/routing/routing_analyzer.py
"""
Core LLM interaction para routing decisions.

Orquesta análisis LLM con structured output y coordina
post-processing usando componentes especializados.
"""

import logging
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from src.agents.orchestrator.specialist_cache import SpecialistCache
from src.core.engine import llm
from src.core.routing_models import RoutingDecision, IntentType
from src.core.schemas import GraphStateV2
from .routing_utils import extract_context_from_state
from .routing_patterns import PatternExtractor, IntentValidator, SpecialistMapper

logger = logging.getLogger(__name__)


class RoutingAnalyzer:
    """
    Orquestador de análisis LLM para routing decisions.
    
    Coordina structured output LLM con componentes especializados
    para análisis robusto y post-processing inteligente.
    """
    
    def __init__(self, routing_prompt: ChatPromptTemplate):
        """
        Inicializa analizador con componentes especializados.
        
        Args:
            routing_prompt: Prompt template configurado para structured output
        """
        self._chain = routing_prompt | llm.with_structured_output(RoutingDecision)
        self._pattern_extractor = PatternExtractor()
        self._intent_validator = IntentValidator()
        self._specialist_mapper = SpecialistMapper()
    
    async def analyze(self, message: str, state: GraphStateV2, cache: SpecialistCache) -> RoutingDecision:
        """
        Analiza mensaje y genera decisión de routing estructurada.
        
        Args:
            message: Mensaje del usuario a analizar
            state: Estado del grafo con contexto conversacional
            cache: Cache de especialistas disponibles
            
        Returns:
            RoutingDecision: Decisión estructurada con intent, confianza y entities
            
        Raises:
            Exception: Si falla análisis LLM o post-processing
        """
        available_tools = list(cache.get_tool_to_specialist_map().keys())
        context = extract_context_from_state(state)
        
        try:
            # Single LLM call con structured output
            decision = await self._chain.ainvoke({
                "user_message": message,
                "available_tools": available_tools,
                "context": self._format_context_for_llm(context)
            })
            
            # Post-processing y validación
            enhanced_decision = self._enhance_decision(decision, message, cache)
            
            logger.info(f"Análisis completado: {enhanced_decision.intent.value} → "
                       f"{enhanced_decision.target_specialist} "
                       f"(confianza: {enhanced_decision.confidence:.2f})")
            
            return enhanced_decision
            
        except ValidationError as e:
            logger.error(f"Error en validación structured output: {e}")
            return self._create_fallback_decision(message)
        except Exception as e:
            logger.error(f"Error en análisis LLM: {e}")
            return self._create_fallback_decision(message)
    
    def _enhance_decision(self, decision: RoutingDecision, message: str, cache: SpecialistCache) -> RoutingDecision:
        """
        Mejora decisión LLM usando componentes especializados.
        
        Args:
            decision: Decisión base del LLM
            message: Mensaje original para análisis complementario
            cache: Cache para mapeo de especialistas
            
        Returns:
            RoutingDecision: Decisión mejorada con validation y mapping
        """
        # Extraer entidades adicionales con pattern extractor
        pattern_entities = self._pattern_extractor.extract_entities_from_text(message)
        decision.entities.extend(pattern_entities)
        
        # Ajustar confianza si hay evidencia clara del intent
        if self._intent_validator.has_clear_intent_evidence(message, decision.intent):
            decision.confidence = min(decision.confidence + 0.15, 1.0)
        
        # Mapear a especialista disponible real
        decision.target_specialist = self._specialist_mapper.map_intent_to_specialist(
            decision.intent, cache
        )
        
        # Determinar requirement de tools
        decision.requires_tools = decision.intent != IntentType.CHAT
        
        return decision
    
    def _format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """
        Formatea contexto para inclusión en prompt LLM.
        
        Args:
            context: Diccionario con información contextual
            
        Returns:
            str: Contexto formateado para prompt
        """
        if not context:
            return "Sin contexto previo"
        
        parts = []
        
        if context.get("user_id"):
            parts.append(f"Usuario: {context['user_id']}")
        
        if context.get("history_length", 0) > 0:
            parts.append(f"Historial: {context['history_length']} mensajes")
        
        return " | ".join(parts) if parts else "Sesión nueva"
    
    def _create_fallback_decision(self, message: str) -> RoutingDecision:
        """
        Crea decisión fallback segura cuando falla análisis LLM.
        
        Args:
            message: Mensaje original para metadata básica
            
        Returns:
            RoutingDecision: Decisión fallback para chat specialist
        """
        return RoutingDecision(
            intent=IntentType.CHAT,
            confidence=0.5,  # Baja confianza indica fallback
            target_specialist="chat_specialist",
            requires_tools=False,
            entities=[],
            processing_metadata={
                "fallback_reason": "LLM analysis failed",
                "message_length": len(message)
            }
        )