"""Background processing dispatcher. FastAPI BackgroundTasks in dev, Celery in prod.

Every tool funnels through run_tool_job(tool, job_id, payload) so routers stay thin
and the future Celery worker can import this same function.
"""

from pathlib import Path
from .job_store import update_job
from ..services import pdf_service, conversion_service, ocr_service, ai_service, workflow_service
from ..utils import storage
from ..utils.config import settings
from ..utils.files import safe_output_name


def _out() -> tuple[str, Path]:
    name = safe_output_name()
    return name, storage.output_path(name)


def run_merge_job(job_id: str, file_ids: list[str]) -> None:
    run_tool_job("merge", job_id, {"file_ids": file_ids})


def run_tool_job(tool: str, job_id: str, payload: dict) -> None:
    update_job(job_id, status="processing")
    try:
        result = _dispatch(tool, payload)
        update_job(job_id, status="completed", output_file=result.get("output_file"),
                   result=result)
    except Exception as exc:
        update_job(job_id, status="failed", error=str(exc))


def _dispatch(tool: str, p: dict) -> dict:
    tmp = storage.tmp_path
    if tool == "merge":
        paths = [tmp(fid) for fid in p["file_ids"]]
        name, out = _out()
        r = pdf_service.merge_pdfs(paths, out)
        return {**r, "output_file": name}
    if tool == "split":
        # Use a unique subdir per job so concurrent splits never overwrite
        # each other (previously all wrote split-1.pdf to output/ top-level).
        parts_req = [p.strip() for p in str(p.get("ranges", "")).split(",")] if p.get("ranges") else None
        if parts_req is not None and len([x for x in parts_req if x]) > settings.max_split_parts:
            raise ValueError(f"Too many split parts (max {settings.max_split_parts}).")
        dirname = job_tmp_dir()
        r = pdf_service.split_pdf(tmp(p["file_id"]), settings.output_dir / dirname, p.get("ranges"))
        namespaced = [f"{dirname}/{n}" for n in r["parts"]]
        return {**r, "parts": namespaced, "output_file": namespaced[0]}
    if tool == "remove-pages":
        name, out = _out()
        r = pdf_service.remove_pages(tmp(p["file_id"]), out, p["pages"])
        return {**r, "output_file": name}
    if tool == "extract-pages":
        name, out = _out()
        r = pdf_service.extract_pages(tmp(p["file_id"]), out, p["pages"])
        return {**r, "output_file": name}
    if tool == "rotate":
        name, out = _out()
        r = pdf_service.rotate_pages(tmp(p["file_id"]), out, p.get("pages"), int(p.get("angle", 90)))
        return {**r, "output_file": name}
    if tool == "reorder":
        name, out = _out()
        r = pdf_service.reorder_pages(tmp(p["file_id"]), out, [int(x) for x in p["order"]])
        return {**r, "output_file": name}
    if tool == "compress":
        name, out = _out()
        r = pdf_service.compress_pdf(tmp(p["file_id"]), out, p.get("level", "recommended"))
        return {**r, "output_file": name}
    if tool == "repair":
        name, out = _out()
        r = pdf_service.repair_pdf(tmp(p["file_id"]), out)
        return {**r, "output_file": name}
    if tool == "watermark":
        name, out = _out()
        r = pdf_service.watermark_pdf(tmp(p["file_id"]), out, p.get("text", "CONFIDENTIAL"))
        return {**r, "output_file": name}
    if tool == "page-numbers":
        name, out = _out()
        r = pdf_service.add_page_numbers(tmp(p["file_id"]), out)
        return {**r, "output_file": name}
    if tool == "crop":
        name, out = _out()
        r = pdf_service.crop_pdf(tmp(p["file_id"]), out, float(p.get("margin_pct", 10)))
        return {**r, "output_file": name}
    if tool == "protect":
        name, out = _out()
        r = pdf_service.protect_pdf(tmp(p["file_id"]), out, p.get("password", ""))
        return {**r, "output_file": name}
    if tool == "unlock":
        name, out = _out()
        r = pdf_service.unlock_pdf(tmp(p["file_id"]), out, p.get("password", ""))
        return {**r, "output_file": name}
    if tool == "redact":
        name, out = _out()
        r = pdf_service.redact_pdf(tmp(p["file_id"]), out, p.get("phrases", []))
        return {**r, "output_file": name}
    if tool == "compare":
        r = pdf_service.compare_pdfs(tmp(p["file_a"]), tmp(p["file_b"]))
        return {**r, "output_file": None}
    if tool == "pdf-to-images":
        # pdf_to_images writes page-*.png into a unique per-job subdir.
        # Namespace output_file (and images) with the subdir so /api/download
        # can resolve it; previously the bare "page-1.png" 404'd because the
        # file lived at output/<uuid>/page-1.png but download looked top-level.
        dpi = int(p.get("dpi", 150))
        if dpi < 72 or dpi > settings.max_image_dpi:
            raise ValueError(f"DPI must be 72–{settings.max_image_dpi} on the free tier.")
        try:
            pages = pdf_service.get_page_count(tmp(p["file_id"]))
        except Exception:
            pages = 0
        if pages and pages > settings.max_image_pages:
            raise ValueError(
                f"PDF has {pages} pages (max {settings.max_image_pages} for image export "
                "on the free tier). Split it first.")
        dirname = job_tmp_dir()
        r = pdf_service.pdf_to_images(tmp(p["file_id"]), settings.output_dir / dirname, dpi, p.get("fmt", "png"))
        namespaced = [f"{dirname}/{n}" for n in r["images"]]
        return {**r, "images": namespaced, "output_file": namespaced[0]}
    if tool == "images-to-pdf":
        paths = [tmp(fid) for fid in p["file_ids"]]
        name, out = _out()
        r = pdf_service.images_to_pdf(paths, out)
        return {**r, "output_file": name}
    if tool == "sign":
        name, out = _out()
        try:
            page = int(p.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        try:
            x = float(p.get("x", 100) or 100)
        except (TypeError, ValueError):
            x = 100.0
        try:
            y = float(p.get("y", 100) or 100)
        except (TypeError, ValueError):
            y = 100.0
        r = pdf_service.place_signature(tmp(p["file_id"]), out, tmp(p["image_id"]), page, x, y)
        return {**r, "output_file": name}
    if tool == "ocr":
        name, out = _out()
        r = ocr_service.run_ocr(tmp(p["file_id"]), out, p.get("language", "eng"))
        return {**r, "output_file": name}
    if tool == "office-to-pdf":
        name, out = _out()
        kind = str(p.get("kind", "docx")).lower()
        if kind == "csv":
            kind = "txt"  # CSV is plain text for the free engine
        src = tmp(p["file_id"])
        fn = {"docx": conversion_service.docx_to_pdf, "xlsx": conversion_service.xlsx_to_pdf,
              "pptx": conversion_service.pptx_to_pdf, "html": conversion_service.html_to_pdf,
              "htm": conversion_service.html_to_pdf,
              "txt": conversion_service.txt_to_pdf}[kind]
        r = fn(src, out)
        return {**r, "output_file": name}
    if tool == "pdf-to-office":
        kind = p.get("kind", "docx")
        src = tmp(p["file_id"])
        ext = {"docx": ".docx", "xlsx": ".xlsx", "pptx": ".pptx", "md": ".md"}[kind]
        dest = storage.output_path(safe_output_name().replace(".pdf", ext))
        fn = {"docx": conversion_service.pdf_to_docx, "xlsx": conversion_service.pdf_to_xlsx,
              "pptx": conversion_service.pdf_to_pptx, "md": conversion_service.pdf_to_markdown_file}[kind]
        r = fn(src, dest)
        return {**r, "output_file": dest.name}
    if tool == "summarize":
        r = ai_service.summarize_pdf(tmp(p["file_id"]), p.get("mode", "key-points"))
        return {**r, "output_file": None}
    if tool == "ask":
        r = ai_service.ask_pdf(tmp(p["file_id"]), p.get("question", ""))
        return {**r, "output_file": None}
    if tool == "markdown":
        dest = storage.output_path(safe_output_name().replace(".pdf", ".md"))
        r = conversion_service.pdf_to_markdown_file(tmp(p["file_id"]), dest)
        return {**r, "output_file": dest.name}
    if tool == "form-detect":
        r = ai_service.detect_form_fields(tmp(p["file_id"]))
        return {**r, "output_file": None}
    if tool == "translate":
        r = ai_service.translate_pages(tmp(p["file_id"]), p.get("target", "es"), p.get("source", "auto"))
        return {**r, "output_file": None}
    if tool == "workflow":
        r = workflow_service.run_workflow(p.get("steps", []), p["file_id"])
        return {**r, "output_file": r["output_file"]}
    raise ValueError(f"Unknown tool: {tool}")


def job_tmp_dir(_p: dict | None = None) -> str:
    import uuid
    d = settings.output_dir / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=True)
    return d.name
