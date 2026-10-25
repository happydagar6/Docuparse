"""
=============================================================================
Litwise RAG Generator (`services/rag/generator.py`)
=============================================================================
This module handles the final Generation and Streaming phase of the RAG pipeline:
1. Retrieves top-ranked chunks using the HybridRetriever (Step 1.3).
2. Formats a grounded, anti-hallucination academic prompt with exact page markers.
3. Invokes OpenAI's `gpt-6-luna` with real-time streaming enabled (`stream=True`).
4. Yields Server-Sent Events (SSE) formatted chunks (`data: {...}\n\n`) for the Next.js frontend:
   - Token chunks: `{"type": "token", "content": "..."}`
   - Source citations: `{"type": "sources", "sources": [...]}`
   - Complete signal: `{"type": "complete"}`
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
    streaming LLM completion with gpt-6-luna, and SSE formatting.
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
        query: str,
        paper_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5
    ) -> AsyncGenerator[str, None]:
        """
        Main streaming generator:
        1. Retrieves relevant passages via HybridRetriever.
        2. Compiles grounded prompt.
        3. Streams tokens from gpt-6-luna using Server-Sent Events (SSE).
        4. Yields structured sources metadata upon completion.
        """
        try:
            logger.info(f"🚀 Starting RAG chat stream for query: '{query}' (paper_id={paper_id})")

            # 1. Retrieve relevant chunks using Hybrid Search (BM25 + Vectors + Re-ranking)
            retrieved_chunks = await self.retriever.retrieve(
                query=query,
                paper_id=paper_id,
                top_k=top_k
            )

            # 2. Format the retrieved context passages
            context_block = self._build_context_block(retrieved_chunks)

            # 3. Build messages array for OpenAI
            messages = self._format_messages(
                query=query,
                context_block=context_block,
                chat_history=chat_history
            )

            # 4. Invoke OpenAI streaming completion with gpt-6-luna
            response_stream = cast(
                AsyncStream[ChatCompletionChunk],
                await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=True,
                    reasoning_effort="medium"
                )
            )

            # 5. Stream tokens word-by-word as they arrive
            async for chunk in response_stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        token_payload = json.dumps({
                            "type": "token",
                            "content": delta.content
                        })
                        yield f"data: {token_payload}\n\n"

            # 6. Prepare and yield verified source citations for the frontend
            sources_list = []
            for chunk in retrieved_chunks:
                sources_list.append({
                    "page_number": chunk.get("page_number", 1),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "score": chunk.get("score", 0.0),
                    "content": chunk.get("content", "")[:300]  # First 300 chars for preview
                })

            sources_payload = json.dumps({
                "type": "sources",
                "sources": sources_list
            })
            yield f"data: {sources_payload}\n\n"

            # 7. Signal completion to the frontend reader
            complete_payload = json.dumps({"type": "complete"})
            yield f"data: {complete_payload}\n\n"

            logger.info(f"✅ RAG stream completed successfully for query: '{query}'")

        except Exception as e:
            logger.error(f"❌ Error during RAG streaming: {e}")
            error_payload = json.dumps({
                "type": "error",
                "error": str(e)
            })
            yield f"data: {error_payload}\n\n"


# Singleton instance ready for application-wide use
rag_generator = ResponseGenerator(model_name="gpt-6-luna")
