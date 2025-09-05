# src/agents/orchestrator/routing/routing_prompts.py
"""
Prompt construction para routing decisions con structured output.

Centraliza definición de prompts para análisis NLP y routing,
facilitando ajustes sin modificar lógica de negocio.
"""

from langchain_core.prompts import ChatPromptTemplate


def build_routing_prompt() -> ChatPromptTemplate:
    """
    Construye prompt para análisis inteligente con function calling.
    
    Returns:
        ChatPromptTemplate: Prompt configurado para function calling (no structured output)
    """
    return ChatPromptTemplate.from_messages([
        ("system", """Analiza el mensaje del usuario y llama a la función route_user_message con los parámetros correctos.

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

IMPORTANTE: Debes llamar OBLIGATORIAMENTE a la función route_user_message con:
- intent: una de las opciones válidas (chat, file_analysis, search, help, task_execution, information_request, planning, document_creation)
- confidence: 0.0-1.0 basado en claridad del mensaje
- target_specialist: especialista más apropiado
- requires_tools: true si necesita herramientas específicas
- entities: lista de entidades encontradas (strings)
- subintent: sub-intención específica si aplica
- next_actions: acciones sugeridas post-routing"""),
        ("human", "{user_message}")
    ])


def build_fallback_context_message() -> str:
    """
    Mensaje de contexto para situaciones de fallback.
    
    Returns:
        str: Contexto informativo para fallback routing
    """
    return "Sin herramientas disponibles o contexto insuficiente para routing especializado"