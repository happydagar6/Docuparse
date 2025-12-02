# LangGraph multi-agent workflow
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from typing import TypedDict, Annotated, Dict, List, Any
from models.paper import PaperSummary
from dotenv import load_dotenv
import json


load_dotenv()
import os

llm = ChatOpenAI(
    model="grok-4-1-fast-reasoning",
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Safely merge dictionaries ensuring JSON serializable output"""
    result = {}
    # Merge a first
    for key, value in a.items():
        result[key] = ensure_json_serializable(value)
    # Merge b, overwriting any conflicts
    for key, value in b.items():
        result[key] = ensure_json_serializable(value)
    return result


def ensure_json_serializable(obj: Any) -> Any:
    """Ensure object is JSON serializable"""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, list):
        return [ensure_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: ensure_json_serializable(v) for k, v in obj.items()}
    else:
        # Convert any other type to string
        return str(obj)


class AgentState(TypedDict):
    text: str
    summary: Annotated[Dict[str, Any], merge_dicts]


# Accumulate
# Add more fileds as needed


def extract_agent(state: AgentState) -> AgentState:
    """Extract key points and citations from paper text"""
    try:
        # Safely chunk the text
        text_chunk = state.get('text', '')[:2000] if state.get('text') else ''
        prompt = f"""Extract key points and citations from this paper text: {text_chunk}

Please format your response using clear markdown:
- Use **bold** SPARINGLY - only for the most important terms and key concepts
- Use bullet points (-) for lists
- Use proper paragraph breaks
- Organize information clearly
- Keep most text at regular weight for readability

Extract the most important points from this text."""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # Ensure clean, serializable output
        extracted_content = response.content if hasattr(response, 'content') else str(response)
        
        result_summary = {
            "key_points": [extracted_content.strip()],
            "citations": [],
            "related_works": []
        }
        
        return {"summary": ensure_json_serializable(result_summary)}
    except Exception as e:
        print(f"Extract agent error: {e}")
        # Return safe fallback
        return {"summary": {"key_points": ["Extraction failed"], "citations": [], "related_works": []}}


def summarize_agent(state: AgentState) -> AgentState:
    """Summarize extracted key points"""
    try:
        # Safely get existing summary
        current_summary = state.get('summary', {})
        key_points = current_summary.get('key_points', [])
        
        if not key_points:
            return {"summary": current_summary}
            
        # Create summary prompt
        points_text = ' '.join(key_points) if isinstance(key_points, list) else str(key_points)
        prompt = f"""Provide a concise summary of these key points: {points_text[:1500]}

Please format your summary using clear markdown:
- Use **bold** SPARINGLY - only for the most important terms and key findings
- Use ## for section headings when appropriate
- Use bullet points (-) for key findings
- Write in clear, readable paragraphs
- Keep most text at regular weight for better readability

Create a well-structured summary that's easy to read and understand."""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        summary_content = response.content if hasattr(response, 'content') else str(response)
        
        # Update summary while preserving other fields
        updated_summary = {
            "key_points": [summary_content.strip()],
            "citations": current_summary.get('citations', []),
            "related_works": current_summary.get('related_works', [])
        }
        
        return {"summary": ensure_json_serializable(updated_summary)}
    except Exception as e:
        print(f"Summarize agent error: {e}")
        # Return current state if processing fails
        return {"summary": state.get('summary', {"key_points": [], "citations": [], "related_works": []})}


def link_agent(state: AgentState) -> AgentState:
    """Generate related works and topic links"""
    try:
        # Safely get text and existing summary
        text_chunk = state.get('text', '')[:1000] if state.get('text') else ''
        current_summary = state.get('summary', {})
        
        prompt = f"""Suggest related research topics and works based on: {text_chunk}

Please format your suggestions using clear markdown:
- Use **bold** SPARINGLY - only for the most important research areas
- Use bullet points (-) for each suggested topic or work
- Organize by relevance or theme
- Keep suggestions concise but informative
- Most text should be regular weight

Provide 3-5 most relevant research topics or works."""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # Process related works
        related_content = response.content if hasattr(response, 'content') else str(response)
        related_works = [work.strip() for work in related_content.split('\n') if work.strip()]
        
        # Build final summary
        final_summary = {
            "key_points": current_summary.get('key_points', []),
            "citations": current_summary.get('citations', []),
            "related_works": related_works[:8]  # Limit to 8 items
        }
        
        return {"summary": ensure_json_serializable(final_summary)}
    except Exception as e:
        print(f"Link agent error: {e}")
        # Return current state if processing fails
        current_summary = state.get('summary', {})
        return {"summary": {
            "key_points": current_summary.get('key_points', []),
            "citations": current_summary.get('citations', []),
            "related_works": current_summary.get('related_works', [])
        }}


# Build graph

graph = StateGraph(AgentState)
graph.add_node("extract", extract_agent)
graph.add_node("summarize", summarize_agent)
graph.add_node("link", link_agent)

graph.set_entry_point("extract")
graph.add_edge("extract", "summarize")
graph.add_edge("summarize", "link")
graph.add_edge("link", END)

workflow = graph.compile()  # Traced in LangSmith automatically
