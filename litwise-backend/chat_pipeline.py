import os
import json
import asyncio
from typing import Dict, Optional, AsyncGenerator, List
from datetime import datetime

# LangChain imports
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate


# LangSmith imports
from langsmith import traceable, Client

# Qdrant imports
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

# Supabase imports
from workflow.db import supabase, qdrant
from dotenv import load_dotenv
load_dotenv()


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
            model="gpt-5-mini-2025-08-07",
            api_key=os.getenv("OPENAI_API_KEY"),
            streaming=True
        )
        
        # Use OpenAI embeddings for query encoding
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
            
            # Import enhanced search system and financial RAG pipeline
            from workflow.enhanced_search import enhanced_search
            from workflow.financial_rag_pipeline import financial_rag
            
            # Use hybrid search for better results
            try:
                # We use OpenAI text-embedding-3-small to generate dense vectors.
                print(f"✅ Using OpenAI embedder for hybrid search")
                embeddings_model = self.embeddings
                
                # Here we perform Hybrid Search (Dense Vectors + BM25 Sparse Vectors).
                # This ensures we match both semantic meaning (vectors) AND exact keywords (BM25).
                enhanced_documents = await enhanced_search.hybrid_search(
                    qdrant_client=self.qdrant_client,
                    embeddings_model=embeddings_model,
                    paper_id=paper_id,
                    query=question,
                    top_k=60  # Raised from 35 — broader retrieval for multi-part & comparative questions
                )
                
                if enhanced_documents:
                    print(f"✅ Enhanced hybrid search found {len(enhanced_documents)} relevant results")
                    
                    # Filter out clearly irrelevant results (threshold lowered 0.3→0.15
                    # so borderline-relevant chunks that span multi-part answers are kept)
                    high_relevance_docs = [doc for doc in enhanced_documents if doc['relevance_score'] > 0.15]

                    if not high_relevance_docs:
                        print("⚠️ No high-relevance results found, using best available")
                        high_relevance_docs = enhanced_documents[:8]  # Raised fallback 3→8
                    
                    # ✨ NEW: Process financial questions with deterministic calculations
                    financial_results = await asyncio.to_thread(
                        financial_rag.process_financial_question,
                        question,
                        high_relevance_docs
                    )
                    
                    # Store financial processing results in state
                    state["financial_calculations"] = financial_results.get("calculated_results")
                    state["normalized_tables"] = financial_results.get("normalized_tables")
                    state["question_metadata"] = financial_results.get("question_metadata")
                    state["financial_context"] = financial_results.get("context_for_llm")
                    
                    print(f"✅ Financial processing complete. Question type: {financial_results.get('question_metadata', {}).get('type')}")
                    if financial_results.get("calculated_results"):
                        print(f"✅ Generated {len(financial_results['calculated_results'])} verified calculations")
                    
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
            
            # Fallback: Generate embedding for the question using OpenAI
            print(f"📍 Generating query embedding with OpenAI...")
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
    
    def _select_optimal_context(self, results: List[Dict], max_tokens: int = 6000) -> List[Dict]:
        """Select optimal context based on relevance and token budget.
        Limits raised (2500→6000 tokens, 8→20 chunks) to leverage the 128k context window
        of GPT-5-mini and provide comprehensive context for broad questions."""
        if not results:
            return []

        # Sort by relevance score (descending) — raised cap from 8→20 for broader coverage
        sorted_results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)[:20]

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
                break  # Stop when we hit the limit

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
            
            # Get optimized history based on conversation length
            chat_history = state.get("chat_history", [])
            memory_summary = state.get("memory_summary", "")
            recent_history, emphasize_summary = self._get_optimal_context(chat_history, memory_summary)
            
            # Build history text with smart formatting
            history_text = ""
            history_length = len(chat_history)
            
            if memory_summary and emphasize_summary:
                # Long conversation: Emphasize summary
                history_text = f"""CONVERSATION SUMMARY (Based on {history_length} messages):
{memory_summary}

RECENT EXCHANGES (Last {len(recent_history)} messages):
"""
            elif memory_summary:
                # Medium conversation: Include summary
                history_text = f"Previous conversation summary: {memory_summary}\n\nRecent messages:\n"
            else:
                # Short conversation: Simple format
                history_text = "Conversation history:\n"
            
            # Add recent messages
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
                    ("system", """You are a friendly and knowledgeable AI research assistant. Your job is to answer questions about documents in a helpful, conversational way.

Key Guidelines:
1. ✅ Base all answers exclusively on the document content provided
2. ✅ Be warm and encouraging in your responses
3. ✅ Clearly cite where information comes from (e.g., "The document mentions..." or "According to the paper...")
4. ❌ Don't use external knowledge or make assumptions
5. ❌ If you can't find the answer, be honest: "I don't have that information in this document, but here's what I found..."

Formatting Tips:
- Use **bold** for key terms (sparingly)
- Use bullet points (-) for lists
- Use clear section breaks between paragraphs
- Keep language conversational and easy to understand

Document Context:
{context}

Conversation History:
{history}

Now, answer the user's question based only on the document above. Be helpful and friendly! 😊"""),
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

    def _get_optimal_context(self, chat_history: List[Dict], memory_summary: str) -> tuple:
        """Smart context selection based on conversation length
        
        Returns:
            tuple: (recent_messages, should_emphasize_summary)
        """
        history_length = len(chat_history)
        
        if history_length <= 20:
            # Short conversation: use last 10 messages, summary optional
            return chat_history[-10:], False
        elif history_length <= 50:
            # Medium conversation: use last 7 messages, include summary
            return chat_history[-7:], False
        else:
            # Long conversation: use last 5 messages, emphasize summary
            return chat_history[-5:], True
    
    async def _stream_response(self, state: Dict) -> AsyncGenerator[Dict, None]:
        """Stream the LLM response token by token"""
        try:
            print("Starting LLM streaming response")
            
            # ✨ NEW: Use financial context if available, otherwise use standard context
            if state.get("financial_context"):
                print("✅ Using financial context with verified calculations")
                context_text = state.get("financial_context")
            elif state.get("context", []):
                # Enhanced context formatting with chunk type awareness
                context_parts = []
                
                for idx, item in enumerate(state.get("context", []), 1):
                    metadata = item.get('metadata', {})
                    page = metadata.get('page', 'unknown')
                    chunk_type = metadata.get('type', 'text')
                    content = item['content']
                    
                    # Structured formatting based on chunk type
                    if chunk_type == 'table':
                        table_type = metadata.get('table_type', 'table')
                        context_parts.append(
                            f"📊 [{chunk_type.upper()}] Page {page}\n"
                            f"Type: {table_type}\n"
                            f"{content}"
                        )
                    elif chunk_type == 'image':
                        context_parts.append(
                            f"🖼️ [IMAGE] Page {page}\n"
                            f"{content}"
                        )
                    else:
                        context_parts.append(
                            f"📄 [TEXT] Page {page}\n"
                            f"{content}"
                        )
                
                context_text = "\n\n" + "="*80 + "\n".join(["\n"] + context_parts)
            else:
                context_text = "No relevant context found in this document."
            
            # Get optimized history based on conversation length
            chat_history = state.get("chat_history", [])
            memory_summary = state.get("memory_summary", "")
            recent_history, emphasize_summary = self._get_optimal_context(chat_history, memory_summary)
            
            # Build history text with smart formatting
            history_text = ""
            history_length = len(chat_history)
            
            if memory_summary and emphasize_summary:
                # Long conversation: Emphasize summary
                history_text = f"""CONVERSATION SUMMARY (Based on {history_length} messages):
{memory_summary}

RECENT EXCHANGES (Last {len(recent_history)} messages):
"""
            elif memory_summary:
                # Medium conversation: Include summary
                history_text = f"Previous conversation summary: {memory_summary}\n\nRecent messages:\n"
            else:
                # Short conversation: Simple format
                history_text = "Conversation history:\n"
            
            # Add recent messages
            for msg in recent_history:
                role = "Human" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n"

            # ✨ NEW: Adapt prompt based on question type
            question_metadata = state.get("question_metadata", {})
            has_calculations = state.get("financial_calculations") is not None
            
            if has_calculations:
                # ✅ FIXED: Financial analysis prompt - constructive guidance instead of restrictive language
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are a senior financial analyst AI assistant with access to a deterministic calculation engine.

