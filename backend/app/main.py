"""
LearnerOS — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    health,
    auth,
    admin,
    curriculum,
    insights,
    institutes,
    teacher_applications,
    test,
    tutor,
    teacher_dashboard,
)
from app.database import close_driver

# Resolve animation assets path: main.py → app/ → backend/ → project root
ANIMATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "animations"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize connections
    print(f"🚀 LearnerOS Backend starting up (env: {settings.ENVIRONMENT})")
    yield
    # Shutdown: close connections
    close_driver()
    print("👋 LearnerOS Backend shutting down")


app = FastAPI(
    title="LearnerOS API",
    version="0.1.0",
    description="Adaptive learning platform backend",
    lifespan=lifespan,
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)

# Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(curriculum.router)
app.include_router(insights.router)
app.include_router(institutes.router)
app.include_router(teacher_applications.router)
app.include_router(test.router)
app.include_router(tutor.router)
app.include_router(teacher_dashboard.router)

# Serve animation HTML files as static assets
if ANIMATIONS_DIR.is_dir() and not settings.ANIMATIONS_R2_PUBLIC_BASE_URL:
    app.mount("/api/animations", StaticFiles(directory=str(ANIMATIONS_DIR), html=True), name="animations")
elif settings.ANIMATIONS_R2_PUBLIC_BASE_URL:
    _ANIMATIONS_R2_BASE = settings.ANIMATIONS_R2_PUBLIC_BASE_URL.rstrip("/")

    @app.get("/api/animations/{asset_path:path}", include_in_schema=False)
    async def animation_from_r2(asset_path: str):
        safe_parts = [p for p in asset_path.split("/") if p and p not in {".", ".."}]
        if not safe_parts:
            raise HTTPException(status_code=404, detail="Animation not found")
        return RedirectResponse(url=f"{_ANIMATIONS_R2_BASE}/{'/'.join(safe_parts)}", status_code=307)
