"""
Health check endpoint — used by Fly.io for health monitoring
and by the frontend to verify backend connectivity.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "ai-tutor-backend",
        "version": "0.1.0",
    }
