# src/agents/specialists/cbt_specialist.py
"""
CBT (Cognitive Behavioral Therapy) Specialist para AEGEN.

Responsabilidad única: proporcionar apoyo terapéutico basado en técnicas
de Terapia Cognitivo Conductual usando knowledge base global especializada.

Capabilities:
- cbt_analysis: Análisis de patrones de pensamiento y emociones
- therapeutic_guidance: Guía terapéutica basada en CBT
- emotional_support: Apoyo emocional estructurado

Keywords activadores: ansiedad, depresión, terapia, emociones, estrés, 
                     pensamientos, sentimientos, miedos, autoestima
"""

import logging
from pathlib import Path
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, StateGraph

from src.core.dependencies import get_global_collection_manager
from src.core.engine import create_observable_config, llm
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2

logger = logging.getLogger(__name__)

# Cargar prompts especializados
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

def load_prompt(filename: str) -> str:
    """Carga prompt desde archivo de texto."""
    try:
        prompt_path = PROMPTS_DIR / filename
        return prompt_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"Error loading prompt {filename}: {e}")
        return f"Error loading prompt {filename}. Using fallback response."

CBT_THERAPEUTIC_TEMPLATE = load_prompt("cbt_therapeutic_response.txt")
CBT_ANALYSIS_TEMPLATE = load_prompt("cbt_analysis.txt")

# Keywords que activan el CBT specialist
CBT_KEYWORDS = {
    'spanish': [
        'ansiedad', 'ansioso', 'ansiosa', 'depresión', 'depresion',
        'deprimido', 'deprimida', 'terapia', 'emociones',
        'estrés', 'estres', 'pensamientos', 'sentimientos', 'miedos',
        'autoestima', 'tristeza', 'preocupación', 'preocupacion',
        'pánico', 'panico', 'angustia', 'ira', 'enojo', 'celos',
        'soledad', 'timidez', 'inseguridad', 'trauma', 'duelo',
        'relaciones', 'pareja', 'familia', 'trabajo', 'universidad'
    ],
    'english': [
        'anxiety', 'anxious', 'depression', 'depressed', 'therapy',
        'emotions', 'stress', 'thoughts', 'feelings', 'fears',
        'self-esteem', 'sadness', 'worry', 'panic', 'anger',
        'loneliness', 'trauma', 'grief'
    ]
}

@tool
async def cbt_therapeutic_guidance_tool(
    user_message: str,
    conversation_history: str = "",
    analysis_context: str | None = None
) -> str:
    """
    Herramienta principal de CBT que proporciona guía terapéutica
    basada en técnicas de Terapia Cognitivo Conductual.

    Args:
        user_message: Mensaje del usuario
        conversation_history: Historial conversacional
        analysis_context: Contexto de análisis previo opcional

    Returns:
        Respuesta terapéutica informada por knowledge base CBT
    """
    logger.info(f"CBT Therapeutic Tool procesando: '{user_message[:50]}...'")

    try:
        # Consultar knowledge base global para contexto CBT
        knowledge_context = await _get_cbt_knowledge_context(user_message)

        # Generar respuesta terapéutica
        therapeutic_response = await _generate_therapeutic_response(
            user_message, conversation_history, knowledge_context, analysis_context
        )

        logger.info(f"CBT therapeutic response generated: {len(therapeutic_response)} chars")
        return therapeutic_response

    except Exception as e:
        logger.error(f"Error in CBT therapeutic guidance: {e}", exc_info=True)
        return ("Entiendo que estás pasando por un momento difícil. "
               "Te recomiendo buscar apoyo de un profesional de salud mental "
               "que pueda brindarte la ayuda personalizada que necesitas.")


