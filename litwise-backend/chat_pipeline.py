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
            model="grok-4-1-fast-reasoning",
            api_key=os.getenv("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
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
            
            # Import enhanced search system
            from workflow.enhanced_search import enhanced_search
            
            # Use hybrid search for better results
            try:
                enhanced_documents = await enhanced_search.hybrid_search(
                    qdrant_client=self.qdrant_client,
                    embeddings_model=self.embeddings,
                    paper_id=paper_id,
                    query=question,
                    top_k=35  # Get top 35 most relevant results
                )
                
                if enhanced_documents:
                    print(f"✅ Enhanced hybrid search found {len(enhanced_documents)} relevant results")
                    
                    # Filter out low-relevance results
                    high_relevance_docs = [doc for doc in enhanced_documents if doc['relevance_score'] > 0.3]
                    
                    if not high_relevance_docs:
                        print("⚠️ No high-relevance results found, using best available")
                        high_relevance_docs = enhanced_documents[:3]  # Use top 3 as fallback
                    
                    # Convert to expected format
                    context = []
                    sources = []
                    
                    for doc in high_relevance_docs:
                        context.append({
                            "content": doc['content'],
                            "metadata": doc.get('metadata', {}),
                            "relevance_score": doc['relevance_score']
                        })
                        
                        # Prepare sources for frontend (top 6)
                        if len(sources) < 6:
                            content = doc['content']
                            page = doc.get('page', 1)
                            
                            sources.append({
                                "content": content[:200] + "..." if len(content) > 200 else content,
                                "page": page,
                                "relevance_score": doc['relevance_score']
                            })
                    
                    state["context"] = context
                    state["sources"] = sources
                    return state
                    
            except Exception as e:
                print(f"Enhanced search failed, falling back to basic vector search: {e}")
            
            # Generate embedding for the question
            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query, 
                question
            )
            
            print(f"Generated embedding for question, dimension: {len(query_embedding)}")
            
            # Use smaller search scope for faster retrieval
            initial_limit = 8  # Reduced from 15 to 8 for faster processing
            
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
            
            # Check if no embeddings exist for this paper
            if len(search_result.points) == 0:
                print(f"No embeddings found for paper {paper_id} - paper may not be processed yet")
                state["context"] = []
                state["sources"] = []
                state["no_embeddings"] = True
                return state
            
            # Intelligent context selection with higher relevance filtering
            all_results = []
            for result in search_result.points:
                content = result.payload.get('content', '')
                relevance_score = float(result.score)
                
                # Only include results with reasonable relevance (reduced threshold for speed)
                if relevance_score > 0.2 and content.strip():  # Reduced from 0.3 to 0.2
                    all_results.append({
                        "content": content,
                        "metadata": result.payload,
                        "relevance_score": relevance_score
                    })
            
            # Dynamic context window management with confidence check
            context = self._select_optimal_context(all_results, max_tokens=2500)  # Reduced from 4000
            
            # Check if we have high-quality context
            if not context or (context and max(item["relevance_score"] for item in context) < 0.5):
                print(f"Warning: Low confidence context (best score: {max([item['relevance_score'] for item in context], default=0):.2f})")
                # Still proceed but the prompt will handle low-confidence gracefully
            
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
    
    def _select_optimal_context(self, results: List[Dict], max_tokens: int = 2500) -> List[Dict]:
        """Select optimal context based on relevance and token budget - optimized for speed"""
        if not results:
            return []
        
        # Sort by relevance score (descending) - limit to top 8 for speed
        sorted_results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)[:8]
        
        selected_context = []
        total_tokens = 0
        
        # Simplified token estimation (6 chars ≈ 1 token for faster calculation)
        for result in sorted_results:
            content = result["content"]
            estimated_tokens = len(content) // 6  # Faster estimation
            
            # Include if we have budget
            if total_tokens + estimated_tokens < max_tokens:
                selected_context.append(result)
                total_tokens += estimated_tokens
            else:
                break  # Stop when we hit the limit for speed
        
        # Ensure we have at least one context item
        if not selected_context and sorted_results:
            selected_context = [sorted_results[0]]
        
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
            # Handle case where paper hasn't been processed yet
            if state.get("no_embeddings", False):
                state["response"] = """I notice this paper hasn't been processed yet, so I don't have access to its content for detailed analysis. 

To chat about this paper, you'll need to:
1. Go to the processing section 
2. Click "Process with AI" to generate the enhanced content
3. Return here once processing is complete

The processing adds AI-powered summaries and enables detailed Q&A about the paper's content."""
                return state
            
            # Prepare context with explicit page information
            context_text = ""
            if state.get("context", []):
                context_text = "\n\n".join([
                    f"[Page {item['metadata'].get('page', 'unknown')}] {item['content']}\n(Relevance Score: {item['relevance_score']:.2f})"
                    for item in state.get("context", [])
                ])
            else:
                context_text = "No relevant context found in this document."
            
            # Prepare chat history
            history_text = ""
            if state.get("memory_summary"):
                history_text = f"Previous conversation summary: {state['memory_summary']}\n\n"
            
            # Recent messages
            recent_history = state.get("chat_history", [])[-10:]  # Last 10 messages
            for msg in recent_history:
                role = "Human" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            # Check if this is a greeting or casual interaction
            question_lower = state.get("question", "").lower().strip()
            greeting_patterns = [
                'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
                'how are you', 'what\'s up', 'how do you do', 'greetings',
                'thanks', 'thank you', 'bye', 'goodbye', 'see you'
            ]
            
            is_greeting = any(pattern in question_lower for pattern in greeting_patterns)
            is_short_query = len(state.get("question", "").strip()) < 10
            
            # Create different prompts for greetings vs actual questions
            if is_greeting or is_short_query:
                # Friendly greeting response
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are a helpful AI research assistant for analyzing documents. 

