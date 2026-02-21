"""
AI Tutor — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from app.observability import setup_mlflow_tracing

# Resolve animation assets path: main.py → app/ → backend/ → project root
ANIMATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "animations"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize connections
    setup_mlflow_tracing()
    print(f"🚀 AI Tutor Backend starting up (env: {settings.ENVIRONMENT})")
    yield
    # Shutdown: close connections
    close_driver()
    print("👋 AI Tutor Backend shutting down")


app = FastAPI(
    title="AI Tutor API",
    version="0.1.0",
    description="Adaptive learning platform backend",
    lifespan=lifespan,
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
if ANIMATIONS_DIR.is_dir():
    app.mount("/api/animations", StaticFiles(directory=str(ANIMATIONS_DIR), html=True), name="animations")
