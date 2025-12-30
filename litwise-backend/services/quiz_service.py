"""
Quiz Generator Service
Handles quiz generation, evaluation, and analytics using RAG + LLM
Production-ready implementation with closed-world constraints
"""

import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import os
import logging


from models.quiz import (
    QuizConfig, 
    QuizQuestion, 
    QuizResponse,
    QuizAttemptRequest,
    QuizAttemptResponse,
    DifficultyLevel,
    QuizType,
    RetrievalContext
)
from workflow.db import supabase

logger = logging.getLogger(__name__)


# ============================================
# CLOSED-WORLD QUIZ GENERATION PROMPT
# ============================================
# This prompt enforces strict grounding to provided context
# Prevents hallucinations and ensures all questions are verifiable

QUIZ_GENERATION_SYSTEM_PROMPT = """You are a rigorous, fact-based quiz generator operating under STRICT CLOSED-WORLD CONSTRAINTS.

## CRITICAL RULES (NON-NEGOTIABLE)

### 1. ABSOLUTE GROUNDING - CLOSED WORLD ASSUMPTION
- Generate questions ONLY from the provided <CONTEXT> chunks.
- Do NOT use any pre-trained knowledge about the topic.
- Every question, answer option, and explanation MUST be directly verifiable in the provided context.
- If you cannot find adequate context, state this clearly instead of fabricating information.
- Treat the provided context as the ONLY source of truth.

### 2. MANDATORY JSON OUTPUT FORMAT
You MUST output ONLY valid JSON with NO additional text before or after.

```json
{
  "questions": [
    {
      "question_text": "Clear, specific question based ONLY on context",
      "options": [
        "Option A (one must be correct)",
        "Option B", 
        "Option C",
        "Option D"
      ],
      "correct_answer_index": 0,
      "explanation": "Detailed explanation. Start with 'According to the document...' Reference the exact section from context. Explain why correct and why others are wrong.",
      "source_citation": "Exact quote from the source context (5-50 words)",
      "source_page": 3,
      "difficulty": "easy|medium|hard",
      "quiz_type": "fact_based|scenario_based|mixed"
    }
  ],
  "quality_check": {
    "total_questions": 5,
    "grounded_questions": 5,
    "coverage_topics": ["topic1", "topic2"],
    "notes": "All questions grounded in context"
  }
}
```

### 3. QUESTION TYPES

**Fact-Based Questions:**
- Test direct recall and basic understanding
- Example: "According to the paper, what is X?"
- Answer is directly stated in context
- For "easy" difficulty

**Scenario-Based Questions:**
- Test application and synthesis of multiple concepts
- Build on context but require connecting ideas
- Example: "Based on the discussed principles, what would happen if...?"
- Answer must be derivable from combining concepts in context
- For "medium" and "hard" difficulty

**Mixed:**
- Combination of fact-based and scenario-based

### 4. DISTRACTORS (Wrong Options)
- Exactly 4 options per question
- 1 correct answer
- 3 plausible but incorrect options that:
  - Sound related to the topic
  - Could be mistaken for correct by someone skimming
  - Are NOT obviously wrong
  - Are derived from the context (misinterpreted or from different sections)

### 5. DIFFICULTY ASSIGNMENT
- **Easy:** Direct definitions, explicit statements, simple facts from context
- **Medium:** Understanding relationships, connecting concepts, simple application
- **Hard:** Synthesis of multiple concepts, critical analysis, complex reasoning from context

### 6. CITATIONS & EXPLANATIONS
- `source_citation`: Exact quote from the provided context (not paraphrased)
- `source_page`: Page number if available in metadata
- `explanation`: 
  - Start with "According to the document..."
  - Reference specific sections
  - Explain why the correct answer is right
  - Briefly explain why others are wrong
  - Must justify the answer using only context

### 7. PRE-OUTPUT QUALITY CHECKLIST
Before outputting, verify:
✓ All questions grounded in provided context?
✓ Every option distinct and plausible?
✓ Exactly 4 options per question?
✓ Exactly 1 correct answer per question?
✓ Explanations reference the source and justify answers?
✓ Citations are exact quotes from context?
✓ Difficulty distribution is appropriate?
✓ No use of external knowledge?
✓ Valid JSON format?

If ANY check fails, REVISE before outputting.

### 8. OUTPUT INSTRUCTIONS
- Respond with ONLY valid JSON
- No markdown code blocks
- No explanatory text before or after
- No trailing commas in JSON
- Ensure all strings are properly escaped"""


