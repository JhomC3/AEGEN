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
2. Extraer entidades relevantes (emails, URLs, archivos, fechas)
3. Seleccionar el especialista más adecuado
4. Calcular tu nivel de confianza en la decisión

ESPECIALISTAS DISPONIBLES: {available_tools}

CRITERIOS DE ROUTING:
• vulnerability → El usuario expresa agotamiento profundo, tristeza clínica, disconformidad personal grave o crisis.
  **REGLA:** No confundas molestia por el trading ("no sale el trade") con vulnerabilidad vital. El trading es técnico/psicológico breve.
• chat → Saludos, preguntas triviales, confirmaciones, dudas técnicas de trading breves.
• topic_shift → El usuario indica que quiere dejar un tema.
• file_analysis → mensajes sobre documentos, PDFs.
• search → búsquedas de información.
• planning → planificación, cronogramas.
• chat → Conversación general que no encaja en lo anterior.

REGLA DE CONTINUIDAD (STICKINESS):
- El sistema te proporciona un `Especialista previo` en el contexto.
- Si el usuario está respondiendo a una pregunta, siguiendo un hilo del especialista previo (ej: respondiendo a un ejercicio de TCC) o si su mensaje es corto/ambiguo (ej: "ok", "sí", "¿por qué?"), DEBES MANTENER a ese mismo especialista.
- Solo cambia de especialista si el usuario solicita explícitamente otro tema o si hay un cambio drástico y claro de contexto.
- Tu prioridad es la fluidez de la conversación actual.

CONTEXTO CONVERSACIONAL: {context}

IMPORTANTE: Debes llamar OBLIGATORIAMENTE a la función route_user_message con:
- intent: una de las opciones válidas (chat, vulnerability, file_analysis, etc.)
- confidence: 0.0-1.0 basado en claridad del mensaje
- target_specialist: `cbt_specialist` para CUALQUIER señal de vulnerabilidad o negatividad personal. `chat_specialist` para lo demás.
- requires_tools: true si necesita herramientas específicas
- entities: lista de entidades encontradas (strings)
- subintent: sub-intención específica si aplica
- next_actions: acciones sugeridas post-routing (ej: "clear_context", "depth_empathy")
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