async def _get_cbt_knowledge_context(user_message: str, max_results: int = 3) -> str:
    """
    Consulta la knowledge base global para obtener contexto relevante de CBT.

    Args:
        user_message: Mensaje para buscar contexto relevante
        max_results: Máximo número de resultados a incluir

    Returns:
        Contexto de conocimiento CBT formateado
    """
    try:
        global_manager = get_global_collection_manager()

        # Consultar global_knowledge_base con query relacionado a CBT
        cbt_query = f"CBT therapy cognitive behavioral {user_message}"
        results = await global_manager.query_global_collection(
            collection_name="global_knowledge_base",
            query_text=cbt_query,
            user_id="cbt_specialist",
            n_results=max_results
        )

        if not results:
            logger.info("No CBT knowledge context found, using general guidance")
            return "Aplicar principios generales de CBT: identificar pensamientos automáticos, examinar evidencias, desarrollar pensamientos alternativos más balanceados."

        # Formatear contexto de conocimiento
        context_parts = []
        for i, result in enumerate(results[:max_results], 1):
            document = result.get('document', '')
            context_parts.append(f"Fuente {i}: {document[:200]}...")

        context = "\n".join(context_parts)
        logger.info(f"CBT knowledge context retrieved: {len(context)} chars from {len(results)} sources")
        return context

    except Exception as e:
        logger.error(f"Error retrieving CBT knowledge context: {e}", exc_info=True)
        return "Usar técnicas CBT fundamentales: reestructuración cognitiva, registro de pensamientos, técnicas de relajación."


async def _generate_therapeutic_response(
    user_message: str,
    conversation_history: str,
    knowledge_context: str,
    analysis_context: str | None = None
) -> str:
    """
    Genera respuesta terapéutica usando prompt especializado CBT.

    Args:
        user_message: Mensaje del usuario
        conversation_history: Historial conversacional
        knowledge_context: Contexto de knowledge base CBT
        analysis_context: Contexto de análisis opcional

    Returns:
        Respuesta terapéutica generada
    """
    therapeutic_prompt = ChatPromptTemplate.from_template(CBT_THERAPEUTIC_TEMPLATE)

    try:
        config = create_observable_config(call_type="cbt_therapeutic_response")
        chain = therapeutic_prompt | llm

        prompt_input = {
            "user_message": user_message,
            "knowledge_context": knowledge_context
        }

        # Añadir contexto de análisis si está disponible
        if analysis_context:
            prompt_input["analysis_context"] = analysis_context

        response = await chain.ainvoke(prompt_input, config=config)

        therapeutic_response = str(response.content).strip()

        # Añadir disclaimer si no está presente
        if "profesional" not in therapeutic_response.lower():
            therapeutic_response += "\n\n💡 Recordatorio: Esta guía complementa pero no reemplaza la terapia profesional. Si necesitas apoyo adicional, considera consultar con un psicólogo o terapeuta."

        return therapeutic_response

    except Exception as e:
        logger.error(f"Error generating therapeutic response: {e}", exc_info=True)
        return ("Comprendo que estás atravesando una situación desafiante. "
               "Es importante que sepas que tus sentimientos son válidos. "
               "Te animo a buscar apoyo profesional si sientes que lo necesitas.")


async def _cbt_node(state: GraphStateV2) -> dict[str, Any]:
    """
    Nodo principal del CBT Specialist que procesa el estado y genera respuesta terapéutica.

    Args:
        state: Estado del grafo con evento y contexto

    Returns:
        Estado actualizado con respuesta CBT
    """
    try:
        event_obj = state["event"]
        user_message = event_obj.content or ""
        session_id = state.get("session_id", "unknown-session")

        logger.info(f"[{session_id}] CBT Node procesando: '{user_message[:50]}...'")

        # Formatear historial conversacional
        conversation_history = _format_conversation_history(
            state.get("conversation_history", [])
        )

        # Generar respuesta terapéutica usando la herramienta
        therapeutic_response = await cbt_therapeutic_guidance_tool.ainvoke({
            "user_message": user_message,
            "conversation_history": conversation_history
        })

        # Actualizar payload con respuesta
        current_payload = state.get("payload", {})
        updated_payload = {
            **current_payload,
            "response": therapeutic_response,
            "specialist_metadata": {
                "specialist_type": "cbt_therapy",
                "session_id": session_id,
                "therapeutic_approach": "cognitive_behavioral_therapy"
            }
        }

        logger.info(f"[{session_id}] CBT therapeutic response generated successfully")

        return {
            "payload": updated_payload
        }

    except Exception as e:
        error_msg = f"Error in CBT specialist node: {e}"
        logger.error(error_msg, exc_info=True)

        return {
            "payload": state.get("payload", {}),
            "error_message": "Error procesando respuesta terapéutica. Por favor, considera buscar apoyo profesional."
        }


