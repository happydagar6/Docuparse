from fastapi import APIRouter, HTTPException, Depends
from models.literature_review import LiteratureReviewRequest, LiteratureReviewResponse
from services.literature_review_service import literature_review_service
from workflow.db import supabase
from datetime import datetime
from auth_middleware import get_current_user, AuthUser

router = APIRouter(prefix="/api/literature-review", tags=["Literature Review"])


@router.post("/generate", response_model=LiteratureReviewResponse)
async def generate_literature_review(request: LiteratureReviewRequest, current_user: AuthUser = Depends(get_current_user)):
    """Generate a literature review from selected papers. User must own all papers."""
    
    # Verify user owns all papers first
    owned_papers = supabase.table("papers").select("id, title").eq("user_id", current_user.id).in_("id", request.paper_ids).execute()
    
    if not owned_papers.data or len(owned_papers.data) != len(request.paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found or access denied")
    
    # Get paper titles for all selected papers
    paper_titles = {paper["id"]: paper["title"] for paper in owned_papers.data}
    
    try:
        review = await literature_review_service.generate_review(request, paper_titles)
        
        # Save to database with user_id
        supabase.table("literature_reviews").insert(
            {
                "id": review.id,
                "user_id": str(current_user.id),  # Convert UUID to string for TEXT field
                "topic": request.topic,
                "review_style": request.review_style.value,
                "paper_ids": request.paper_ids,
                "paper_count": len(request.paper_ids),
                "content": review.content.model_dump(),
                "word_count": review.word_count,
                "created_at": datetime.utcnow().isoformat(),
            }
        ).execute()
        return review
    
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate literature review: {str(e)}"
        )
        
@router.get("/list")
async def list_literature_reviews(current_user: AuthUser = Depends(get_current_user), limit: int = 20):
    """List user's literature reviews"""
    
    result = (
        supabase.table("literature_reviews")
        .select("*")
        .eq("user_id", str(current_user.id))  # Filter by user_id (TEXT field)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"reviews": result.data}

@router.get("/{review_id}")
async def get_literature_review(review_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get a specific literature review. User must own it."""
    
    result = (
        supabase.table("literature_reviews")
        .select("*")
        .eq("id", review_id)
        .eq("user_id", str(current_user.id))
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Literature review not found or access denied")
    
    return result.data


@router.delete("/{review_id}")
async def delete_literature_review(review_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Delete a literature review. User must own it."""
    
    # Verify ownership before deleting
    check = supabase.table("literature_reviews").select("id").eq("id", review_id).eq("user_id", str(current_user.id)).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Literature review not found or access denied")
    
    supabase.table("literature_reviews").delete().eq("id", review_id).eq("user_id", str(current_user.id)).execute()
    return {"success": True}
