import json
import uuid
from datetime import datetime
from typing import Optional
from openai import OpenAI
from qdrant_client import QdrantClient
from models.study_plan import StudyPlanRequest, StudyPlanResponse, WeekPlan, DayPlan
import os


class StudyPlanService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("XAPI_API_KEY"), base_url="https://api.x.ai/v1"
        )
        self.qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"))

    async def get_paper_context(self, paper_id: str, limit: int = 15) -> str:
        """Retrieve paper content from RAG system"""
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        results = self.qdrant_client.scroll(
            collection_name="litwise_collection",
            scroll_filter=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
            limit=limit,
            with_payload=True,
        )

        chunks = [point.payload.get("content", "") for point in results[0]]
        return "\n\n".join(chunks[:limit])

    async def generate_plan(
        self, request: StudyPlanRequest, paper_title: str
    ) -> StudyPlanResponse:
        """Generate study plan using AI"""

        # Get paper context from RAG
        context = await self.get_paper_context(request.paper_id)
        prompt = f"""Create a {request.duration_weeks}-week study plan for:
Document: {paper_title}
Exam Type: {request.exam_type.value}
Study Style: {request.study_style.value}
Daily Study Hours: {request.daily_hours}
{f"Exam Name: {request.exam_name}" if request.exam_name else ""}

Document Content Summary:
{context[:3000]}

Generate a structured JSON study plan with this exact format:
{{
  "weeks": [
    {{
      "week": 1,
      "focus_area": "Topic name",
      "goals": ["Goal 1", "Goal 2"],
      "revision_topics": ["Topic to revise"],
      "days": [
        {{
          "day": 1,
          "topics": ["Topic 1"],
          "tasks": ["Read chapter X", "Practice problems"],
          "duration_hours": 2
        }}
      ]
    }}
  ],
  "tips": ["Tip 1", "Tip 2", "Tip 3"]
}}

Rules:
- Create exactly {request.duration_weeks} weeks
- Each week has 6 study days (1 rest day)
- Match the {request.study_style.value} intensity
- Focus on topics from the document
- Include revision in later weeks
- Respond ONLY with valid JSON, no markdown"""

    response = self.client.chat.completions.create(
        model="grok-4.1-fast-reasoning",
        messages=[
            {
                "role": "system",
                "content": "You are a study planner. Output only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4000,
    )

    plan_json = json.loads(response.choices[0].message.content)

    return StudyPlanResponse(
        id=str(uuid.uuid4()),
        paper_id=request.paper_id,
        paper_title=paper_title,
        duration_weeks=request.duration_weeks,
        exam_type=request.exam_type.value,
        study_style=request.study_style.value,
        weeks=[WeekPlan(**w) for w in plan_json["weeks"]],
        tips=plan_json.get("tips", []),
        created_at=datetime.utcnow(),
    )


study_plan_service = StudyPlanService()
