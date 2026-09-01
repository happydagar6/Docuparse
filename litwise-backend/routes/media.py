"""
Media Routes - Image and File Upload Handling
DISABLED: All data is stored in database only. Local file storage is not used.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from auth_middleware import get_current_user, AuthUser

router = APIRouter(prefix="/api/media", tags=["media"])

# Note: All data is stored in database only. Local file storage is disabled.


@router.post("/upload-figure")
async def upload_figure(
    file: UploadFile = File(..., description="Image file for figure (JPEG, PNG, GIF, WebP, or SVG)"),
    caption: str = "", 
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Upload figure/image for research paper
    
    **DISABLED**: File uploads are disabled. All data is stored in database only.
    This endpoint is currently not available.
    """
    raise HTTPException(
        status_code=503,
        detail="File upload functionality is disabled. All data is stored in database only."
    )


@router.delete("/delete-figure/{file_id}")
async def delete_figure(
    file_id: str,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Delete uploaded figure by file ID
    
    **DISABLED**: File deletion is disabled. All data is stored in database only.
    This endpoint is currently not available.
    """
    raise HTTPException(
        status_code=503,
        detail="File deletion functionality is disabled. All data is stored in database only."
    )
