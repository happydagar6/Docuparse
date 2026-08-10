
"""
Quiz Generation Routes
Endpoints for creating, retrieving, and evaluating quizzes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, cast, List, Any, Dict
from auth_middleware import get_current_user, AuthUser
from models.quiz import QuizConfig, QuizResponse, QuizAttemptRequest, QuizAttemptResponse
from services.quiz_service import quiz_service
from workflow.db import supabase
from services.rate_limiter_service import rate_limit_dependency
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["Quiz Generator"])


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(
    request: QuizConfig,
    current_user: AuthUser = Depends(get_current_user),
    rate_limit_check = Depends(rate_limit_dependency)
):
    """
    Generate a quiz from a paper
    
    **Authentication**: Required
    **Authorization**: User must own the paper
    
    Args:
        request: Quiz configuration
        current_user: Current authenticated user
        
    Returns:
        Generated quiz with questions
    """
    try:
        # Verify user owns the paper
        paper = supabase.table("papers").select("id").eq("id", request.paper_id).eq("user_id", current_user.id).single().execute()
        if not paper.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        
        # We delegate the actual Quiz Generation to `quiz_service`.
        # Under the hood, this extracts text from Qdrant and prompts an LLM 
        # (like Groq or XAI) to output a strictly formatted JSON array of questions.
        quiz = await quiz_service.generate_quiz(
            config=request,
            paper_id=request.paper_id,
            user_id=current_user.id
        )
        
        return quiz
        
    except ValueError as e:
        logger.error(f"Quiz generation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Quiz generation failed: {error_msg}", exc_info=True)
        
        # Provide more helpful error messages
        if "XAI_API_KEY" in error_msg or "api_key" in error_msg.lower():
            raise HTTPException(
                status_code=500, 
                detail="Quiz service not configured. Missing XAI API key. Please check backend environment variables."
            )
        elif "QDRANT" in error_msg or "qdrant" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail="Vector database not accessible. Please ensure Qdrant is running and configured correctly."
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate quiz: {error_msg[:100]}"
            )


@router.get("/list")
async def list_quizzes(
    current_user: AuthUser = Depends(get_current_user),
    paper_id: Optional[str] = None
):
    """
    List user's quizzes
    
    **Authentication**: Required
    
    Args:
        current_user: Current authenticated user
        paper_id: Optional filter by paper
        
    Returns:
        List of quizzes with metadata
    """
    try:
        query = supabase.table("quizzes").select("*").order("created_at", desc=True)
        
        if paper_id:
            # Verify user owns the paper
            paper = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
            if not paper.data:
                raise HTTPException(status_code=404, detail="Paper not found")
            query = query.eq("paper_id", paper_id)
        else:
            # Get user's papers
            user_papers = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
            up_data = cast(List[Any], user_papers.data or [])
            paper_ids = [p["id"] for p in up_data if isinstance(p, dict)]
            if not paper_ids:
                return {"quizzes": []}
            query = query.in_("paper_id", paper_ids)
        
        result = query.limit(50).execute()
        return {"quizzes": result.data or []}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing quizzes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list quizzes")


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get a specific quiz
    
    **Authentication**: Required
    **Authorization**: User must own the quiz
    """
    try:
        quiz = supabase.table("quizzes").select("*").eq("id", quiz_id).single().execute()
        q_data = cast(Dict[str, Any], quiz.data or {})
        if not q_data:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Verify ownership
        if q_data.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return q_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quiz: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch quiz")


@router.post("/attempt/submit", response_model=QuizAttemptResponse)
async def submit_attempt(
    request: QuizAttemptRequest,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Submit and evaluate a quiz attempt
    
    **Authentication**: Required
    **Authorization**: User must own the quiz
    """
    try:
        result = await quiz_service.evaluate_attempt(request, current_user.id)
        return result
        
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting attempt: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit attempt")


@router.get("/{quiz_id}/analytics")
async def get_quiz_analytics(
    quiz_id: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get quiz performance analytics
    
    **Authentication**: Required
    **Authorization**: User must own the quiz
    """
    try:
        analytics = await quiz_service.get_quiz_analytics(quiz_id, current_user.id)
        return analytics
        
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Delete a quiz
    
    **Authentication**: Required
    **Authorization**: User must own the quiz
    """
    try:
        # Verify ownership
        quiz = supabase.table("quizzes").select("user_id").eq("id", quiz_id).single().execute()
        q_data = cast(Dict[str, Any], quiz.data or {})
        if not q_data:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        if q_data.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete quiz (cascade will delete attempts)
        supabase.table("quizzes").delete().eq("id", quiz_id).execute()
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quiz: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete quiz")