def _format_conversation_history(conversation_history: list[dict[str, Any]]) -> str:
    """
    Formatea historial conversacional para contexto terapéutico.

    Args:
        conversation_history: Lista de mensajes del historial

    Returns:
        Historial formateado como string
    """
    if not conversation_history:
        return "Sin historial previo."

    # Usar últimos 5 mensajes para contexto relevante
    recent_history = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history

    history_parts = []
    for msg in recent_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        formatted_role = "Usuario" if role == "user" else "Terapeuta"
        history_parts.append(f"{formatted_role}: {content}")

    return "\n".join(history_parts)


def _contains_cbt_keywords(text: str) -> bool:
    """
    Verifica si el texto contiene keywords relacionados con CBT.

    Args:
        text: Texto a analizar

    Returns:
        True si contiene keywords CBT
    """
    text_lower = text.lower()

    # Verificar keywords en español e inglés
    for lang_keywords in CBT_KEYWORDS.values():
        for keyword in lang_keywords:
            if keyword in text_lower:
                return True

    return False


class CBTSpecialist(SpecialistInterface):
    """
    Especialista en Terapia Cognitivo Conductual (CBT) para AEGEN.

    Proporciona apoyo terapéutico basado en técnicas CBT validadas,
    integrando knowledge base global especializada en terapia.

    Capabilities:
    - Análisis de patrones de pensamiento y emociones
    - Guía terapéutica estructurada basada en CBT  
    - Apoyo emocional empático y profesional
    - Técnicas de reestructuración cognitiva
    - Estrategias de manejo de ansiedad y depresión
    """

    def __init__(self):
        self._name = "cbt_specialist"
        self._graph = self._build_graph()
        self._tool: BaseTool = cbt_therapeutic_guidance_tool

        logger.info("✅ CBT Specialist initialized with therapeutic guidance capabilities")

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> Any:
        return self._graph

    @property
    def tool(self) -> BaseTool:
        return self._tool

    def get_capabilities(self) -> list[str]:
        """
        Retorna capacidades del CBT Specialist.

        Returns:
            Lista de capabilities que puede manejar
        """
        return [
            "cbt_analysis",           # Análisis CBT de pensamientos/emociones
            "therapeutic_guidance",   # Guía terapéutica estructurada
            "emotional_support",      # Apoyo emocional empático
            "anxiety_management",     # Manejo de ansiedad
            "depression_support",     # Apoyo para depresión
            "cognitive_restructuring", # Reestructuración cognitiva
            "mindfulness_techniques", # Técnicas mindfulness
            "behavioral_activation"   # Activación conductual
        ]

    def can_handle_message(self, message: str, context: dict[str, Any] | None = None) -> bool:
        """
        Determina si el CBT Specialist puede manejar un mensaje específico.

        Args:
            message: Mensaje del usuario
            context: Contexto adicional opcional

        Returns:
            True si puede manejar el mensaje
        """
        # Verificar keywords CBT en el mensaje
        if _contains_cbt_keywords(message):
            return True

        # Verificar contexto si está disponible
        if context and context.get("emotional_indicators", False):
            return True

        return False

    def _build_graph(self) -> Any:
        """
        Construye el grafo LangGraph para el CBT Specialist.

        Returns:
            Grafo compilado de LangGraph
        """
        graph_builder = StateGraph(GraphStateV2)
        graph_builder.add_node("cbt_therapy", _cbt_node)
        graph_builder.set_entry_point("cbt_therapy")
        graph_builder.add_edge("cbt_therapy", END)

        return graph_builder.compile()


# Registrar CBT Specialist en el registry
specialist_registry.register(CBTSpecialist())
logger.info("🧠 CBT Specialist registered successfully")
