from fastapi import APIRouter, HTTPException, Depends
from models.study_plan import StudyPlanRequest, StudyPlanResponse
from services.study_plan_service import study_plan_service
from workflow.db import supabase
from datetime import datetime
from auth_middleware import get_current_user, AuthUser
from services.rate_limiter_service import rate_limit_dependency

router = APIRouter(prefix="/api/study-plan", tags=["Study Plan"])

@router.post("/generate", response_model=StudyPlanResponse)
async def generate_study_plan(request: StudyPlanRequest, 
current_user: AuthUser = Depends(get_current_user),
rate_limit_check = Depends(rate_limit_dependency)
):
    """Generate a study plan for a paper. User must own the paper."""
    
    # Get paper details and verify ownership
    paper = supabase.table("papers").select("*").eq("id", request.paper_id).eq("user_id", current_user.id).single().execute()
    if not paper.data:
        raise HTTPException(status_code=404, detail="Paper not found or access denied")
    
    try:
        # We delegate the actual Study Plan Generation to `study_plan_service`.
        # Under the hood, this uses a LangChain agent and an LLM to generate
        # a structured, day-by-day JSON schedule based on the user's exam type and duration.
        plan = await study_plan_service.generate_plan(request, paper.data["title"])
        
        # Save to database
        supabase.table("study_plans").insert({
            "id": plan.id,
            "paper_id": request.paper_id,
            "paper_title": paper.data["title"],
            "duration_weeks": request.duration_weeks,
            "exam_type": request.exam_type.value,
            "study_style": request.study_style.value,
            "plan_data": plan.model_dump_json(),
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {str(e)}")

@router.get("/list")
async def list_study_plans(current_user: AuthUser = Depends(get_current_user), paper_id: str = None):
    """List user's study plans, optionally filtered by paper"""
    
    # Start with user's papers
    query = supabase.table("study_plans").select("*").order("created_at", desc=True)
    
    if paper_id:
        # Verify user owns the paper first
        paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        query = query.eq("paper_id", paper_id)
    else:
        # Filter by user's papers
        user_papers = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
        paper_ids = [p["id"] for p in user_papers.data]
        if paper_ids:
            query = query.in_("paper_id", paper_ids)
        else:
            return {"plans": []}
    
    result = query.limit(20).execute()
    return {"plans": result.data}

@router.get("/{plan_id}")
async def get_study_plan(plan_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get a specific study plan. User must own the associated paper."""
    
    result = supabase.table("study_plans").select("*").eq("id", plan_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Verify user owns the paper
    paper_check = supabase.table("papers").select("id").eq("id", result.data["paper_id"]).eq("user_id", current_user.id).execute()
    if not paper_check.data:
        raise HTTPException(status_code=404, detail="Plan not found or access denied")
    
    return result.data

@router.delete("/{plan_id}")
async def delete_study_plan(plan_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Delete a study plan. User must own the associated paper."""
    
    # Check if plan exists and verify ownership
    plan = supabase.table("study_plans").select("paper_id").eq("id", plan_id).single().execute()
    if not plan.data:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Verify user owns the paper
    paper_check = supabase.table("papers").select("id").eq("id", plan.data["paper_id"]).eq("user_id", current_user.id).execute()
    if not paper_check.data:
        raise HTTPException(status_code=404, detail="Plan not found or access denied")
    
    supabase.table("study_plans").delete().eq("id", plan_id).execute()
    return {"success": True}