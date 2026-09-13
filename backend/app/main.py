from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .utils.config import settings
from .utils import storage
from .api import files, merge, download, tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_dirs()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router)
app.include_router(merge.router)
app.include_router(tools.router)
app.include_router(download.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/tools")
def list_tools():
    return {"tools": ["merge", "split", "remove-pages", "extract-pages", "rotate", "reorder",
                      "compress", "repair", "watermark", "page-numbers", "crop", "protect",
                      "unlock", "redact", "compare", "pdf-to-images", "images-to-pdf", "sign",
                      "ocr", "office-to-pdf", "pdf-to-office", "summarize", "ask", "markdown",
                      "form-detect", "translate", "workflow"]}
