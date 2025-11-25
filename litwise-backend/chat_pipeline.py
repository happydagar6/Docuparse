import os
import json
import asyncio
from typing import Any, Dict, Optional, AsyncGenerator, List
from datetime import datetime

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document


# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

# LangSmith imports
from langsmith import traceable, Client

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

# Supabase imports
from workflow.db import supabase, qdrant
from dotenv import load_dotenv
load_dotenv()

# Import models
from models.chat import ChatMessage, ChatRequest, ChatResponse

class ChatState:
    def __init__(self):
        self.question: str = ""
        self.context: List[Dict] = []
        self.chat_history: List[Dict] = []
        self.memory_summary: str = ""
        self.response: str = ""
        self.sources: List[Dict] = []
        self.session_id: str = ""
        self.error: Optional[str] = None

class RAGChatPipeline:
    def __init__(self):
        # Initialize clients
        self.openai_llm = ChatOpenAI(
            model="gpt-4o-mini-2024-07-18",
            temperature=0.1,
            streaming=True
        )
        
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Use existing connections from workflow.db
        self.qdrant_client = qdrant
        self.supabase = supabase
        
        # LangSmith client
        self.langsmith_client = Client(
            api_key=os.getenv("LANGSMITH_API_KEY"),
            api_url=os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")
        )

    @traceable(name="retrieve_context")
    async def _retrieve_context(self, state: Dict) -> Dict:
        """Retrieve relevant context with dynamic scope and intelligent filtering"""
        try:
            paper_id = state.get("paper_id")
            question = state.get("question", "")
            
            print(f"Retrieving context for paper: {paper_id}, question: {question}")
            
            # Generate embedding for the question
            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query, 
                question
            )
            
            print(f"Generated embedding for question, dimension: {len(query_embedding)}")
            
            # Use larger search scope for better context coverage
            initial_limit = 15  # Increased from 5 to capture more relevant context
            
            # Retrieve more context initially
            search_result = await asyncio.to_thread(
                self.qdrant_client.query_points,
                collection_name="litwise_collection",
                query=query_embedding,
                limit=initial_limit,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",
                            match=MatchValue(value=paper_id)
                        )
                    ]
                )
            )
            
            print(f"Found {len(search_result.points)} initial search results")
            
            # Intelligent context selection with relevance filtering
            all_results = []
            for result in search_result.points:
                content = result.payload.get('content', '')
                relevance_score = float(result.score)
                
                # Only include results with reasonable relevance (>0.1)
                if relevance_score > 0.1 and content.strip():
                    all_results.append({
                        "content": content,
                        "metadata": result.payload,
                        "relevance_score": relevance_score
                    })
            
            # Dynamic context window management
            context = self._select_optimal_context(all_results, max_tokens=4000)
            
            # Prepare sources for frontend display (top 5 most relevant)
            sources = []
            for result in context[:5]:
                content = result["content"]
                page = result["metadata"].get('page', 1)
                
                sources.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "page": page,
                    "relevance_score": result["relevance_score"]
                })
            
            state["context"] = context
            state["sources"] = sources
            
            print(f"Selected {len(context)} optimal context items from {len(all_results)} candidates")
            
        except Exception as e:
            print(f"Context retrieval failed: {str(e)}")
            import traceback
            traceback.print_exc()
            state["error"] = f"Context retrieval failed: {str(e)}"
            
        return state
    
    def _select_optimal_context(self, results: List[Dict], max_tokens: int = 4000) -> List[Dict]:
        """Select optimal context based on relevance and token budget"""
        if not results:
            return []
        
        # Sort by relevance score (descending)
        sorted_results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)
        
        selected_context = []
        total_tokens = 0
        
        # Rough token estimation (4 chars ≈ 1 token)
        for result in sorted_results:
            content = result["content"]
            estimated_tokens = len(content) // 4
            
            # Include if we have budget and it's relevant
            if total_tokens + estimated_tokens < max_tokens:
                selected_context.append(result)
                total_tokens += estimated_tokens
            else:
                # Check if this chunk is significantly more relevant than the last included
                if (selected_context and 
                    result["relevance_score"] > selected_context[-1]["relevance_score"] * 1.5 and
                    total_tokens + estimated_tokens < max_tokens * 1.2):  # Allow 20% overflow for high relevance
                    
                    # Replace least relevant item if this one is much better
                    selected_context[-1] = result
                    total_tokens = total_tokens - len(selected_context[-1]["content"]) // 4 + estimated_tokens
                else:
                    break
        
        # Ensure we have at least some context even if relevance is low
        if not selected_context and sorted_results:
            selected_context = [sorted_results[0]]  # At least include the top result
        
        print(f"Context selection: {len(selected_context)} chunks, ~{total_tokens} tokens")
        return selected_context

    @traceable(name="load_memory")
    async def _load_memory(self, state: Dict) -> Dict:
        """Load conversation memory from database"""
        try:
            session_id = state.get("session_id")
            
            # Load memory from database
            result = self.supabase.table("chat_memory").select("*").eq(
                "session_id", session_id
            ).execute()
            
            if result.data:
                memory_data = result.data[0]["memory_data"]
                state["memory_summary"] = memory_data.get("summary", "")
                state["chat_history"] = memory_data.get("history", [])
            else:
                state["memory_summary"] = ""
                state["chat_history"] = []
                
        except Exception as e:
            state["error"] = f"Memory loading failed: {str(e)}"
            state["memory_summary"] = ""
            state["chat_history"] = []
            
        return state

    @traceable(name="generate_response")
    async def _generate_response(self, state: Dict) -> Dict:
        """Generate AI response with streaming"""
        try:
            # Prepare context
            context_text = "\n\n".join([
                f"Content: {item['content']}\nRelevance: {item['relevance_score']:.2f}"
                for item in state.get("context", [])
            ])
            
            # Prepare chat history
            history_text = ""
            if state.get("memory_summary"):
                history_text = f"Previous conversation summary: {state['memory_summary']}\n\n"
            
            # Recent messages
            recent_history = state.get("chat_history", [])[-10:]  # Last 10 messages
            for msg in recent_history:
                role = "Human" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an AI research assistant helping users understand and analyze research papers. 