🎯 PRIMARY OBJECTIVE:
Provide accurate, well-cited financial analysis using verified calculations when available.

📊 HOW TO USE CALCULATIONS:

When "✅ VERIFIED CALCULATIONS" exist in the context:
1. ✅ Use the EXACT result provided (these are pre-computed by a financial engine)
2. ✅ Reference the formula shown: "Current Ratio = 1.85 (calculated as Current Assets ÷ Current Liabilities)"
3. ✅ ALWAYS cite sources: "(Source: Balance Sheet, Page 15)"
4. ✅ Add business context: Explain what the result means for stakeholders

When calculations are "⛔ BLOCKED" or "❌ FAILED":
1. ✅ Explain WHY it couldn't be calculated (missing inputs listed in the context)
2. ✅ If some data exists, describe what IS available
3. ✅ Suggest what additional information would enable the calculation
4. ❌ Don't say "I cannot perform calculations" - instead say "The calculation requires [missing data]"

When NO calculation section exists:
1. ✅ Use simple arithmetic for straightforward questions (e.g., "5 + 3 = 8")
2. ✅ For complex financial ratios, extract values from tables and perform basic math
3. ✅ Always show your work: "Revenue ($50M) - Cost ($30M) = Profit ($20M)"
4. ✅ Cite where each number came from: "(Revenue from Income Statement, Page 12)"

