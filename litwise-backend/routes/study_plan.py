from fastapi import APIRouter, HTTPException, Depends
from models.study_plan import StudyPlanRequest, StudyPlanResponse
from services.study_plan_service import study_plan_service
from workflow.db import supabase
from datetime import datetime, timezone
from typing import cast, List, Optional, Any, Dict
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
    paper_data = cast(Dict[str, Any], paper.data or {})
    if not paper_data:
        raise HTTPException(status_code=404, detail="Paper not found or access denied")
    
    try:
        paper_title = str(paper_data.get("title", ""))
        plan = await study_plan_service.generate_plan(request, paper_title)
        
        # Save to database
        supabase.table("study_plans").insert({
            "id": plan.id,
            "paper_id": request.paper_id,
            "paper_title": paper_title,
            "duration_weeks": request.duration_weeks,
            "exam_type": request.exam_type.value,
            "study_style": request.study_style.value,
            "plan_data": plan.model_dump_json(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {str(e)}")

@router.get("/list")
async def list_study_plans(current_user: AuthUser = Depends(get_current_user), paper_id: Optional[str] = None):
    """List user's study plans, optionally filtered by paper"""
    
    # Start with user's papers
    query = supabase.table("study_plans").select("*").order("created_at", desc=True)
    
    if paper_id:
        # Verify user owns the paper first
        paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        p_check = cast(List[Any], paper_check.data or [])
        if not p_check:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        query = query.eq("paper_id", paper_id)
    else:
        # Filter by user's papers
        user_papers = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
        up_data = cast(List[Any], user_papers.data or [])
        paper_ids = [p["id"] for p in up_data if isinstance(p, dict)]
        if paper_ids:
            query = query.in_("paper_id", paper_ids)
        else:
            return {"plans": []}
    
    result = query.limit(20).execute()
    return {"plans": result.data or []}

@router.get("/{plan_id}")
async def get_study_plan(plan_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get a specific study plan. User must own the associated paper."""
    
    result = supabase.table("study_plans").select("*").eq("id", plan_id).single().execute()
    res_data = cast(Dict[str, Any], result.data or {})
    if not res_data:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Verify user owns the paper
    paper_check = supabase.table("papers").select("id").eq("id", res_data.get("paper_id")).eq("user_id", current_user.id).execute()
    p_check = cast(List[Any], paper_check.data or [])
    if not p_check:
        raise HTTPException(status_code=404, detail="Plan not found or access denied")
    
    return res_data

@router.delete("/{plan_id}")
async def delete_study_plan(plan_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Delete a study plan. User must own the associated paper."""
    
    # Check if plan exists and verify ownership
    plan = supabase.table("study_plans").select("paper_id").eq("id", plan_id).single().execute()
    plan_data = cast(Dict[str, Any], plan.data or {})
    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Verify user owns the paper
    paper_check = supabase.table("papers").select("id").eq("id", plan_data.get("paper_id")).eq("user_id", current_user.id).execute()
    p_check = cast(List[Any], paper_check.data or [])
    if not p_check:
        raise HTTPException(status_code=404, detail="Plan not found or access denied")
    
    supabase.table("study_plans").delete().eq("id", plan_id).execute()
    return {"success": True}