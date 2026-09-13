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

_origins = settings.cors_origin_list
# Starlette rejects allow_credentials=True together with allow_origins=["*"],
# and browsers reject it too. The API uses no cookies, so credentials are
# unnecessary when wildcard is configured (covers Vercel preview URLs).
_allow_credentials = not ("*" in _origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
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
