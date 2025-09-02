# src/agents/orchestrator/routing/routing_prompts.py
"""
Prompt construction para routing decisions con structured output.

Centraliza definición de prompts para análisis NLP y routing,
facilitando ajustes sin modificar lógica de negocio.
"""

from langchain_core.prompts import ChatPromptTemplate


def build_routing_prompt() -> ChatPromptTemplate:
    """
    Construye prompt para análisis inteligente con structured output.
    
    Returns:
        ChatPromptTemplate: Prompt configurado para RoutingDecision output
    """
    return ChatPromptTemplate.from_messages([
        ("system", """Analiza el mensaje del usuario y genera una decisión de routing estructurada.

Tu trabajo es:
1. Identificar la intención principal del mensaje
2. Extraer entidades relevantes (emails, URLs, archivos, fechas)  
3. Seleccionar el especialista más adecuado
4. Calcular tu nivel de confianza en la decisión

ESPECIALISTAS DISPONIBLES: {available_tools}

CRITERIOS DE ROUTING:
• file_analysis → mensajes sobre documentos, PDFs, análisis de archivos
• search → búsquedas de información, investigación, "busca X"
• planning → planificación, cronogramas, organización de tareas
• chat → conversación general, saludos, clarificaciones simples

CONTEXTO CONVERSACIONAL: {context}

Responde usando el formato RoutingDecision con:
- intent: una de las opciones válidas
- confidence: 0.0-1.0 basado en claridad del mensaje
- target_specialist: especialista más apropiado
- requires_tools: true si necesita herramientas específicas
- entities: lista de entidades encontradas"""),
        ("human", "{user_message}")
    ])


def build_fallback_context_message() -> str:
    """
    Mensaje de contexto para situaciones de fallback.
    
    Returns:
        str: Contexto informativo para fallback routing
    """
    return "Sin herramientas disponibles o contexto insuficiente para routing especializado"