Respond to the user's greeting in a friendly, professional way and offer to help with questions about the uploaded document. 
Keep your response conversational and welcoming. Mention that you can help analyze, summarize, or answer questions about the document content.

Example responses:
- "Hello! I'm here to help you analyze and understand your research document. What would you like to know about it?"
- "Hi there! I can help you explore the content of your uploaded document. Feel free to ask me any questions about it!"
- "Thank you! Is there anything specific you'd like to know about your document? I can summarize sections, explain concepts, or find specific information."

Conversation History:
{history}"""),
                    ("human", "{question}")
                ])
            else:
                # Strict document-grounded responses for actual questions
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an AI research assistant. Answer questions using ONLY the provided document context.

RULES:
1. Use only information from the context below
2. If information isn't in context, say "I don't have enough information in this document to answer that."
3. Use phrases like "According to the document" when citing
4. Keep formatting simple: use **bold** sparingly, # for headers, - for lists
5. Use proper line breaks between paragraphs

Document Context:
{context}

Conversation History:
{history}

Answer based only on the context above."""),
                ("human", "{question}")
            ])            # Format the prompt based on type
            if is_greeting or is_short_query:
                # For greetings, don't include document context
                formatted_prompt = prompt.format_messages(
                    history=history_text,
                    question=state.get("question", "")
                )
            else:
                # For actual questions, include full context
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
                }, on_conflict="session_id").execute()
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
            
            # Load memory and retrieve context in parallel for speed
            import asyncio
            memory_task = self._load_memory(state)
            context_task = self._retrieve_context(state)
            
            # Wait for both to complete
            state_memory = await memory_task
            state_context = await context_task
            
            # Merge states
            state.update(state_memory)
            state.update(state_context)
            if state.get("error"):
                yield {"type": "error", "error": state["error"]}
                return
            
            # Send sources if available
            if state.get("sources"):
                yield {"type": "sources", "sources": state["sources"]}
                
            # Generate streaming response immediately
            async for chunk in self._stream_response(state):
                yield chunk
                
            # Save memory asynchronously (non-blocking)
            asyncio.create_task(self._save_memory_async(state))
            
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
            
            # Prepare context (same as in generate_response) with explicit page information
            context_text = ""
            if state.get("context", []):
                context_text = "\n\n".join([
                    f"[Page {item['metadata'].get('page', 'unknown')}] {item['content']}\n(Relevance Score: {item['relevance_score']:.2f})"
                    for item in state.get("context", [])
                ])
            else:
                context_text = "No relevant context found in this document."
            
            history_text = ""
            if state.get("memory_summary"):
                history_text = f"Previous conversation summary: {state['memory_summary']}\n\n"
            
            recent_history = state.get("chat_history", [])[-10:]
            for msg in recent_history:
                role = "Human" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an AI research assistant. Answer questions using ONLY the provided document context.

RULES:
1. Use only information from the context below
2. If information isn't in context, say "I don't have enough information in this document to answer that."
3. Use phrases like "According to the document" when citing
4. Keep formatting simple: use **bold** sparingly, # for headers, - for lists
5. Use proper line breaks between paragraphs

Document Context:
{context}

Conversation History:
{history}

Answer based only on the context above."""),
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