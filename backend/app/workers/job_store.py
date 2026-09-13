"""In-memory job store for Phase 1 dev.

Phase 2: replace with Postgres (jobs table) + Redis queue + Celery worker.
Interface (create/get/update) is kept stable so routers don't change.
"""

from datetime import datetime, timezone
import uuid
from threading import Lock

_jobs: dict[str, dict] = {}
_lock = Lock()


def create_job(tool: str, input_files: list[str]) -> dict:
    job_id = uuid.uuid4().hex
    job = {
        "id": job_id,
        "tool": tool,
        "status": "queued",  # queued | processing | completed | failed
        "input_files": input_files,
        "output_file": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _jobs[job_id] = job
    return job


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def update_job(job_id: str, **fields) -> dict | None:
    with _lock:
        if job_id not in _jobs:
            return None
        _jobs[job_id].update(fields)
        return dict(_jobs[job_id])
