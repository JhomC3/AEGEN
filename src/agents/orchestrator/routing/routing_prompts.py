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
        (
            "system",
            """Analiza el mensaje del usuario y llama a la función route_user_message con los parámetros correctos.

Tu trabajo es:
1. Identificar la intención principal del mensaje
2. Extraer entidades relevantes
3. Seleccionar el especialista (MAGI es principalmente un SISTEMA DE SOPORTE TCC)
4. Calcular tu nivel de confianza en la decisión

ESPECIALISTAS DISPONIBLES: {available_tools}

CRITERIOS DE ROUTING (SOPORTE TCC PRIORITARIO):
• cbt_specialist → PARA TODO: saludos, charla general, desahogos, ansiedad, problemas personales, o simplemente conversar. MAGI es un amigo experto en TCC por defecto.
• chat_specialist → SOLO para preguntas extremadamente técnicas sobre el sistema o meta-comentarios sobre la IA que no requieran apoyo. (Casi nunca se usa).
• file_analysis → mensajes sobre documentos, PDFs.
• search → búsquedas de información externa.
• planning → planificación y organización de tareas.

**REGLA DE ORO:** MAGI no es un asistente genérico, es un soporte psicológico TCC. Ante la duda, envía SIEMPRE a `cbt_specialist`.

CONTEXTO CONVERSACIONAL: {context}

IMPORTANTE: Debes llamar OBLIGATORIAMENTE a la función route_user_message con:
- intent: una de las opciones válidas (chat, vulnerability, file_analysis, etc.)
- confidence: 0.0-1.0 basado en claridad del mensaje
- target_specialist: `cbt_specialist` para el 99% de las interacciones interpersonales.
- requires_tools: true si necesita herramientas específicas
- entities: lista de entidades encontradas
- subintent: sub-intención específica
- next_actions: acciones sugeridas post-routing
""",
        ),
        ("human", "{user_message}"),
    ])


def build_fallback_context_message() -> str:
    """
    Mensaje de contexto para situaciones de fallback.

    Returns:
        str: Contexto informativo para fallback routing
    """
    return "Sin herramientas disponibles o contexto insuficiente para routing especializado"