🧠 DECISION TREE:
1. Check context for "VERIFIED CALCULATIONS" section
   - If found → Use those exact results
   - If not found → Extract numbers from tables and calculate yourself
2. For ratio questions without verified calculations:
   - Find numerator in document → cite page
   - Find denominator in document → cite page  
   - Perform division → show formula
   - Interpret result → add context

📋 QUALITY STANDARDS:
1. ✅ For margins: Express in percentage (22.27%) AND basis points if showing changes (7.7 bps)
2. ✅ Always show the formula ONCE, then use result
3. ✅ Never round provided values - use exactly as shown
4. ✅ If partial data exists, provide partial answer + explain what's missing

💡 EXAMPLE RESPONSE (with verified calculation):
"The Current Ratio is **1.85** (calculated as $37.2M Current Assets ÷ $20.1M Current Liabilities, Source: Balance Sheet, Page 15).

This indicates strong short-term liquidity - the company has $1.85 in current assets for every $1 of current liabilities. A ratio above 1.5 is generally considered healthy for manufacturing companies."

💡 EXAMPLE RESPONSE (without verified calculation):
"Looking at the Balance Sheet on Page 15:
- Current Assets: $37.2M
- Current Liabilities: $20.1M  

Current Ratio = $37.2M ÷ $20.1M = **1.85**

This indicates strong short-term liquidity - the company has $1.85 in current assets for every $1 of current liabilities."

📄 Document Context (may include verified calculations):
{context}

💬 Conversation History:
{history}

Now answer the question using this framework. Be helpful, precise, and well-cited."""),
                    ("human", "{question}")
                ])
            else:
                # Enhanced standard research assistant prompt
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert AI research assistant specialized in document analysis and academic literature review.

🎯 PRIMARY OBJECTIVE:
Provide accurate, well-sourced answers using ONLY the document content provided below.

📋 CORE PRINCIPLES:
1. ✅ **Document Grounding**: Base ALL answers exclusively on provided context
2. ✅ **Source Attribution**: Always cite page numbers: "(Page X)" or "(Pages X-Y)"
3. ✅ **Honest Uncertainty**: If information isn't in the document, clearly state: "This document doesn't contain information about [topic]"
4. ✅ **Partial Answers**: If you have SOME relevant info, share it and note what's missing
5. ❌ **No External Knowledge**: Don't use information not in the document
6. ❌ **No Assumptions**: Don't infer or extrapolate beyond what's explicitly stated

📊 RESPONSE STRUCTURE:
1. **Direct Answer**: Start with the most relevant information
2. **Supporting Details**: Add context, quotes, or elaboration
3. **Source Citations**: Include page numbers for ALL claims
4. **Caveats** (if any): Note limitations or missing information

💬 TONE & STYLE:
- Be conversational yet professional
- Use **bold** for key terms (sparingly)
- Use bullet points for lists
- Keep paragraphs according to query asked
- Be helpful and encouraging

📄 Document Context:
{context}

💬 Conversation History:
{history}

Answer the question using only the document above. Be precise, helpful, and always cite your sources!"""),
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
            
            # ✨ NEW: Validate response for financial accuracy
            if has_calculations:
                try:
                    print("🔍 Validating financial response accuracy...")
                    from workflow.financial_rag_pipeline import financial_rag
                    
                    is_valid, issues, correction_prompt = await asyncio.to_thread(
                        financial_rag.validate_response,
                        full_response,
                        state.get("financial_calculations"),
                        question_metadata
                    )
                    
                    if not is_valid:
                        print(f"⚠️ Validation found {len(issues)} issues. Generating correction...")
                        
                        # Generate corrected response
                        if correction_prompt:
                            correction_messages = [
                                SystemMessage(content=correction_prompt),
                                HumanMessage(content=state.get("question", ""))
                            ]
                            
                            corrected_response = ""
                            yield {"type": "token", "content": "\n\n[Correcting calculation errors...]\n\n"}
                            
                            async for chunk in self.openai_llm.astream(correction_messages):
                                if chunk.content:
                                    corrected_response += chunk.content
                                    yield {"type": "token", "content": chunk.content}
                            
                            full_response = corrected_response
                            print("✅ Response corrected with verified calculations")
                    else:
                        print("✅ Response validation passed")
                
                except Exception as validation_error:
                    # Don't let validation errors break the response
                    print(f"⚠️ Validation failed but continuing: {validation_error}")
                    logger.error(f"Validation error: {validation_error}", exc_info=True)
            
            # Save complete message to state for memory saving
            state["full_response"] = full_response
            
        except Exception as e:
            print(f"Streaming failed: {str(e)}")
            import traceback
            traceback.print_exc()
            yield {"type": "error", "error": f"Streaming failed: {str(e)}"}

# Global instance
rag_pipeline = RAGChatPipeline()