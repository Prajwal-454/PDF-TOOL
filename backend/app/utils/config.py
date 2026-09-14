from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "PDF Platform API"
    max_upload_mb: int = 50
    storage_dir: Path = Path(__file__).resolve().parent.parent.parent / "storage"
    tmp_dir: Path = Path(__file__).resolve().parent.parent.parent / "storage" / "tmp"
    output_dir: Path = Path(__file__).resolve().parent.parent.parent / "storage" / "output"
    # Comma-separated origins, e.g. CORS_ORIGINS=https://a.vercel.app,http://localhost:3000
    # Use "*" to allow all origins (handy for Vercel preview URLs on the free tier;
    # safe here because the API uses no cookies/auth). Defaults to "*" so a fresh
    # Render deploy works with any Vercel frontend until you lock it down.
    cors_origins: str = "*"
    # Ephemeral-disk hygiene (free tier has no persistent disk): files/jobs older
    # than these TTLs are safe to delete. Cleanup runs on startup + on demand
    # via POST /api/maintenance/cleanup.
    file_ttl_hours: int = 24
    job_ttl_hours: int = 24
    max_jobs: int = 1000
    # Free-tier abuse guards: cap render cost per job (OOM protection).
    max_image_pages: int = 80
    max_image_dpi: int = 200
    max_split_parts: int = 50
    # Groq (free tier) for real AI summarize/ask. Empty key = offline fallback.
    # Get a free key at https://console.groq.com -> GROQ_API_KEY=gsk_...
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # Cap PDF text sent to Groq per request (chars). Keeps free-tier fast/cheap.
    groq_max_chars: int = 15000
    groq_timeout_s: float = 30.0
    # Phase 2+: switch to Postgres / Redis / Celery
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
