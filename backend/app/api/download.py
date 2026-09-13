from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..utils import storage

router = APIRouter(prefix="/api", tags=["download"])

MEDIA = {".pdf": ("application/pdf", "result.pdf"), ".png": ("image/png", "page.png"),
         ".jpg": ("image/jpeg", "page.jpg"), ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "result.docx"),
         ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "result.xlsx"),
         ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "result.pptx"),
         ".md": ("text/markdown", "result.md")}


@router.get("/download/{file_name}")
def download_result(file_name: str):
    if "/" in file_name or "\\" in file_name or ".." in file_name:
        raise HTTPException(400, "Invalid file name.")
    path = storage.output_path(file_name)
    if not path.exists():
        raise HTTPException(404, "Result not found or expired.")
    media, dl = MEDIA.get(path.suffix.lower(), ("application/octet-stream", file_name))
    return FileResponse(str(path), media_type=media, filename=dl)
