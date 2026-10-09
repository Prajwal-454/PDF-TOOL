"""Ops endpoints for the free/ephemeral tier: storage + job hygiene.

POST /api/maintenance/cleanup  -> delete tmp/output files older than FILE_TTL_HOURS
                                  + prune jobs older than JOB_TTL_HOURS.
GET  /api/maintenance/stats    -> storage usage + job count (for dashboards).
No auth: all data here is ephemeral by design (see DEPLOY.md).
"""

from fastapi import APIRouter
from ..utils import storage
from ..utils.config import settings
from ..workers import job_store

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.get("/stats")
def stats():
    return {
        "storage": storage.storage_stats(),
        "jobs": job_store.job_count(),
        "ttl": {"files_hours": settings.file_ttl_hours, "jobs_hours": settings.job_ttl_hours},
        "limits": {
            "max_upload_mb": settings.max_upload_mb,
            "max_image_pages": settings.max_image_pages,
            "max_image_dpi": settings.max_image_dpi,
            "max_split_parts": settings.max_split_parts,
        },
    }


@router.post("/cleanup")
def cleanup():
    storage.ensure_dirs()
    files = storage.cleanup_old_files()
    jobs = job_store.prune_old()
    return {"files": files, "jobs_pruned": jobs}
