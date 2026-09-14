from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .utils.config import settings
from .utils import storage
from .api import files, merge, download, tools, maintenance


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_dirs()
    # Best-effort hygiene on boot (ephemeral disk): never crash startup.
    try:
        storage.cleanup_old_files()
    except Exception:
        pass
    try:
        from .workers import job_store
        job_store.prune_old()
    except Exception:
        pass
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
app.include_router(maintenance.router)


@app.get("/api/health")
def health():
    # Keep {"status": "ok"} shape (frontend + Render depend on it) and add
    # cheap diagnostics. Individual counters are best-effort.
    try:
        store = storage.storage_stats()
    except Exception:
        store = {}
    try:
        from .workers import job_store
        jobs = job_store.job_count()
    except Exception:
        jobs = None
    try:
        from .services import ocr_service
        ocr = ocr_service.ocr_status()
    except Exception:
        ocr = {}
    return {"status": "ok", "storage": store, "jobs": jobs, "ocr": ocr}


@app.get("/api/tools")
def list_tools():
    return {"tools": ["merge", "split", "remove-pages", "extract-pages", "rotate", "reorder",
                      "compress", "repair", "watermark", "page-numbers", "crop", "protect",
                      "unlock", "redact", "compare", "pdf-to-images", "images-to-pdf", "sign",
                      "ocr", "office-to-pdf", "pdf-to-office", "summarize", "ask", "markdown",
                      "form-detect", "translate", "workflow"]}
