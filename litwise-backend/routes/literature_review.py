from fastapi import APIRouter, HTTPException
from models.literature_review import LiteratureReviewRequest, LiteratureReviewResponse
from services.literature_review_service import literature_review_service
from workflow.db import supabase
from datetime import datetime

router = APIRouter(prefix="/api/literature-review", tags=["Literature Review"])


@router.post("/generate", response_model=LiteratureReviewResponse)
async def generate_literature_review(request: LiteratureReviewRequest):
    """Generate a literature review from a selected paper"""
    
    # Get paper titles for all selected papers
    paper_titles = {}
    for paper_id in request.paper_ids:
        paper = (
            supabase.table("papers")
            .select("id, title")
            .eq("id", paper_id)
            .single()
            .execute()
        )
        if paper.data:
            paper_titles[paper_id] = paper.data["title"] # Store title by ID
        else:
            paper_titles[paper_id] = "Unknown Title" # Fallback title
            
    if not paper_titles:
        raise HTTPException(status_code=404, detail="No valid papers found for the provided IDs")
    
    try:
        review = await literature_review_service.generate_review(request, paper_titles)
        
        # Save to database
        supabase.table("literature_reviews").insert(
            {
                "id": review.id,
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
async def list_literature_reviews(limit: int = 20):
    """List all literature reviews"""
    
    result = (
        supabase.table("literature_reviews")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"reviews": result.data}

@router.get("/{review_id}")
async def get_literature_review(review_id: str):
    """Get a specific literature review"""
    
    result = (
        supabase.table("literature_reviews")
        .select("*")
        .eq("id", review_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Literature review not found")
    
    return result.data


@router.delete("/{review_id}")
async def delete_literature_review(review_id: str):
    """Delete a literature review"""
    supabase.table("literature_reviews").delete().eq("id", review_id).execute()
    return {"success": True}
