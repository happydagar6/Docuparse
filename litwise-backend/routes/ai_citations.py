"""
AI-Powered Citation Generator Routes

Endpoints for generating citations using hybrid DOI + AI approach
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
import tempfile
import os

from services.ai_citation_service import ai_citation_service

router = APIRouter()


@router.post("/generate-citation")
async def generate_citation(
    file: UploadFile = File(..., description="PDF file to generate citation from")
) -> Dict:
    """
    Generate APA 7th Edition citation from uploaded PDF
    
    **Hybrid Cost-Saving Architecture:**
    1. Extract text from first 2 pages only
    2. Search for DOI using regex
    3. If DOI found: Use free Crossref API
    4. If no DOI: Use Grok AI to extract metadata
    5. Format into APA 7th Edition
    
    **Request:**
    - file: PDF file (multipart/form-data)
    
    **Response:**
    ```json
    {
        "citation": "Author, A. (2021). Title. *Journal*, *5*(3), 123-145. https://doi.org/...",
        "source": "crossref" or "ai",
        "metadata": {
            "title": "...",
            "authors": ["...", "..."],
            "year": 2021,
            "journal": "...",
            "volume": "5",
            "issue": "3",
            "pages": "123-145",
            "doi": "10.xxxx/xxxxx"
        },
        "success": true,
        "error": null
    }
    ```
    
    **Error Response:**
    ```json
    {
        "citation": null,
        "source": null,
        "metadata": null,
        "success": false,
        "error": "Error message"
    }
    ```
    """
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are accepted."
        )
    
    # Create temporary file for processing
    temp_file = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        print(f"📄 Processing PDF: {file.filename}")
        
        # Generate citation using AI service
        result = await ai_citation_service.generate_citation_from_pdf(temp_path)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Return result (success or error)
        if result['success']:
            print(f"✅ Citation generated successfully (source: {result['source']})")
        else:
            print(f"❌ Citation generation failed: {result['error']}")
        
        return result
        
    except Exception as e:
        # Clean up temp file on error
        if temp_file and os.path.exists(temp_file.name):
            os.remove(temp_file.name)
        
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Citation generation failed: {str(e)}"
        )


@router.post("/batch-generate-citations")
async def batch_generate_citations(
    files: list[UploadFile] = File(..., description="Multiple PDF files")
) -> Dict:
    """
    Generate citations for multiple PDFs in batch
    
    **Request:**
    - files: List of PDF files (multipart/form-data)
    
    **Response:**
    ```json
    {
        "citations": [
            {
                "filename": "paper1.pdf",
                "citation": "...",
                "source": "crossref",
                "success": true
            },
            {
                "filename": "paper2.pdf",
                "citation": "...",
                "source": "ai",
                "success": true
            }
        ],
        "total": 2,
        "successful": 2,
        "failed": 0
    }
    ```
    """
    
    if len(files) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 PDFs allowed per batch request"
        )
    
    results = []
    successful = 0
    failed = 0
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            results.append({
                "filename": file.filename,
                "citation": None,
                "source": None,
                "success": False,
                "error": "Invalid file type"
            })
            failed += 1
            continue
        
        temp_file = None
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            # Generate citation
            result = await ai_citation_service.generate_citation_from_pdf(temp_path)
            
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Add filename to result
            result['filename'] = file.filename
            results.append(result)
            
            if result['success']:
                successful += 1
            else:
                failed += 1
                
        except Exception as e:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            
            results.append({
                "filename": file.filename,
                "citation": None,
                "source": None,
                "success": False,
                "error": str(e)
            })
            failed += 1
    
    return {
        "citations": results,
        "total": len(files),
        "successful": successful,
        "failed": failed
    }
