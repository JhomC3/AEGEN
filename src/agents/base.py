from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver  # SqlliteSaver, PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


class BaseAgent:
    """
    Clase base para todos los agentes que utilizan langgraph.
    Encapsula la crecial del grafo, nodos y la logica de ejecucion.
    """

    def __init__(
        self, llm: BaseChatModel, tools: list[BaseTool], checkpointer: MemorySaver
    ):
        self.llm = llm.bind_tools(tools)
        self.tools = tools
        self.graph = self._build_graph(checkpointer)

    def _chatbot_node(self, state: AgentState):
        return {"messages": [self.llm.invoke(state["messages"])]}

    def _build_graph(self, checkpointer: MemorySaver):
        """Construye y compila el grafo de langgraph"""
        graph_builder = StateGraph(AgentState)

        tool_node = ToolNode(self.tools)

        graph_builder.add_node("chatbot", self._chatbot_node)
        graph_builder.add_node("tools", tool_node)

        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
            {"tools": "tools", END: END},  # ???
        )
        return graph_builder.compile(checkpointer=checkpointer)

    async def arun(self, user_input: str, thread_id: str):
        """Ejecuta el agente de forma asíncrona"""
        config = {"configurable": {"thread_id": thread_id}}
        final_state = await self.graph.ainvoke(
            {"messages": {"rol": "user", "content": user_input}}, config=config
        )

        return final_state["messages"][-1]
