from fastapi import APIRouter, UploadFile, File, HTTPException
from ..utils.config import settings
from ..utils.files import validate_pdf_bytes, secure_file_id, _strip_leading_junk
from ..utils import storage
from ..services.pdf_service import get_page_count

router = APIRouter(prefix="/api/files", tags=["files"])

IMAGE_MAGIC = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png"}
OFFICE_EXTS = {".docx", ".xlsx", ".pptx", ".html", ".htm", ".txt", ".csv", ".jpeg", ".jpg", ".png", ".pdf"}
# Extensions that map to a normalized suffix / kind without magic check.
OFFICE_SUFFIX_MAP = {
    ".docx": (".docx", "office"),
    ".xlsx": (".xlsx", "office"),
    ".pptx": (".pptx", "office"),
    ".html": (".html", "office"),
    ".htm": (".html", "office"),
    ".txt": (".txt", "office"),
    ".csv": (".csv", "office"),
}

FREE_INTAKE_MSG = "Free intake accepts PDF, JPG/JPEG, PNG, DOCX, XLSX, PPTX, HTML, TXT/CSV (50 MB max)."


def _detect_kind(head: bytes, orig: str) -> tuple[str, str] | None:
    """Return (suffix, kind) or None if unsupported. Magic first, then extension."""
    stripped = _strip_leading_junk(head)
    if stripped.startswith(b"%PDF"):
        return ".pdf", "pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image"
    if head.startswith(b"\x89PNG"):
        return ".png", "image"
    ext = "." + orig.rsplit(".", 1)[-1] if "." in orig else ""
    if ext in OFFICE_SUFFIX_MAP:
        # .txt/.csv/.html/.docx/etc: accept by extension (content checked later by converter).
        # Empty files are rejected after write with a clear message.
        return OFFICE_SUFFIX_MAP[ext]
    return None


