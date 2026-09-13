from pathlib import Path
from .config import settings


def ensure_dirs() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.tmp_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)


def tmp_path(file_id: str) -> Path:
    return settings.tmp_dir / file_id


def output_path(file_name: str) -> Path:
    return settings.output_dir / file_name
