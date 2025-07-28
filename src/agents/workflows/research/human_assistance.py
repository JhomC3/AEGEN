from typing import Annotated

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt
from typing_extensions import TypedDict


class State(TypedDict):
    messages: Annotated[list, add_messages]


class HumanAssistanceAgent:
    def __init__(self, llm):
        self.llm = llm
        self.tool = TavilySearch(max_results=5, topic="general")
        self.tools = [self.tool, self._human_assistance]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.tool_node = ToolNode(self.tools)
        self.memory = MemorySaver()
        self.graph = self.build_graph()

    def _chatbot(self, state: State):
        message = self.llm_with_tools.invoke(state["messages"])
        assert len(message.tool_calls) <= 1
        return {"messages": [message]}

    @tool
    def _human_assistance(self, query: str) -> str:
        """Request assistance from a human user.

        This tool allows the agent to ask for human input when it needs clarification,
        additional information, or guidance that cannot be obtained through other means.

        Args:
            query: The question or request to present to the human user

        Returns:
            str: The human's response to the query
        """
        human_response: str = interrupt({"query": query})
        if not human_response or not isinstance(human_response, str):
            return ""
        return human_response

    def build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", self._chatbot)
        graph_builder.add_node("tools", self.tool_node)
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        return graph_builder.compile(checkpointer=self.memory)

    def run(self, user_input: str):
        config = {"configurable": {"thread_id": "1"}}
        for event in self.graph.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode="values",
        ):
            if "messages" in event and event["messages"]:
                print("Assistant:", event["messages"][-1].pretty_print())


def main():
    import os

    from core.config import BaseAppSettings

    settings = BaseAppSettings()
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY.get_secret_value()
    os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY.get_secret_value()

    llm = init_chat_model("google_genai:gemini-2.5-flash")
    agent = HumanAssistanceAgent(llm)

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            agent.run(user_input)
        except Exception as e:
            print(f"\nAn error occurred: {e}\n")
            break


if __name__ == "__main__":
    main()