def _helpful_type_error(head: bytes, orig: str) -> str:
    if not head:
        return f"Empty file is not allowed. {FREE_INTAKE_MSG}"
    stripped = _strip_leading_junk(head)
    h = head[:32]
    ext = "." + orig.rsplit(".", 1)[-1] if "." in orig else "(no extension)"
    # File claims to be PDF/JPG/PNG by extension but magic does not match -> corrupted/renamed.
    if ext == ".pdf":
        return f"File ends with .pdf but is not a valid PDF (bad magic bytes). Re-export it as PDF. {FREE_INTAKE_MSG}"
    if ext in (".jpg", ".jpeg"):
        # Actual bytes may be gif/webp/etc. renamed to .jpg -> give specific hint below if known.
        pass
    if ext in (".jpg", ".jpeg", ".png") and not (h.startswith(b"\xff\xd8\xff") or h.startswith(b"\x89PNG")):
        # Fall through to magic-specific hints; generic fallback at end covers the rest.
        pass
    # Common image formats the free engine does not convert.
    if h.startswith((b"GIF87a", b"GIF89a")):
        return f"GIF images are not supported. Convert to JPG/PNG first. {FREE_INTAKE_MSG}"
    if h.startswith(b"BM"):
        return f"BMP images are not supported. Convert to JPG/PNG first. {FREE_INTAKE_MSG}"
    if h.startswith((b"II*\x00", b"MM\x00*")):
        return f"TIFF images are not supported. Convert to JPG/PNG first. {FREE_INTAKE_MSG}"
    if h.startswith(b"RIFF") and b"WEBP" in h:
        return f"WEBP images are not supported. Convert to JPG/PNG first. {FREE_INTAKE_MSG}"
    if h[4:12] == b"ftypheic" or h[4:12] == b"ftypheix" or h[4:11] == b"ftypmif":
        return f"HEIC photos (iPhone) are not supported. Export as JPG first. {FREE_INTAKE_MSG}"
    if stripped.startswith(b"<") or stripped.lower().startswith(b"<!doctype html"):
        # HTML pasted/saved without .html extension
        return f"HTML content needs a .html extension to be accepted. {FREE_INTAKE_MSG}"
    if h.startswith(b"PK\x03\x04"):
        # ZIP container: could be docx/xlsx/pptx with wrong extension, or zip/odt/etc.
        ext = "." + orig.rsplit(".", 1)[-1] if "." in orig else "(no extension)"
        if ext in (".doc", ".xls", ".ppt"):
            return f"Legacy {ext} is not supported. Re-save as DOCX/XLSX/PPTX in Word/Excel first. {FREE_INTAKE_MSG}"
        if ext in (".odt", ".ods", ".odp"):
            return f"OpenDocument ({ext}) is not supported. Export as DOCX/XLSX/PPTX first. {FREE_INTAKE_MSG}"
        if ext == ".zip":
            return f"ZIP archives are not supported. Extract and upload the document inside. {FREE_INTAKE_MSG}"
        return f"Unsupported file type '{ext}'. {FREE_INTAKE_MSG}"
    ext = "." + orig.rsplit(".", 1)[-1] if "." in orig else "(no extension)"
    if ext in (".doc", ".xls", ".ppt"):
        return f"Legacy {ext} is not supported. Re-save as DOCX/XLSX/PPTX first. {FREE_INTAKE_MSG}"
    if ext in (".gif", ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif", ".avif", ".svg"):
        return f"Image type {ext} is not supported. Convert to JPG/PNG first. {FREE_INTAKE_MSG}"
    return f"Unsupported file type '{ext}'. {FREE_INTAKE_MSG}"


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    storage.ensure_dirs()
    head = await file.read(32)
    await file.seek(0)
    file_id = secure_file_id(".pdf")
    dest = storage.tmp_path(file_id)
    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
            out.write(chunk)

    err = validate_pdf_bytes(head, size, settings.max_upload_mb)
    if err:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, err)

    try:
        pages = get_page_count(dest)
    except Exception:
        # Allow encrypted PDFs (unlock tool handles them); reject truly broken files
        try:
            from pypdf import PdfReader as _R
            if _R(str(dest)).is_encrypted:
                return {"file_id": file_id, "original_name": file.filename or "upload.pdf",
                        "size": size, "pages": 0, "kind": "pdf", "encrypted": True}
        except Exception:
            pass
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Uploaded file is corrupted or not a readable PDF.")

    return {"file_id": file_id, "original_name": file.filename or "upload.pdf",
            "size": size, "pages": pages, "kind": "pdf"}


@router.post("/upload-any")
async def upload_any(file: UploadFile = File(...)):
    """Free multi-format intake: PDF, JPG/PNG (magic-checked), Office/TXT/HTML (extension + size checked)."""
    storage.ensure_dirs()
    head = await file.read(32)
    await file.seek(0)
    orig = (file.filename or "upload").lower().strip()
    detected = _detect_kind(head, orig)
    if detected is None:
        raise HTTPException(400, _helpful_type_error(head, orig))
    suffix, kind = detected
    # Normalize jpeg -> jpg so downstream image handling sees one suffix.
    if suffix == ".jpeg":
        suffix = ".jpg"
    file_id = secure_file_id(suffix)
    dest = storage.tmp_path(file_id)
    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
            out.write(chunk)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Empty file is not allowed. {FREE_INTAKE_MSG}")
    pages = 0
    if kind == "pdf":
        try:
            pages = get_page_count(dest)
        except Exception:
            # Allow encrypted PDFs (unlock tool handles them)
            try:
                from pypdf import PdfReader as _R
                if _R(str(dest)).is_encrypted:
                    return {"file_id": file_id, "original_name": file.filename or "upload",
                            "size": size, "pages": 0, "kind": "pdf", "encrypted": True}
            except Exception:
                pass
            dest.unlink(missing_ok=True)
            raise HTTPException(400, "Uploaded file is corrupted or not a readable PDF.")
    return {"file_id": file_id, "original_name": file.filename or "upload",
            "size": size, "pages": pages, "kind": kind}
