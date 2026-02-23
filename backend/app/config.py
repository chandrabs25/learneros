"""
LearnerOS — Configuration (loaded from environment variables)
"""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    ENVIRONMENT: str = "development"

   

    # Neo4j
    NEO4J_URI:str = "neo4j+s://763a18af.databases.neo4j.io"
    NEO4J_USER:str = "neo4j"
    NEO4J_PASSWORD:str = "xLLVtnzQuAJREwmkuEWVAvIcdBbIKEqJbHdDgUfvDG0"

    # LLM
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    # Fireworks-hosted Kimi 2.5 (OpenAI-compatible API)
    FIREWORKS_API_KEY: str = ""
    FIREWORKS_API_KEY_EMBEDDINGS: str = Field(
        default="",
        validation_alias=AliasChoices("FIREWORKS_API_KEY_EMBEDDINGS", "FIREWORKS_API_KEY_embeddings"),
    )
    FIREWORKS_BASE_URL: str = "https://api.fireworks.ai/inference/v1"
    FIREWORKS_MODEL: str = "accounts/fireworks/models/kimi-k2p5"
    FIREWORKS_EMBEDDING_MODEL: str = "fireworks/qwen3-embedding-8b"
    # MLflow GenAI tracing (optional)
    MLFLOW_ENABLE_TRACING: bool = False
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"
    MLFLOW_EXPERIMENT_NAME: str = "ai-tutor"

    # Firebase (path to service account JSON)
    FIREBASE_SERVICE_ACCOUNT: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    # Frontend URL (for CORS)
    FRONTEND_URL: str = "http://localhost:3000"

    # Optional public R2 base URL for animation assets.
    # Example: https://pub-xxxxxxxx.r2.dev/animations
    ANIMATIONS_R2_PUBLIC_BASE_URL: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins."""
        origins = [
            "http://localhost:3000",
            "http://localhost:3001",
        ]
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"



settings = Settings()
