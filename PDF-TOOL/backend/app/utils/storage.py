from pathlib import Path
import time
from .config import settings


def ensure_dirs() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.tmp_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)


def tmp_path(file_id: str) -> Path:
    return settings.tmp_dir / file_id


def output_path(file_name: str) -> Path:
    return settings.output_dir / file_name


def storage_stats() -> dict:
    """Count files/bytes under tmp/ and output/ (best-effort, never raises)."""
    stats = {"tmp_files": 0, "tmp_bytes": 0, "output_files": 0, "output_bytes": 0}
    try:
        for p in settings.tmp_dir.rglob("*"):
            if p.is_file():
                stats["tmp_files"] += 1
                try:
                    stats["tmp_bytes"] += p.stat().st_size
                except OSError:
                    pass
        for p in settings.output_dir.rglob("*"):
            if p.is_file():
                stats["output_files"] += 1
                try:
                    stats["output_bytes"] += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return stats


def cleanup_old_files(max_age_hours: float | None = None) -> dict:
    """Delete tmp/output files older than TTL. Returns counts. Never raises."""
    ttl = max_age_hours if max_age_hours is not None else settings.file_ttl_hours
    cutoff = time.time() - ttl * 3600
    removed = {"tmp": 0, "output": 0, "bytes_freed": 0}
    for base, key in ((settings.tmp_dir, "tmp"), (settings.output_dir, "output")):
        try:
            if not base.exists():
                continue
            for p in sorted(base.rglob("*")):
                try:
                    if p.is_file() and p.stat().st_mtime < cutoff:
                        try:
                            removed["bytes_freed"] += p.stat().st_size
                        except OSError:
                            pass
                        p.unlink(missing_ok=True)
                        removed[key] += 1
                except OSError:
                    continue
            # remove newly-empty job subdirs (one level only, never base itself)
            for sub in sorted(base.iterdir()):
                try:
                    if sub.is_dir() and not any(sub.iterdir()):
                        sub.rmdir()
                except OSError:
                    continue
        except OSError:
            continue
    return removed
