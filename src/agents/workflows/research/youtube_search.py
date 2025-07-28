import os
from typing import Annotated

from agents.config import AgentConfig
from core.config import settings
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver  # sqliteSaver PostgresSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from tools.youtube.youtube_tools import youtube_search_tool
from typing_extensions import TypedDict


class State(TypedDict):
    messages: Annotated[list, add_messages]


class YoutubeSearchAgent:
    def __init__(self, config: RunnableConfig):
        self.configuration = AgentConfig.from_runnable_config(config)
        self.llm = init_chat_model(self.configuration.search_model)
        self.tools = [youtube_search_tool]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.tool_node = ToolNode(self.tools)
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _chatbot(self, state: State):
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("tools", self.tool_node)
        graph_builder.add_node("chatbot", self._chatbot)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        return graph_builder.compile(checkpointer=self.memory)

    def run(self, user_input: str, thread_id: str = "default_thread"):
        config = {"configurable": {"thread_id": thread_id}}
        events = self.graph.stream(
            {"messages": [{"role": "user", "content": user_input}]}, config=config
        )
        for event in events:
            if "chatbot" in event:
                final_message = event["chatbot"]["messages"][-1]
                if final_message.content:
                    print("\n--- Respuesta del Agente ---")
                    final_message.pretty_print()
                    print("--------------------------\n")


def main():
    # Configuración inicial de claves y modelo
    google_api_key = settings.GOOGLE_API_KEY.get_secret_value()
    os.environ["GOOGLE_API_KEY"] = google_api_key

    # Inicialización del LLM y el Agente
    config = {"configurable": {"search_model": "google_genai:gemini-2.5-flash"}}
    agent = YoutubeSearchAgent(config=config)

    print("Asistente de Búsqueda de YouTube iniciado. Escribe 'q' para salir.")
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["q", "quit", "exit"]:
                print("Adiós.")
                break
            agent.run(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nAdiós.")
            break
        except Exception as e:
            print(f"\nOcurrió un error: {e}\n")


if __name__ == "__main__":
    main()
