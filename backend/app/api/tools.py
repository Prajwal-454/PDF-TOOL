"""Generic tool endpoint — one route for every tool, same job flow.

POST /api/tools/{tool}  {file_id | file_ids | ...params} -> 202 {job_id}
GET  /api/jobs/{job_id} (defined in merge.py, shared store)
Tools: split, remove-pages, extract-pages, rotate, reorder, compress, repair,
watermark, page-numbers, crop, protect, unlock, redact, compare, pdf-to-images,
images-to-pdf, sign, ocr, office-to-pdf, pdf-to-office, summarize, ask,
markdown, form-detect, translate, workflow
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from ..workers.job_store import create_job, get_job
from ..workers import tasks
from ..utils import storage

router = APIRouter(prefix="/api/tools", tags=["tools"])

TOOLS_SINGLE_FILE = {"split", "remove-pages", "extract-pages", "rotate", "reorder",
                     "compress", "repair", "watermark", "page-numbers", "crop",
                     "protect", "unlock", "redact", "pdf-to-images", "ocr",
                     "office-to-pdf", "pdf-to-office", "summarize", "ask",
                     "markdown", "form-detect", "translate", "workflow"}


@router.post("/{tool}", status_code=202)
def start_tool(tool: str, payload: dict, bg: BackgroundTasks):
    if tool == "merge":
        file_ids = payload.get("file_ids", [])
        if len(file_ids) < 2:
            raise HTTPException(400, "Merge needs at least 2 files.")
        for fid in file_ids:
            if not storage.tmp_path(fid).exists():
                raise HTTPException(400, f"Unknown or expired file_id: {fid}")
        job = create_job(tool="merge", input_files=file_ids)
        bg.add_task(tasks.run_tool_job, "merge", job["id"], {"file_ids": file_ids})
        return {"job_id": job["id"], "status": job["status"]}

    if tool == "images-to-pdf":
        for fid in payload.get("file_ids", []):
            if not storage.tmp_path(fid).exists():
                raise HTTPException(400, f"Unknown file_id: {fid}")
        job = create_job(tool=tool, input_files=payload.get("file_ids", []))
        bg.add_task(tasks.run_tool_job, tool, job["id"], payload)
        return {"job_id": job["id"], "status": job["status"]}

    if tool == "compare":
        for k in ("file_a", "file_b"):
            if not payload.get(k) or not storage.tmp_path(payload[k]).exists():
                raise HTTPException(400, f"Missing or expired {k}.")
        job = create_job(tool=tool, input_files=[payload["file_a"], payload["file_b"]])
        bg.add_task(tasks.run_tool_job, tool, job["id"], payload)
        return {"job_id": job["id"], "status": job["status"]}

    if tool == "sign":
        if not payload.get("file_id") or not storage.tmp_path(payload["file_id"]).exists():
            raise HTTPException(400, "Missing PDF file_id.")
        if not payload.get("image_id") or not storage.tmp_path(payload["image_id"]).exists():
            raise HTTPException(400, "Missing signature image. Upload a PNG first.")
        job = create_job(tool=tool, input_files=[payload["file_id"]])
        bg.add_task(tasks.run_tool_job, tool, job["id"], payload)
        return {"job_id": job["id"], "status": job["status"]}

    if tool not in TOOLS_SINGLE_FILE:
        raise HTTPException(404, f"Unknown tool: {tool}")
    fid = payload.get("file_id")
    if not fid or not storage.tmp_path(fid).exists():
        raise HTTPException(400, "Missing or expired file_id. Upload first.")
    job = create_job(tool=tool, input_files=[fid])
    bg.add_task(tasks.run_tool_job, tool, job["id"], payload)
    return {"job_id": job["id"], "status": job["status"]}


@router.get("/ai/status")
def ai_status():
    from ..services import ai_service
    return ai_service.groq_status()


@router.get("/ocr/status")
def ocr_engine_status():
    from ..services import ocr_service
    return ocr_service.ocr_status()
