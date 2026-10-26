# pipelines/__init__.py
"""
Pipelines Package for Litwise Backend
Provides:
- graph_app: LangGraph multi-agent paper summarizer
- get_async_pipeline: Non-blocking ThreadPool executor wrapper for LangGraph
"""

from .pipeline import workflow as graph_app
from .async_pipeline import get_async_pipeline, AsyncPipelineWrapper

__all__ = [
    'graph_app',
    'get_async_pipeline',
    'AsyncPipelineWrapper',
]
