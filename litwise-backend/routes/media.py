"""
Media Routes - Image and File Upload Handling
Handles figure/table image uploads for research papers
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime
from pathlib import Path
import mimetypes

from auth_middleware import get_current_user, AuthUser

router = APIRouter(prefix="/api/media", tags=["media"])

# Configuration for file uploads
UPLOAD_DIR = "uploads/figures"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB limit
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'}
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}


def _ensure_upload_directory():
    """
    Ensure upload directory exists
    Creates the directory if it doesn't exist
    """
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def _validate_image_file(file: UploadFile) -> bool:
    """
    Validate uploaded image file
    
    Checks:
    - File size (max 5MB)
    - MIME type (only image formats)
    - File extension
    
    Args:
        file: Uploaded file object
        
    Returns:
        True if valid, raises HTTPException if invalid
    """
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds limit. Maximum allowed: 5MB, Uploaded: {file.size / 1024 / 1024:.1f}MB"
        )
    
    # Check MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: JPEG, PNG, GIF, WebP, SVG"
        )
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    return True


@router.post("/upload-figure")
async def upload_figure(
    file: UploadFile = File(..., description="Image file for figure (JPEG, PNG, GIF, WebP, or SVG)"),
    caption: str = "", 
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Upload figure/image for research paper
    
    **Authentication Required**: User must be logged in
    
    **Parameters**:
    - file: Image file (JPEG, PNG, GIF, WebP, or SVG)
    - caption: Optional figure caption/title
    
    **Validation**:
    - Maximum file size: 5MB
    - Allowed formats: JPEG, PNG, GIF, WebP, SVG
    
    **Returns**:
    JSON object with:
    - file_id: Unique identifier for the uploaded file
    - filename: Original filename
    - url: URL to access the uploaded file
    - caption: Figure caption
    - upload_time: Timestamp of upload
    
    **Usage in Editor**:
    Use the returned `file_id` to embed the figure in your document.
    The figure will be automatically numbered (Figure 1, Figure 2, etc.)
    and included in the list of figures when exported to APA format.
    
    **Example Response**:
    ```json
    {
        "file_id": "fig_550e8400-e29b-41d4-a716-446655440000",
        "filename": "experimental_setup.png",
        "url": "/uploads/figures/fig_550e8400-e29b-41d4-a716-446655440000.png",
        "caption": "Experimental Setup",
        "upload_time": "2025-12-26T10:30:00Z"
    }
    ```
    """
    try:
        # Ensure upload directory exists
        _ensure_upload_directory()
        
        # Validate file
        _validate_image_file(file)
        
        # Generate unique file ID
        file_id = f"fig_{str(uuid.uuid4())}"
        
        # Get original file extension
        original_ext = Path(file.filename).suffix.lower()
        
        # Create new filename with user_id and timestamp for organization
        saved_filename = f"{file_id}{original_ext}"
        file_path = os.path.join(UPLOAD_DIR, saved_filename)
        
        # Read and save file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Return metadata
        return JSONResponse(
            status_code=201,
            content={
                "file_id": file_id,
                "filename": file.filename,
                "saved_filename": saved_filename,
                "url": f"/uploads/figures/{saved_filename}",
                "caption": caption or "",
                "upload_time": datetime.utcnow().isoformat() + "Z",
                "size_bytes": len(contents),
                "mime_type": file.content_type
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )


@router.delete("/delete-figure/{file_id}")
async def delete_figure(
    file_id: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Delete uploaded figure by file ID
    
    **Authentication Required**: User must be logged in
    
    **Parameters**:
    - file_id: Unique file ID returned from upload endpoint
    
    **Returns**:
    Success message confirming deletion
    """
    try:
        # Ensure upload directory exists
        _ensure_upload_directory()
        
        # Find and delete file
        # Search for file matching the file_id pattern
        for filename in os.listdir(UPLOAD_DIR):
            if filename.startswith(file_id):
                file_path = os.path.join(UPLOAD_DIR, filename)
                os.remove(file_path)
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "Figure deleted successfully",
                        "file_id": file_id
                    }
                )
        
        raise HTTPException(
            status_code=404,
            detail=f"Figure with ID {file_id} not found"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file: {str(e)}"
        )