class QuizService:
    """
    Quiz generation and management service
    Uses RAG (Retrieval-Augmented Generation) + LLM
    """
    
    def __init__(self):
        """Initialize quiz service with API clients"""
        try:
            # Initialize XAI Grok API client
            self.client = OpenAI(
                api_key=os.getenv("XAI_API_KEY"),
                base_url="https://api.x.ai/v1"
            )
            
            # Initialize Qdrant vector database client
            self.qdrant_client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY"),
                check_compatibility=False,
            )
            
            # Initialize embedding model for semantic search
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            
            logger.info("✅ Quiz Service initialized successfully")
            logger.info(f"   - LLM Model: Grok-4-1-Fast-Reasoning")
            logger.info(f"   - Vector DB: Qdrant")
            logger.info(f"   - Embeddings: text-embedding-3-small")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Quiz Service: {str(e)}")
            raise

    
    async def generate_quiz(
        self, 
        config: QuizConfig, 
        paper_id: str,
        user_id: str
    ) -> QuizResponse:
        """
        Generate a quiz from a paper using RAG + LLM
        
        RAG Flow:
        1. Semantic search for topic-relevant context chunks from vector DB
        2. Construct LLM prompt with retrieved context
        3. Call Grok LLM to generate quiz questions as JSON
        4. Safely parse and validate JSON output
        5. Save quiz to Supabase with source citations
        
        Args:
            config (QuizConfig): Quiz configuration with difficulty, topic, question count, type
            paper_id (str): ID of paper to generate quiz from (verified by route)
            user_id (str): ID of quiz owner (verified by route)
            
        Returns:
            QuizResponse: Generated quiz with questions, explanations, and source citations
            
        Raises:
            ValueError: If no relevant context found or LLM parsing fails
            Exception: On database or API errors
        """
        try:
            logger.info(f"🎯 Quiz Generation Started")
            logger.info(f"   - Questions: {config.question_count}")
            logger.info(f"   - Difficulty: {config.difficulty_level.value}")
            logger.info(f"   - Type: {config.quiz_type.value}")
            logger.info(f"   - Topic: '{config.topic}'")
            
            # ========== STEP 1: RETRIEVE CONTEXT FROM VECTOR DATABASE ==========
            logger.info("📚 Step 1: Retrieving relevant context chunks from vector database...")
            context_chunks = await self._retrieve_context(
                paper_id=paper_id,
                topic=config.topic,
                num_chunks=50,  # Get 50 chunks for comprehensive coverage
                difficulty=config.difficulty_level
            )
            
            if not context_chunks:
                raise ValueError(
                    f"❌ No relevant context found for topic: '{config.topic}'. "
                    f"Try a different topic or check if the paper has been processed."
                )
            
            logger.info(f"   ✅ Retrieved {len(context_chunks)} context chunks")
            avg_score = sum(c["score"] for c in context_chunks) / len(context_chunks)
            logger.info(f"   ✅ Average relevance score: {avg_score:.3f}")
            
            # ========== STEP 2: BUILD LLM PROMPT ==========
            logger.info("📝 Step 2: Constructing LLM prompt with context...")
            user_prompt = self._build_quiz_prompt(
                config=config,
                context_chunks=context_chunks
            )
            logger.info(f"   ✅ Prompt size: {len(user_prompt)} characters")
            
            # ========== STEP 3: CALL LLM TO GENERATE QUIZ ==========
            logger.info("🤖 Step 3: Calling Grok-4-1-Fast-Reasoning to generate questions...")
            quiz_json = await self._call_llm_for_quiz(
                system_prompt=QUIZ_GENERATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_retries=3
            )
            
            # ========== STEP 4: PARSE AND VALIDATE JSON ==========
            logger.info("🔍 Step 4: Parsing and validating quiz JSON...")
            questions = self._parse_quiz_json(quiz_json, config.question_count)
            
            if len(questions) < config.question_count:
                logger.warning(
                    f"⚠️  Generated {len(questions)} questions, requested {config.question_count}. "
                    f"Using all {len(questions)} generated."
                )
            
            logger.info(f"   ✅ Successfully parsed {len(questions)} valid questions")
            
            # ========== STEP 5: SAVE QUIZ TO DATABASE ==========
            logger.info("💾 Step 5: Saving quiz to Supabase database...")
            quiz_id = str(uuid.uuid4())
            
            quiz_data = {
                "id": quiz_id,
                "user_id": user_id,
                "paper_id": paper_id,
                "title": config.title,
                "description": config.description,
                "difficulty_level": config.difficulty_level.value,
                "topic": config.topic,
                "question_count": len(questions),
                "quiz_type": config.quiz_type.value,
                "questions": [q.model_dump() for q in questions],  # Store as JSON
                "retrieval_context": [
                    {
                        "chunk_id": c["id"],
                        "paper_id": c["paper_id"],
                        "content": c["text"],
                        "page": c.get("metadata", {}).get("page"),
                        "similarity_score": c["score"]
                    }
                    for c in context_chunks
                ],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            supabase.table("quizzes").insert(quiz_data).execute()
            logger.info(f"   ✅ Quiz saved with ID: {quiz_id}")
            
            # ========== RETURN RESPONSE ==========
            logger.info(f"✅ Quiz generation completed successfully")
            
            return QuizResponse(
                id=quiz_id,
                user_id=user_id,
                paper_id=paper_id,
                title=config.title,
                description=config.description,
                difficulty_level=config.difficulty_level,
                topic=config.topic,
                question_count=len(questions),
                quiz_type=config.quiz_type,
                questions=questions,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"❌ Quiz generation failed: {str(e)}", exc_info=True)
            raise
    
    async def _retrieve_context(
        self,
        paper_id: str,
        topic: str,
        num_chunks: int = 50,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    ) -> List[Dict]:
        """
        Retrieve relevant context chunks from Qdrant vector database
        
        Uses semantic search to find chunks most relevant to the topic.
        Higher scores = more relevant.
        
        Args:
            paper_id: ID of paper to search
            topic: Topic to search for (will be embedded and used for semantic search)
            num_chunks: Number of chunks to retrieve
            difficulty: Difficulty level (for filtering/ranking if needed)
            
        Returns:
            List of context chunks with text, metadata, and relevance scores
        """
        try:
            logger.info(f"   - Embedding query: '{topic}'")
            
            # Embed the topic query using same model as document embeddings
            topic_embedding = self.embeddings.embed_query(topic)
            logger.info(f"   - Embedding dimension: {len(topic_embedding)}")
            
            # Search Qdrant for similar chunks
            logger.info(f"   - Searching Qdrant collection 'litwise_collection'...")
            search_results = self.qdrant_client.search(
                collection_name="litwise_collection",
                query_vector=topic_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",
                            match=MatchValue(value=paper_id)
                        )
                    ]
                ),
                limit=num_chunks,
                score_threshold=0.2,  # Minimum relevance threshold (0-1 scale)
            )
            
            # Format search results for use in prompt
            context_chunks = [
                {
                    "id": result.id,
                    "paper_id": result.payload.get("paper_id"),
                    "text": result.payload.get("text", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "score": result.score
                }
                for result in search_results
            ]
            
            if context_chunks:
                avg_score = sum(c["score"] for c in context_chunks) / len(context_chunks)
                logger.info(f"   - Retrieval stats: {len(context_chunks)} chunks, avg relevance {avg_score:.3f}")
            
            return context_chunks
            
        except Exception as e:
            logger.error(f"❌ Context retrieval failed: {str(e)}", exc_info=True)
            raise
    
    def _build_quiz_prompt(
        self,
        config: QuizConfig,
        context_chunks: List[Dict]
    ) -> str:
        """
        Build the user prompt for LLM quiz generation
        
        Includes:
        - Quiz requirements (difficulty, type, count)
        - Retrieved context chunks (top 50, limited to stay within token limits)
        - Specific instructions for question generation
        - Quality guidelines
        
        Args:
            config: Quiz configuration
            context_chunks: Retrieved context chunks from vector DB
            
        Returns:
            Formatted prompt string for LLM
        """
        # Limit to top 50 chunks to avoid exceeding token limits
        # Grok has 200k context window, but we want to be conservative
        context_text = "\n\n".join([
            f"[CHUNK {i+1} - Page {chunk.get('metadata', {}).get('page', 'N/A')}]\n{chunk['text']}"
            for i, chunk in enumerate(context_chunks[:50])
        ])
        
        prompt = f"""
You are a rigorous quiz generator. Generate a quiz based STRICTLY on the provided context.

## QUIZ REQUIREMENTS
- **Topic**: {config.topic}
- **Difficulty Level**: {config.difficulty_level.value}
- **Question Type**: {config.quiz_type.value}
- **Number of Questions**: {config.question_count}
- **Format**: Multiple choice (exactly 4 options per question)

## SOURCE CONTEXT
<CONTEXT>
{context_text}
</CONTEXT>

## INSTRUCTIONS

1. Generate exactly {config.question_count} questions based ONLY on the provided context.
2. Do NOT use external knowledge. Every question must be answerable from the context.
3. For each question:
   - Create exactly 4 options
   - One correct answer
   - Three plausible but incorrect distractors (all derived from context)
   - Provide detailed explanation referencing the exact context
   - Include a direct quote as source citation
4. Question Difficulty:
   - Easy: Direct recall from context
   - Medium: Understanding and connecting concepts
   - Hard: Synthesis and analysis of multiple concepts
5. Question Type:
   - fact_based: Direct questions about content
   - scenario_based: Application and reasoning questions
   - mixed: Combination of both

## QUALITY REQUIREMENTS

Before outputting, verify:
- ✓ All {config.question_count} questions are grounded in context
- ✓ Every question has exactly 4 distinct options
- ✓ Each question has exactly 1 correct answer
- ✓ Distractors are plausible but clearly incorrect to someone who read context
- ✓ Explanations cite the specific context section
- ✓ Difficulty matches "{config.difficulty_level.value}"
- ✓ Type matches "{config.quiz_type.value}"
- ✓ All citations are exact quotes from context

## OUTPUT FORMAT

Output ONLY valid JSON (no markdown, no extra text):

```json
{{
  "questions": [
    {{
      "question_text": "...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer_index": 0,
      "explanation": "According to the document...",
      "source_citation": "Exact quote from context",
      "source_page": 1,
      "difficulty": "easy|medium|hard",
      "quiz_type": "fact_based|scenario_based|mixed"
    }}
  ],
  "quality_check": {{
    "total_questions": {config.question_count},
    "grounded_questions": {config.question_count},
    "coverage_topics": [...],
    "notes": "Assessment of generation quality"
  }}
}}
```

Generate the quiz now. Output ONLY JSON.
"""
        return prompt
    
    async def _call_llm_for_quiz(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3
    ) -> Dict:
        """
        Call Grok-4-1-Fast-Reasoning LLM to generate quiz
        
        Implements retry logic for JSON parsing failures.
        Grok-4-1-Fast-Reasoning is optimized for reasoning tasks.
        
        Args:
            system_prompt: System prompt with instructions
            user_prompt: User prompt with context and requirements
            max_retries: Number of retries for JSON parsing
            
        Returns:
            Parsed quiz JSON
            
        Raises:
            ValueError: If JSON parsing fails after all retries
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"   - LLM attempt {attempt + 1}/{max_retries}")
                
                # Call Grok LLM
                response = self.client.chat.completions.create(
                    model="grok-4-1-fast-reasoning",  # Latest Grok model optimized for reasoning
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for consistency and factuality
                    max_tokens=4000,
                    timeout=120
                )
                
                response_text = response.choices[0].message.content.strip()
                logger.info(f"   - LLM response size: {len(response_text)} characters")
                
                # Remove markdown code blocks if present
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                response_text = response_text.strip()
                
                # Parse JSON
                quiz_json = json.loads(response_text)
                logger.info(f"   ✅ Successfully parsed LLM response as JSON")
                return quiz_json
                
            except json.JSONDecodeError as e:
                logger.warning(
                    f"   ⚠️  JSON parse error on attempt {attempt + 1}/{max_retries}: {str(e)}"
                )
                if attempt == max_retries - 1:
                    raise ValueError(
                        f"Failed to parse LLM response as JSON after {max_retries} attempts. "
                        f"Last error: {str(e)}"
                    )
                await asyncio.sleep(1)  # Brief pause before retry
                
            except Exception as e:
                logger.error(f"   ❌ LLM call error: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)  # Longer pause before retry
    
    def _parse_quiz_json(
        self,
        quiz_json: Dict,
        expected_count: int
    ) -> List[QuizQuestion]:
        """
        Safely parse and validate quiz JSON from LLM
        
        Converts raw LLM output to QuizQuestion Pydantic models.
        Skips invalid questions but ensures minimum quality.
        
        Args:
            quiz_json: Raw JSON from LLM
            expected_count: Expected number of questions
            
        Returns:
            List of validated QuizQuestion objects
            
        Raises:
            ValueError: If no valid questions could be parsed
        """
        try:
            questions_data = quiz_json.get("questions", [])
            
            if not questions_data:
                raise ValueError("No questions found in LLM response")
            
            questions = []
            for idx, q_data in enumerate(questions_data[:expected_count]):
                try:
                    question = QuizQuestion(
                        question_text=q_data["question_text"],
                        options=q_data["options"],
                        correct_answer_index=q_data["correct_answer_index"],
                        explanation=q_data["explanation"],
                        source_citation=q_data["source_citation"],
                        source_page=q_data.get("source_page"),
                        difficulty=DifficultyLevel(q_data.get("difficulty", "medium")),
                        quiz_type=QuizType(q_data.get("quiz_type", "fact_based"))
                    )
                    questions.append(question)
                    logger.info(f"   - Parsed question {idx + 1}: ✅")
                    
                except Exception as e:
                    logger.warning(
                        f"   ⚠️  Skipping invalid question {idx + 1}: {str(e)}"
                    )
                    continue
            
            if not questions:
                raise ValueError("No valid questions could be parsed from LLM response")
            
            logger.info(f"   ✅ Successfully parsed {len(questions)} valid questions")
            return questions
            
        except Exception as e:
            logger.error(f"❌ Quiz JSON parsing failed: {str(e)}", exc_info=True)
            raise
    
    async def evaluate_attempt(
        self,
        attempt_request: QuizAttemptRequest,
        user_id: str
    ) -> QuizAttemptResponse:
        """
        Evaluate user's quiz attempt and save results
        
        Calculates score based on correct answers.
        Saves attempt to database for tracking.
        
        Args:
            attempt_request: User's responses to quiz
            user_id: User ID (for ownership verification)
            
        Returns:
            QuizAttemptResponse with score and feedback
            
        Raises:
            PermissionError: If user doesn't own the quiz
            ValueError: If quiz not found
        """
        try:
            # Fetch quiz from database
            quiz_result = (
                supabase.table("quizzes")
                .select("*")
                .eq("id", attempt_request.quiz_id)
                .single()
                .execute()
            )
            
            if not quiz_result.data:
                raise ValueError(f"Quiz not found: {attempt_request.quiz_id}")
            
            quiz_data = quiz_result.data
            
            # Verify ownership
            if quiz_data["user_id"] != user_id:
                raise PermissionError("User does not own this quiz")
            
            # Parse questions
            questions = [QuizQuestion(**q) for q in quiz_data["questions"]]
            
            # Calculate score
            correct_count = 0
            for q_idx_str, selected_idx in attempt_request.responses.items():
                q_idx = int(q_idx_str)
                if q_idx < len(questions):
                    if questions[q_idx].correct_answer_index == selected_idx:
                        correct_count += 1
            
            total = len(questions)
            score = int((correct_count / total) * 100) if total > 0 else 0
            
            # Save attempt to database
            attempt_id = str(uuid.uuid4())
            attempt_data = {
                "id": attempt_id,
                "user_id": user_id,
                "quiz_id": attempt_request.quiz_id,
                "responses": attempt_request.responses,
                "score": score,
                "correct_answers": correct_count,
                "total_questions": total,
                "time_spent_seconds": attempt_request.time_spent_seconds,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("quiz_attempts").insert(attempt_data).execute()
            
            logger.info(
                f"✅ Attempt saved: {attempt_id} | "
                f"Score: {correct_count}/{total} ({score}%)"
            )
            
            return QuizAttemptResponse(
                id=attempt_id,
                quiz_id=attempt_request.quiz_id,
                correct_answers=correct_count,
                total_questions=total,
                score=score,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"❌ Attempt evaluation failed: {str(e)}", exc_info=True)
            raise
    
    async def get_quiz_analytics(
        self,
        quiz_id: str,
        user_id: str
    ) -> Dict:
        """
        Get analytics for a quiz (attempts, scores, performance)
        
        Args:
            quiz_id: Quiz ID
            user_id: User ID (for ownership verification)
            
        Returns:
            Dictionary with attempt statistics and history
            
        Raises:
            PermissionError: If user doesn't own the quiz
        """
        try:
            # Verify user owns quiz
            quiz = (
                supabase.table("quizzes")
                .select("user_id")
                .eq("id", quiz_id)
                .single()
                .execute()
            )
            
            if not quiz.data or quiz.data["user_id"] != user_id:
                raise PermissionError("Access denied to this quiz")
            
            # Get all attempts
            attempts_result = (
                supabase.table("quiz_attempts")
                .select("*")
                .eq("quiz_id", quiz_id)
                .execute()
            )
            
            attempts = attempts_result.data or []
            
            if not attempts:
                return {
                    "quiz_id": quiz_id,
                    "total_attempts": 0,
                    "best_score": None,
                    "average_score": None,
                    "attempts": []
                }
            
            scores = [a["score"] for a in attempts if a.get("score") is not None]
            
            return {
                "quiz_id": quiz_id,
                "total_attempts": len(attempts),
                "best_score": max(scores) if scores else None,
                "average_score": sum(scores) / len(scores) if scores else None,
                "attempts": [
                    {
                        "id": a["id"],
                        "score": a["score"],
                        "correct": a["correct_answers"],
                        "total": a["total_questions"],
                        "completed_at": a["completed_at"],
                        "time_spent": a.get("time_spent_seconds")
                    }
                    for a in sorted(
                        attempts, 
                        key=lambda x: x["completed_at"], 
                        reverse=True
                    )
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Analytics retrieval failed: {str(e)}", exc_info=True)
            raise


# ============================================
# SINGLETON INSTANCE
# ============================================
# Create and export a single quiz service instance for use throughout the app

quiz_service = QuizService()