Use the provided document context to answer questions accurately and comprehensively. 

Guidelines:
1. Base your answers primarily on the provided context
2. If information isn't in the context, clearly state this
3. Provide specific quotes when relevant
4. Maintain conversation context from previous messages
5. Be concise but thorough
6. Use academic tone appropriate for research discussions

Document Context:
{context}

Conversation History:
{history}"""),
                ("human", "{question}")
            ])
            
            # Format the prompt
            formatted_prompt = prompt.format_messages(
                context=context_text,
                history=history_text,
                question=state.get("question", "")
            )
            
            # Generate response (non-streaming for now, we'll handle streaming in the API)
            response = await self.openai_llm.ainvoke(formatted_prompt)
            state["response"] = response.content
            
        except Exception as e:
            state["error"] = f"Response generation failed: {str(e)}"
            state["response"] = "I apologize, but I encountered an error while generating a response."
            
        return state

    @traceable(name="save_memory")
    async def _save_memory_async(self, state: Dict) -> None:
        """Save conversation memory to database asynchronously without blocking"""
        try:
            session_id = state.get("session_id")
            question = state.get("question", "")
            response = state.get("full_response", state.get("response", ""))
            
            # Get current memory state
            chat_history = state.get("chat_history", [])
            memory_summary = state.get("memory_summary", "")
            
            # Add current exchange to history
            new_history = chat_history + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response}
            ]
            
            # Check if summarization is needed (but don't block for it)
            if len(new_history) > 20:
                # Schedule summarization as background task
                asyncio.create_task(self._background_summarize(session_id, new_history, memory_summary))
                # Keep only recent messages for immediate storage
                new_history = new_history[-10:]
            
            # Save current state immediately (non-blocking)
            memory_data = {
                "summary": memory_summary,
                "history": new_history
            }
            
            # Use asyncio.create_task to make this truly non-blocking
            asyncio.create_task(self._store_memory(session_id, memory_data))
            
        except Exception as e:
            print(f"Memory saving failed: {str(e)}")
            # Don't let memory errors break the chat flow
    
    async def _background_summarize(self, session_id: str, chat_history: List[Dict], current_summary: str):
        """Background task to summarize conversation without blocking main thread"""
        try:
            # Generate summary in background
            summary_prompt = f"""
            Previous summary: {current_summary}
            
            Recent conversation:
            {json.dumps(chat_history[-15:], indent=2)}
            
            Create a concise summary of the conversation focusing on key topics discussed and important information shared.
            Keep it under 200 words.
            """
            
            summary_response = await self.openai_llm.ainvoke([
                SystemMessage(content="Create a brief conversation summary."),
                HumanMessage(content=summary_prompt)
            ])
            
            new_summary = summary_response.content
            
            # Update with summarized memory
            memory_data = {
                "summary": new_summary,
                "history": chat_history[-5:]  # Keep only 5 most recent
            }
            
            await self._store_memory(session_id, memory_data)
            print(f"Background summarization completed for session: {session_id}")
            
        except Exception as e:
            print(f"Background summarization failed: {str(e)}")
    
    async def _store_memory(self, session_id: str, memory_data: Dict):
        """Helper to store memory data in database"""
        try:
            await asyncio.to_thread(
                lambda: self.supabase.table("chat_memory").upsert({
                    "session_id": session_id,
                    "memory_data": memory_data,
                    "updated_at": datetime.now().isoformat()
                }).execute()
            )
        except Exception as e:
            print(f"Memory storage failed: {str(e)}")

    async def chat_stream(
        self, 
        question: str, 
        session_id: str, 
        paper_id: str
    ) -> AsyncGenerator[Dict, None]:
        """Stream chat response with real-time updates"""
        try:
            print(f"Chat pipeline starting for question: {question}")
            
            # Initialize state
            state = {
                "question": question,
                "session_id": session_id,
                "paper_id": paper_id
            }
            
            # Send loading message
            yield {"type": "token", "content": "🔍 Loading conversation history..."}
            
            # Load memory
            state = await self._load_memory(state)
            
            # Send context retrieval message
            yield {"type": "token", "content": "\n📚 Searching relevant content..."}
            
            # Retrieve context
            state = await self._retrieve_context(state)
            if state.get("error"):
                yield {"type": "error", "error": state["error"]}
                return
            
            # Send sources if available
            if state.get("sources"):
                yield {"type": "sources", "sources": state["sources"]}
                
            yield {"type": "token", "content": "\n🤖 Generating response...\n\n"}
            
            # Generate streaming response
            async for chunk in self._stream_response(state):
                yield chunk
                
            # Save memory asynchronously (non-blocking)
            await self._save_memory_async(state)
            
            yield {"type": "complete", "content": ""}
            
        except Exception as e:
            print(f"Chat pipeline error: {str(e)}")
            import traceback
            traceback.print_exc()
            yield {"type": "error", "error": f"Chat pipeline failed: {str(e)}"}

    async def _stream_response(self, state: Dict) -> AsyncGenerator[Dict, None]:
        """Stream the LLM response token by token"""
        try:
            print("Starting LLM streaming response")
            
            # Prepare context (same as in generate_response)
            context_text = "\n\n".join([
                f"Content: {item['content']}\nRelevance: {item['relevance_score']:.2f}"
                for item in state.get("context", [])
            ])
            
            history_text = ""
            if state.get("memory_summary"):
                history_text = f"Previous conversation summary: {state['memory_summary']}\n\n"
            
            recent_history = state.get("chat_history", [])[-10:]
            for msg in recent_history:
                role = "Human" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an AI research assistant helping users understand and analyze research papers. 

Use the provided document context to answer questions accurately and comprehensively. 

Guidelines:
1. Base your answers primarily on the provided context
2. If information isn't in the context, clearly state this
3. Provide specific quotes when relevant
4. Maintain conversation context from previous messages
5. Be concise but thorough
6. Use academic tone appropriate for research discussions

Document Context:
{context}

Conversation History:
{history}"""),
                ("human", "{question}")
            ])
            
            formatted_prompt = prompt.format_messages(
                context=context_text,
                history=history_text,
                question=state.get("question", "")
            )
            
            # Stream the response
            full_response = ""
            async for chunk in self.openai_llm.astream(formatted_prompt):
                if chunk.content:
                    full_response += chunk.content
                    print(f"Streaming chunk: {chunk.content}")
                    yield {"type": "token", "content": chunk.content}
            
            # Save complete message to state for memory saving
            state["full_response"] = full_response
            
        except Exception as e:
            print(f"Streaming failed: {str(e)}")
            import traceback
            traceback.print_exc()
            yield {"type": "error", "error": f"Streaming failed: {str(e)}"}

# Global instance
rag_pipeline = RAGChatPipeline()