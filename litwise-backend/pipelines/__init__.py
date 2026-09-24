# pipelines/__init__.py
"""
Pipelines Package for Litwise Backend
Provides:
- rag_pipeline: RAG chat streaming pipeline
- graph_app: LangGraph multi-agent paper summarizer
- get_async_pipeline: Non-blocking ThreadPool executor wrapper for LangGraph
"""

from .chat_pipeline import rag_pipeline, RAGChatPipeline
from .pipeline import workflow as graph_app
from .async_pipeline import get_async_pipeline, AsyncPipelineWrapper

__all__ = [
    'rag_pipeline',
    'RAGChatPipeline',
    'graph_app',
    'get_async_pipeline',
    'AsyncPipelineWrapper',
]
