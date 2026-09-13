"""Sequential workflow runner — reuses the same free services as single tools."""

from pathlib import Path
from . import pdf_service, ocr_service
from ..utils import storage
from ..utils.files import safe_output_name


def run_workflow(steps: list[dict], start_file: str) -> dict:
    """steps: [{'op': 'ocr'|'compress'|'watermark'|'protect'|'page-numbers'|'rotate', 'params': {...}}].
    Threads a single PDF through each step. Returns final output info."""
    cur = storage.tmp_path(start_file)
    if not cur.exists():
        raise ValueError("Starting file not found or expired.")
    trace = []
    for s in steps:
        op = s.get("op")
        params = s.get("params", {})
        out_name = safe_output_name()
        out = storage.output_path(out_name)
        if op == "ocr":
            r = ocr_service.run_ocr(cur if cur.suffix == ".pdf" else cur, out, params.get("language", "eng"))
            cur = out
        elif op == "compress":
            r = pdf_service.compress_pdf(cur, out, params.get("level", "recommended"))
            cur = out
        elif op == "watermark":
            r = pdf_service.watermark_pdf(cur, out, params.get("text", "CONFIDENTIAL"))
            cur = out
        elif op == "protect":
            r = pdf_service.protect_pdf(cur, out, params.get("password", ""))
            cur = out
        elif op == "page-numbers":
            r = pdf_service.add_page_numbers(cur, out)
            cur = out
        elif op == "rotate":
            r = pdf_service.rotate_pages(cur, out, None, int(params.get("angle", 90)))
            cur = out
        else:
            raise ValueError(f"Unknown workflow op: {op}")
        trace.append({"op": op, "result": r})
    return {"output_file": cur.name, "steps": trace, "size": cur.stat().st_size}
