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
            api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"
        )
        self.qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            check_compatibility=False
        )

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
        
        prompt = f"""You are an expert educational planner. Create a comprehensive, detailed {request.duration_weeks}-week study plan.

📚 DOCUMENT DETAILS:
- Title: {paper_title}
- Exam Type: {request.exam_type.value}
- Study Style: {request.study_style.value} 
- Available Daily Hours: {request.daily_hours} hours
{f"- Target Exam: {request.exam_name}" if request.exam_name else ""}

📄 DOCUMENT CONTENT:
{context[:4000]}

📋 REQUIREMENTS:
Generate a DETAILED and ACTIONABLE study plan. Each element must be specific and helpful:

1. **Topics**: Use full descriptive names (e.g., "Introduction to Node.js Architecture and Event Loop" NOT just "Node.js Overview")

2. **Tasks**: Provide 3-5 SPECIFIC, ACTIONABLE tasks per day, such as:
   - "Read Chapter 2: Understanding Express Middleware (pages 45-78) and take notes on the middleware chain"
   - "Complete 10 practice problems on routing patterns from the exercise section"
   - "Build a simple REST API with 3 endpoints (GET, POST, DELETE) to practice CRUD operations"
   - "Watch the recommended video tutorial on async/await patterns (30 mins)"
   - "Create flashcards for the 15 key concepts covered today"
   
3. **Goals**: Write 2-3 measurable weekly goals (e.g., "Master the fundamentals of Express routing and be able to create nested routes independently")

4. **Focus Areas**: Describe what the week covers in detail (e.g., "Deep dive into Express.js framework - routing, middleware, error handling, and request/response cycle")

5. **Revision Topics**: List specific concepts to review, not just category names

Generate a structured JSON with this EXACT format:
{{
  "weeks": [
    {{
      "week": 1,
      "focus_area": "Detailed description of this week's main focus and learning objectives",
      "goals": [
        "Specific measurable goal 1",
        "Specific measurable goal 2"
      ],
      "revision_topics": ["Specific concept to revise from previous learning"],
      "days": [
        {{
          "day": 1,
          "topics": ["Full descriptive topic name with subtopics"],
          "tasks": [
            "Specific actionable task 1 with details",
            "Specific actionable task 2 with details",
            "Specific actionable task 3 with details"
          ],
          "duration_hours": {request.daily_hours}
        }}
      ]
    }}
  ],
  "tips": [
    "Specific, actionable study tip 1",
    "Specific, actionable study tip 2",
    "Specific, actionable study tip 3",
    "Specific, actionable study tip 4",
    "Specific, actionable study tip 5"
  ]
}}

📌 IMPORTANT RULES:
- Create exactly {request.duration_weeks} weeks
- Each week has 6 study days (Day 1-6, with Day 7 as rest)
- Intensity should match "{request.study_style.value}" style:
  * intensive = challenging tasks, more content per day
  * balanced = moderate pace, mix of learning and practice
  * light = relaxed pace, focus on understanding over speed
- Base ALL content on the actual document provided
- Include progressive revision starting from week 2
- Make tasks specific enough that a student knows EXACTLY what to do
- Each day's tasks should take approximately {request.daily_hours} hours total

⚠️ OUTPUT: Respond with ONLY valid JSON. No markdown, no code blocks, no explanations."""

        response = self.client.chat.completions.create(
            model="grok-3-fast",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert study planner who creates detailed, actionable, and comprehensive study schedules. Your plans are thorough, specific, and help students understand exactly what to do each day. Always output valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=8000,
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
