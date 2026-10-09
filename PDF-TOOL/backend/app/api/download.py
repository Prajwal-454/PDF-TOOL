from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from ..utils import storage
from ..utils.config import settings

router = APIRouter(prefix="/api", tags=["download"])

MEDIA = {".pdf": ("application/pdf", "result.pdf"), ".png": ("image/png", "page.png"),
         ".jpg": ("image/jpeg", "page.jpg"), ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "result.docx"),
         ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "result.xlsx"),
         ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "result.pptx"),
         ".md": ("text/markdown", "result.md")}


@router.get("/download/{file_name:path}")
def download_result(file_name: str):
    # Allow top-level ("abc.pdf") and one level of job subdir
    # ("<uuid>/page-1.png", "<uuid>/split-1.pdf") for split/pdf-to-images.
    # Reject traversal and absolute paths.
    if "\\" in file_name or ".." in file_name or file_name.startswith("/"):
        raise HTTPException(400, "Invalid file name.")
    parts = [p for p in file_name.split("/") if p not in ("", ".")]
    if len(parts) not in (1, 2) or any(p in ("", ".", "..") for p in parts):
        raise HTTPException(400, "Invalid file name.")
    import re
    if any(not re.fullmatch(r"[A-Za-z0-9._-]+", p) for p in parts):
        raise HTTPException(400, "Invalid file name.")
    path = storage.output_path(parts[0] if len(parts) == 1 else f"{parts[0]}/{parts[1]}")
    # Containment check: resolved path must stay under output_dir
    try:
        if not path.resolve().is_relative_to(settings.output_dir.resolve()):
            raise HTTPException(400, "Invalid file name.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid file name.")
    if not path.exists():
        raise HTTPException(404, "Result not found or expired.")
    media, dl = MEDIA.get(path.suffix.lower(), ("application/octet-stream", file_name))
    return FileResponse(str(path), media_type=media, filename=dl)


@router.get("/download-bundle/{subdir}")
def download_bundle(subdir: str):
    """Zip every file in a per-job output subdir (split / pdf-to-images).

    subdir is the bare uuid dir name, e.g. <uuid> from "<uuid>/page-1.png".
    """
    import io
    import re
    import zipfile
    if not re.fullmatch(r"[A-Za-z0-9_-]+", subdir):
        raise HTTPException(400, "Invalid bundle name.")
    folder = storage.output_path(subdir)
    try:
        if not folder.resolve().is_relative_to(settings.output_dir.resolve()):
            raise HTTPException(400, "Invalid bundle name.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid bundle name.")
    if not folder.is_dir():
        raise HTTPException(404, "Result not found or expired.")
    names = sorted(p.name for p in folder.iterdir() if p.is_file())
    if not names:
        raise HTTPException(404, "Result not found or expired.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in names:
            if not re.fullmatch(r"[A-Za-z0-9._-]+", n):
                continue
            zf.write(str(folder / n), arcname=n)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename={subdir}.zip"})
