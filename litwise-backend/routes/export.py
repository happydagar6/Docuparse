"""
Export Routes - APA Document Generation
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict
from datetime import datetime

from models import APAExportRequest
from services.apa_export_service import apa_export_service
from auth_middleware import get_current_user, AuthUser

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/apa")
async def export_apa_document(
    request: APAExportRequest,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Export research paper as APA 7th Edition formatted .docx file
    
    **Authentication Required**: User must be logged in
    
    **Request Body**:
    - title: Paper title
    - running_head: Short title for header (max 50 chars)
    - authors: List of author names
    - affiliation: Author affiliation (optional)
    - content: List of paragraphs with citation placeholders
    - references_metadata: Metadata for cited papers
    
    **Citation Format**:
    In your content text, use placeholders like `{{paper_123}}` which will be 
    replaced with formatted citations like `(Smith et al., 2021)`.
    
    **Returns**: 
    Word document (.docx) file as download
    """
    try:
        # Convert Pydantic models to dicts for service
        references_dict = {
            paper_id: ref.model_dump()
            for paper_id, ref in request.references_metadata.items()
        }
        
        content_list = [para.model_dump() for para in request.content]
        
        # Generate document
        doc_buffer = apa_export_service.generate_document(
            title=request.title,
            running_head=request.running_head,
            authors=request.authors,
            content=content_list,
            references_metadata=references_dict,
            affiliation=request.affiliation,
            abstract=request.abstract,
            keywords=request.keywords
        )
        
        # Generate filename
        sanitized_title = "".join(
            c for c in request.title if c.isalnum() or c in (' ', '-', '_')
        ).strip()[:50]
        filename = f"{sanitized_title}_{datetime.now().strftime('%Y%m%d')}.docx"
        
        # Return as streaming response
        return StreamingResponse(
            doc_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")


@router.get("/apa/example")
async def get_example_request():
    """
    Get example request body for APA export endpoint
    
    Use this to understand the expected format for the POST /export/apa endpoint
    """
    return {
        "title": "The Impact of Artificial Intelligence on Modern Healthcare Systems",
        "running_head": "AI IN HEALTHCARE",
        "authors": ["Dr. John Smith", "Dr. Sarah Johnson"],
        "affiliation": "Stanford University School of Medicine",
        "content": [
            {
                "text": "Artificial intelligence (AI) has emerged as a transformative force in healthcare, revolutionizing diagnostics, treatment planning, and patient care {{paper_001}}. The integration of machine learning algorithms into clinical practice has demonstrated unprecedented accuracy in disease detection {{paper_002}}.",
                "citations": ["paper_001", "paper_002"]
            },
            {
                "text": "Deep learning models, particularly convolutional neural networks, have shown remarkable performance in medical imaging analysis {{paper_003}}. Recent studies indicate that AI-assisted diagnosis can match or exceed human expert performance in specific domains such as radiology and pathology.",
                "citations": ["paper_003"]
            },
            {
                "text": "Despite these advances, several challenges remain. Data privacy concerns, algorithmic bias, and the need for regulatory frameworks are critical issues that must be addressed {{paper_001}}. The future of AI in healthcare depends on collaborative efforts between technologists, clinicians, and policymakers.",
                "citations": ["paper_001"]
            }
        ],
        "references_metadata": {
            "paper_001": {
                "title": "Artificial Intelligence in Healthcare: Past, Present and Future",
                "author_list": ["Topol, Eric J."],
                "year": "2019",
                "doi": "10.1038/s41591-018-0300-7",
                "publisher": "Nature Medicine"
            },
            "paper_002": {
                "title": "Deep Learning for Healthcare: Review, Opportunities and Challenges",
                "author_list": ["Miotto, Riccardo", "Wang, Fei", "Wang, Shuang", "Jiang, Xiaoqian", "Dudley, Joel T."],
                "year": "2018",
                "doi": "10.1093/bib/bbx044",
                "publisher": "Briefings in Bioinformatics"
            },
            "paper_003": {
                "title": "A Survey on Deep Learning in Medical Image Analysis",
                "author_list": ["Litjens, Geert", "Kooi, Thijs", "Bejnordi, Babak Ehteshami"],
                "year": "2017",
                "doi": "10.1016/j.media.2017.07.005",
                "publisher": "Medical Image Analysis"
            }
        }
    }