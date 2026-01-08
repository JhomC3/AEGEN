import json
from typing import Annotated

from langchain.chat_models import init_chat_model

# from langgraph.prebuilt import create_react_agent
from langchain_core.messages import ToolMessage
from langchain_tavily import TavilySearch
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class State(TypedDict):
    messages: Annotated[list, add_messages]


class BasicToolNode:  # prebuilt tool node
    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("no message found in inputs")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}


class ResearchAgent:
    def __init__(self, llm):
        self.llm = llm
        self.tool = TavilySearch(max_results=5, topic="general")
        self.tools = [self.tool]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.tool_node = BasicToolNode(tools=[self.tool])
        self.graph = self._build_graph()

    def _chatbot(self, state: State):
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def _route_tools(self, state: State):  # prebuilt tools_condition
        messages = state.get("messages", [])
        if not messages:
            raise ValueError(f"NO messages found in input state to tool_edge: {state}")

        ai_message = messages[-1]

        # Check if the last message is an AIMessage and has tool calls
        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            return "tools"
        return END

    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("tools", self.tool_node)
        graph_builder.add_node("chatbot", self._chatbot)
        graph_builder.add_conditional_edges(
            "chatbot", self._route_tools, {"tools": "tools", END: END}
        )
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")
        return graph_builder.compile()

    def run(self, user_input: str):
        for event in self.graph.stream({
            "messages": [{"role": "user", "content": user_input}]
        }):
            for value in event.values():
                if "messages" in value and value["messages"]:
                    print("Assistant:", value["messages"][-1].pretty_print())


def main():
    import os

    from core.config import BaseAppSettings

    settings = BaseAppSettings()
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY.get_secret_value()
    os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY.get_secret_value()

    model_id = f"google_genai:{settings.DEFAULT_LLM_MODEL}"
    llm = init_chat_model(model_id)

    agent = ResearchAgent(llm)

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
