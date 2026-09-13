from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "PDF Platform API"
    max_upload_mb: int = 50
    storage_dir: Path = Path(__file__).resolve().parent.parent.parent / "storage"
    tmp_dir: Path = Path(__file__).resolve().parent.parent.parent / "storage" / "tmp"
    output_dir: Path = Path(__file__).resolve().parent.parent.parent / "storage" / "output"
    cors_origins: list[str] = ["http://localhost:3000"]
    # Phase 2+: switch to Postgres / Redis / Celery
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
