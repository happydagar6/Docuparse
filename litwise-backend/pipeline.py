# LangGraph multi-agent workflow
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from typing import TypedDict, Annotated
from models import PaperSummary
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def merge_dicts(a, b):
    return {**a, **b
            }
class AgentState(TypedDict):
    text: str
    summary: Annotated[PaperSummary, merge_dicts]


# Accumulate
# Add more fileds as needed


def extract_agent(state: AgentState) -> AgentState:
    prompt = f"Extract key points and citations from this paper text: {state['text'][:2000]}"  # Chunk if long
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"summary": {"key_points": [response.content], "citations": []}}


def summarize_agent(state: AgentState) -> AgentState:
    prompt = f"Summarize the key points: {state['summary']['key_points']}"
    response = llm.invoke([HumanMessage(content=prompt)])
    state["summary"]["key_points"] = [response.content]  # Override or append
    return {
        "summary": {
            "key_points": state["summary"]["key_points"],
            "citations": state["summary"]["citations"],
        }
    }


def link_agent(state: AgentState) -> AgentState:
    prompt = f"Link topics and suggest related works from: {state['text'][:1000]}"
    response = llm.invoke([HumanMessage(content=prompt)])
    state["summary"]["related_works"] = response.content.split("\n")
    return {
        "summary": {
            "key_points": state["summary"]["key_points"],
            "citations": state["summary"]["citations"],
            "related_works": state["summary"]["related_works"],
        }
    }


# Build graph

graph = StateGraph(AgentState)
graph.add_node("extract", extract_agent)
graph.add_node("summarize", summarize_agent)
graph.add_node("link", link_agent)

graph.set_entry_point("extract")
graph.add_edge("extract", "summarize")
graph.add_edge("summarize", "link")
graph.add_edge("link", END)

workflow = graph.compile() # Traced in LangSmith automatically