from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from ..workers.job_store import create_job, get_job
from ..workers import tasks
from ..utils import storage

router = APIRouter(prefix="/api", tags=["merge"])


class MergeRequest(BaseModel):
    file_ids: list[str] = Field(min_length=2, max_length=20)


@router.post("/merge", status_code=202)
def start_merge(body: MergeRequest, bg: BackgroundTasks):
    # Verify all inputs exist before queueing (fail fast)
    for fid in body.file_ids:
        if not storage.tmp_path(fid).exists():
            raise HTTPException(400, f"Unknown or expired file_id: {fid}")
    job = create_job(tool="merge", input_files=body.file_ids)
    bg.add_task(tasks.run_merge_job, job["id"], body.file_ids)
    return {"job_id": job["id"], "status": job["status"]}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job
