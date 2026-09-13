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
    # Phase 2+: switch to Postgres / Redis / Celery
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
