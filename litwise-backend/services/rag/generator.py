"""
=============================================================================
Litwise RAG Generator (`services/rag/generator.py`)
=============================================================================
This module handles the final Generation and Streaming phase of the RAG pipeline:
1. Retrieves top-ranked chunks using the HybridRetriever (Step 1.3).
2. Formats a grounded, anti-hallucination academic prompt with exact page markers.
3. Invokes OpenAI's `gpt-6-luna` with real-time streaming enabled (`stream=True`).
4. Yields pure Python dictionaries for the FastAPI route:
   - Token chunks: `{"type": "token", "content": "..."}`
   - Source citations: `{"type": "sources", "sources": [...]}`
   - Complete signal: `{"type": "complete", "content": ""}`
"""

import os
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional, cast
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam
from dotenv import load_dotenv

from services.rag.retriever import hybrid_retriever

load_dotenv()

logger = logging.getLogger(__name__)

# Standard System Prompt for Academic Grounding
SYSTEM_PROMPT = """You are Litwise, an expert AI research assistant designed to analyze scientific and academic documents.

Your goal is to answer the user's questions with high factual accuracy, rigor, and clarity based strictly on the provided document context.

CORE RULES:
1. GROUNDING: Answer ONLY using the document passages provided below. Never make up facts or extrapolate beyond what the text explicitly states.
2. CITATIONS: Always cite the source page for every factual claim, number, methodology, or finding using brackets, like [Page X] (e.g., "The model achieved 94.6% accuracy on GLUE [Page 2].").
3. UNKNOWN INFORMATION: If the answer cannot be found in the provided context, state clearly: "Based on the provided document, this information is not mentioned." Do not attempt to guess.
4. STYLE: Use clear, concise academic language. Format responses with markdown bolding, bullet points, and clean structure.
"""


class ResponseGenerator:
    """
    RAG Response Generator responsible for prompt compilation,
    streaming LLM completion with gpt-6-luna, and dictionary chunk yielding.
    """

    def __init__(self, model_name: str = "gpt-6-luna", retriever=hybrid_retriever):
        self.model_name = model_name
        self.retriever = retriever
        # Asynchronous OpenAI client for non-blocking token streaming
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY is not set in environment!")
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info(f"✅ ResponseGenerator initialized with model '{self.model_name}'")

    def _build_context_block(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved chunks into a numbered, structured context block
        with clear page tags for the LLM to cite.
        """
        if not retrieved_chunks:
            return "No relevant passages found in the document."

        formatted_passages = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            page_num = chunk.get("page_number", chunk.get("metadata", {}).get("page_number", 1))
            content = chunk.get("content", "").strip()
            passage_text = f"--- [Passage {i} | Page {page_num}] ---\n{content}"
            formatted_passages.append(passage_text)

        return "\n\n".join(formatted_passages)

    def _format_messages(
        self,
        query: str,
        context_block: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[ChatCompletionMessageParam]:
        """
        Assembles the full OpenAI messages payload:
        1. System message with grounding instructions.
        2. Recent conversation history (if provided).
        3. Current user question accompanied by the retrieved document context.
        """
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Append recent conversation turns (limit to last 6 for context efficiency)
        if chat_history:
            for msg in chat_history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    messages.append({"role": "assistant", "content": content})

        # Inject the retrieved document context alongside the user's question
        user_prompt = (
            f"DOCUMENT CONTEXT:\n{context_block}\n\n"
            f"USER QUESTION: {query}\n\n"
            f"Please answer the question based strictly on the context above, citing page numbers as [Page X]."
        )
        messages.append({"role": "user", "content": user_prompt})

        return messages

    async def chat_stream(
        self,
        question: Optional[str] = None,
        query: Optional[str] = None,
        paper_id: Optional[str] = None,
        session_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main streaming generator:
        1. Resolves query from either `question` or `query` parameter.
        2. Automatically loads multi-turn history from Supabase if session_id is provided.
        3. Retrieves relevant passages via HybridRetriever (Step 1.3).
        4. Streams pure Python dictionaries (tokens, sources, complete) for the FastAPI route.
        """
        user_query = (question or query or "").strip()
        if not user_query:
            logger.warning("Empty query received in chat_stream")
            return

        try:
            logger.info(f"🚀 Starting RAG chat stream for query: '{user_query}' (paper_id={paper_id}, session_id={session_id})")

            # 1. Multi-turn memory: load last 6 messages from Supabase if session_id provided and chat_history empty
            if session_id and not chat_history:
                try:
                    from workflow.db import supabase
                    history_res = supabase.table("chat_messages")\
                        .select("role, content")\
                        .eq("session_id", session_id)\
                        .order("created_at", desc=False)\
                        .limit(6)\
                        .execute()
                    
                    raw_messages = cast(List[Dict[str, Any]], history_res.data or [])
                    chat_history = [
                        {"role": str(msg.get("role")), "content": str(msg.get("content"))}
                        for msg in raw_messages
                        if msg.get("role") in ["user", "assistant"] and msg.get("content")
                    ]
                except Exception as history_err:
                    logger.warning(f"Could not load conversation history for session {session_id}: {history_err}")
                    chat_history = []

            # 2. Retrieve relevant chunks using Hybrid Search (BM25 + Vectors + Re-ranking)
            retrieved_chunks = await self.retriever.retrieve(
                query=user_query,
                paper_id=paper_id,
                top_k=top_k
            )

            # 3. Format the retrieved context passages
            context_block = self._build_context_block(retrieved_chunks)

            # 4. Build messages array for OpenAI
            messages = self._format_messages(
                query=user_query,
                context_block=context_block,
                chat_history=chat_history
            )

            # 5. Invoke OpenAI streaming completion with gpt-6-luna
            response_stream = cast(
                AsyncStream[ChatCompletionChunk],
                await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=True,
                    reasoning_effort="medium",
                )
            )

            # 6. Stream tokens word-by-word as pure dictionaries
            async for chunk in response_stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield {
                            "type": "token",
                            "content": delta.content
                        }

            # 7. Prepare and yield verified source citations for the frontend
            sources_list = []
            for chunk in retrieved_chunks:
                sources_list.append({
                    "page_number": chunk.get("page_number", 1),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "score": chunk.get("score", 0.0),
                    "content": chunk.get("content", "")[:300]  # First 300 chars for preview
                })

            yield {
                "type": "sources",
                "sources": sources_list
            }

            # 8. Signal completion to the FastAPI route
            yield {
                "type": "complete",
                "content": ""
            }

            logger.info(f"✅ RAG stream completed successfully for query: '{user_query}'")

        except Exception as e:
            logger.error(f"❌ Error during RAG streaming: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }


# Singleton instance ready for application-wide use
rag_generator = ResponseGenerator(model_name="gpt-6-luna")
