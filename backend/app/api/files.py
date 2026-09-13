from fastapi import APIRouter, UploadFile, File, HTTPException
from ..utils.config import settings
from ..utils.files import validate_pdf_bytes, secure_file_id
from ..utils import storage
from ..services.pdf_service import get_page_count

router = APIRouter(prefix="/api/files", tags=["files"])

IMAGE_MAGIC = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png"}
OFFICE_EXTS = {".docx", ".xlsx", ".pptx", ".html", ".htm", ".txt"}


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    storage.ensure_dirs()
    head = await file.read(8)
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
    head = await file.read(8)
    await file.seek(0)
    orig = (file.filename or "upload").lower()
    suffix = ".bin"
    kind = "other"
    if head.startswith(b"%PDF"):
        suffix, kind = ".pdf", "pdf"
    elif head.startswith(b"\xff\xd8\xff"):
        suffix, kind = ".jpg", "image"
    elif head.startswith(b"\x89PNG"):
        suffix, kind = ".png", "image"
    elif any(orig.endswith(e) for e in OFFICE_EXTS):
        suffix = "." + orig.rsplit(".", 1)[-1]
        kind = "office"
        if suffix == ".htm":
            suffix = ".html"
    else:
        raise HTTPException(400, "Unsupported file type. Free intake accepts PDF, JPG, PNG, DOCX, XLSX, PPTX, HTML, TXT.")
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
    pages = 0
    if kind == "pdf":
        try:
            pages = get_page_count(dest)
        except Exception:
            dest.unlink(missing_ok=True)
            raise HTTPException(400, "Corrupted PDF.")
    return {"file_id": file_id, "original_name": file.filename or "upload",
            "size": size, "pages": pages, "kind": kind}
