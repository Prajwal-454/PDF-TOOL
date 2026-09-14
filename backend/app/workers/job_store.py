"""In-memory job store for Phase 1 dev.

Phase 2: replace with Postgres (jobs table) + Redis queue + Celery worker.
Interface (create/get/update) is kept stable so routers don't change.
"""

from datetime import datetime, timezone
import uuid
from threading import Lock

_jobs: dict[str, dict] = {}
_lock = Lock()
MAX_JOBS_FALLBACK = 1000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cap() -> int:
    try:
        from ..utils.config import settings
        return max(100, int(settings.max_jobs))
    except Exception:
        return MAX_JOBS_FALLBACK


def create_job(tool: str, input_files: list[str]) -> dict:
    job_id = uuid.uuid4().hex
    job = {
        "id": job_id,
        "tool": tool,
        "status": "queued",  # queued | processing | completed | failed
        "input_files": input_files,
        "output_file": None,
        "error": None,
        "created_at": _now(),
        "finished_at": None,
    }
    with _lock:
        # Evict oldest by created_at so unbounded growth can't OOM the free tier.
        if len(_jobs) >= _cap():
            oldest = sorted(_jobs.values(), key=lambda j: j.get("created_at", ""))[: len(_jobs) - _cap() + 1]
            for j in oldest:
                _jobs.pop(j["id"], None)
        _jobs[job_id] = job
    return job


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def job_count() -> int:
    with _lock:
        return len(_jobs)


def update_job(job_id: str, **fields) -> dict | None:
    with _lock:
        if job_id not in _jobs:
            return None
        if fields.get("status") in ("completed", "failed") and not fields.get("finished_at"):
            fields["finished_at"] = _now()
        _jobs[job_id].update(fields)
        return dict(_jobs[job_id])


def prune_old(max_age_hours: float | None = None) -> int:
    """Drop jobs older than TTL (by created_at). Returns evicted count."""
    try:
        from ..utils.config import settings
        ttl = settings.job_ttl_hours if max_age_hours is None else max_age_hours
    except Exception:
        ttl = 24
    try:
        cutoff = datetime.now(timezone.utc).timestamp() - ttl * 3600
    except Exception:
        return 0
    evicted = 0
    with _lock:
        for jid, job in list(_jobs.items()):
            try:
                ts = datetime.fromisoformat(str(job.get("created_at", ""))).timestamp()
            except Exception:
                continue
            if ts < cutoff:
                _jobs.pop(jid, None)
                evicted += 1
    return evicted
