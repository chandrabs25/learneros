"""
LearnerOS — Configuration (loaded from environment variables)
"""

from urllib.parse import urlparse

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    ENVIRONMENT: str = "development"

   

    # Neo4j
    NEO4J_URI: str = ""
    NEO4J_USER: str = ""
    NEO4J_PASSWORD: str = ""

    # LLM
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
    GEN_CACHE_TTL_SECONDS: int = 604800
    GEN_CACHE_MAX_ENTRIES: int = 5000
    GEN_PROMPT_VERSION: str = "v2"
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    # Firebase (path to service account JSON)
    FIREBASE_SERVICE_ACCOUNT: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    # Frontend URL (for CORS)
    FRONTEND_URL: str = "http://localhost:3000"
    # Optional comma-separated extra origins for CORS.
    # Example: "https://www.learneros.me,https://learneros.me"
    CORS_ORIGINS: str = ""

    # Optional public R2 base URL for animation assets.
    # Example: https://pub-xxxxxxxx.r2.dev/animations
    ANIMATIONS_R2_PUBLIC_BASE_URL: str = ""
    # Public chapter-cover assets settings.
    # Deterministic cover URL format:
    # {CHAPTER_COVERS_ASSETS_DOMAIN}/{CHAPTER_COVERS_PREFIX}/grade-{grade}/{subject-slug}/chapter-{NN}-{title-slug}.jpg
    CHAPTER_COVERS_ASSETS_DOMAIN: str = "https://assets.learneros.me"
    CHAPTER_COVERS_PREFIX: str = "chapter-covers"

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins."""
        base_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
        ]
        if self.FRONTEND_URL:
            base_origins.append(self.FRONTEND_URL.strip())
        if self.CORS_ORIGINS:
            base_origins.extend([o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()])

        normalized: list[str] = []
        seen: set[str] = set()

        def add_origin(origin: str) -> None:
            if not origin:
                return
            if origin in seen:
                return
            seen.add(origin)
            normalized.append(origin)

        for origin in base_origins:
            add_origin(origin)
            parsed = urlparse(origin)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                host = parsed.hostname or ""
                if host.startswith("www."):
                    alt_host = host[4:]
                    if alt_host:
                        add_origin(f"{parsed.scheme}://{alt_host}")
                else:
                    add_origin(f"{parsed.scheme}://www.{host}")

        return normalized

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"



settings = Settings()
