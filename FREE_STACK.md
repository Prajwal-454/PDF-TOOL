# 100% FREE Stack — no paid services, no API keys

Everything in this project runs free, offline-first. No OpenAI, no paid OCR, no paid hosting required.

## Backend (all free / open-source)
| Need | Free choice | License | Notes |
|---|---|---|---|
| API | FastAPI + Uvicorn | MIT/BSD | |
| PDF organize/edit/security | `pypdf` + `PyMuPDF` | BSD/AGPL | merge/split/remove/extract/rotate/reorder/crop/watermark/page-numbers/repair/redact/compare/sign |
| Images | `Pillow` | HPND | JPG/PNG ⇄ PDF, signature placement |
| Office → PDF | `python-docx` + `openpyxl` + `python-pptx` + `reportlab` | MIT/Apache/BSD | Pure-Python free engine. If free LibreOffice is installed, auto-upgrades to it |
| PDF → Office | PyMuPDF text/tables → docx/openpyxl/pptx writers | same | Best-effort; scanned PDFs need OCR first (UI says so) |
| HTML/TXT → PDF | `reportlab` sanitizer | BSD | No paid HTML renderer |
| OCR | `Tesseract` + `OCRmyPDF` (optional install, both free: Apache/GPL) | free | If missing, API still works: reports engine status + passes through searchable PDFs |
| AI summarize/ask | Groq LLM (`GROQ_API_KEY`, free tier) with offline extractive + TF-IDF fallback, page citations | — | Real answers when key set; zero keys still works |
| AI translate | Pluggable: `OLLAMA_URL` (free local LLM) or `LIBRETRANSLATE_URL` (free self-host) else honest offline passthrough preserving layout | — | Never pretends to translate; UI shows provider |
| Markdown/forms | PyMuPDF heuristics | — | Free |
| Jobs dev | FastAPI BackgroundTasks | — | Zero infra |
| Jobs prod | Celery + Redis + PostgreSQL (all free OSS) | Apache/BSD/PostgreSQL | docker-compose slots reserved |
| Storage dev | Local disk + TTL auto-cleanup (boot + POST /api/maintenance/cleanup) | — | Free tier ephemeral by design; UI warns links expire ~24h |
| Storage prod | MinIO (free S3-compatible, AGPL) or Cloudflare R2 free tier | — | Same S3 API |

## Frontend (all free)
Next.js + React + Tailwind + react-dropzone — MIT, no paid UI kits. History in localStorage (no paid auth/DB needed for v1).

## Run free locally
```powershell
cd pdf-platform/backend
pip install -r requirements.txt
python -m pytest tests/ -v
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
# http://localhost:3000  (26 tools + /ai + /workflows + /history)
```

## Optional free upgrades (still $0)
- OCR: install free Tesseract + `pip install ocrmypdf`
- Perfect Office rendering: install free LibreOffice (auto-detected via `soffice`)
- Real local MT/LLM: run free Ollama (`OLLAMA_URL=http://localhost:11434`) or self-host free LibreTranslate
- Free hosting: Vercel/Render free tier (frontend), Render/Railway free tier or Oracle Always-Free (API), Supabase free Postgres, Upstash free Redis

## What is intentionally NOT included
Paid LLM APIs, paid OCR SaaS, paid conversion SaaS, paid auth/billing — the architecture has provider interfaces so you can add them later, but v1 needs none of them.
