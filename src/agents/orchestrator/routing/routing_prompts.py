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
            "Analiza el mensaje del usuario y llama a la función route_user_message con los parámetros correctos.\n"
            "\n"
            "Tu trabajo es:\n"
            "1. Identificar la intención principal del mensaje\n"
            "2. Extraer entidades relevantes (emails, URLs, archivos, fechas)\n"
            "3. Seleccionar el especialista más adecuado\n"
            "4. Calcular tu nivel de confianza en la decisión\n"
            "\n"
            "ESPECIALISTAS DISPONIBLES: {available_tools}\n"
            "\n"
            "CRITERIOS DE ROUTING:\n"
            "• vulnerability → El usuario expresa agotamiento profundo, tristeza clínica, "
            "disconformidad personal grave o crisis.\n"
            '  **REGLA:** No confundas molestia por el trading ("no sale el trade") con '
            "vulnerabilidad vital.\n"
            "  El trading es técnico/psicológico breve.\n"
            "• chat → Saludos, preguntas triviales, confirmaciones, dudas técnicas de trading breves.\n"
            "• topic_shift → El usuario indica que quiere dejar un tema.\n"
            "• file_analysis → mensajes sobre documentos, PDFs.\n"
            "• search → búsquedas de información.\n"
            "• planning → planificación, cronogramas.\n"
            "• chat → Conversación general que no encaja en lo anterior.\n"
            "\n"
            "REGLA DE CONTINUIDAD (STICKINESS):\n"
            "- El sistema te proporciona un `Especialista previo` en el contexto.\n"
            "- Si el usuario está respondiendo a una pregunta, siguiendo un hilo del especialista previo\n"
            "  (ej: respondiendo a un ejercicio de TCC) o si su mensaje es corto/ambiguo "
            "(ej: 'ok', 'sí', '¿por qué?'),\n"
            "  DEBES MANTENER a ese mismo especialista.\n"
            "- Solo cambia de especialista si el usuario solicita explícitamente otro tema o si hay "
            "un cambio drástico y claro de contexto.\n"
            "- Tu prioridad es la fluidez de la conversación actual.\n"
            "\n"
            "REGLA DE SESIÓN TERAPÉUTICA:\n"
            "- Si el `Especialista previo` es `cbt_specialist` y el usuario expresa frustración, queja\n"
            "  sobre el servicio, o respuestas cortas negativas (ej: 'no sirves', 'no me ayudas',\n"
            "  'esto no funciona'), esto es RESISTENCIA TERAPÉUTICA, no un cambio de tema.\n"
            "- En este caso, mantén `cbt_specialist` con intent `vulnerability` y añade la acción\n"
            "  'handle_resistance' en next_actions.\n"
            "- Solo cambia de CBT si el usuario dice explícitamente que quiere otro tema o usa un comando.\n"
            "\n"
            "CONTEXTO CONVERSACIONAL: {context}\n"
            "\n"
            "IMPORTANTE: Debes llamar OBLIGATORIAMENTE a la función route_user_message con:\n"
            "- intent: una de las opciones válidas (chat, vulnerability, file_analysis, etc.)\n"
            "- confidence: 0.0-1.0 basado en claridad del mensaje\n"
            "- target_specialist: `cbt_specialist` para CUALQUIER señal de vulnerabilidad o "
            "negatividad personal.\n"
            "  `chat_specialist` para lo demás.\n"
            "- requires_tools: true si necesita herramientas específicas\n"
            "- entities: lista de entidades encontradas (strings)\n"
            "- subintent: sub-intención específica si aplica\n"
            '- next_actions: acciones sugeridas post-routing (ej: "clear_context", "depth_empathy")\n',
        ),
        ("human", "{user_message}"),
    ])
