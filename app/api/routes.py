from fastapi import APIRouter, status
from app.config import settings

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """HTTP endpoint verifying service layer operations."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version
    }
