from fastapi import APIRouter, HTTPException
from models.study_plan import StudyPlanRequest, StudyPlanResponse
from services.study_plan_service import study_plan_service
from workflow.db import supabase
from datetime import datetime

router = APIRouter(prefix="/api/study-plan", tags=["Study Plan"])

@router.post("/generate", response_model=StudyPlanResponse)
async def generate_study_plan(request: StudyPlanRequest):
    """Generate a study plan for a paper"""
    
    # Get paper details
    paper = supabase.table("papers").select("*").eq("id", request.paper_id).single().execute()
    if not paper.data:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
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
async def list_study_plans(paper_id: str = None):
    """List all study plans, optionally filtered by paper"""
    
    query = supabase.table("study_plans").select("*").order("created_at", desc=True)
    if paper_id:
        query = query.eq("paper_id", paper_id)
    
    result = query.limit(20).execute()
    return {"plans": result.data}

@router.get("/{plan_id}")
async def get_study_plan(plan_id: str):
    """Get a specific study plan"""
    
    result = supabase.table("study_plans").select("*").eq("id", plan_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return result.data

@router.delete("/{plan_id}")
async def delete_study_plan(plan_id: str):
    """Delete a study plan"""
    supabase.table("study_plans").delete().eq("id", plan_id).execute()
    return {"success": True}