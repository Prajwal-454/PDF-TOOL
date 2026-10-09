# PDF Platform — complete, 100% free (no paid services)

Modular iLovePDF-style platform. See `FREE_STACK.md` for the free-only guarantee.
It runs entirely on your own PC as a desktop app — nothing is hosted online (see below).

## Desktop app (Windows) — install once, then just type `PDF-TOOL`

1. Double-click **`Install-PDF-TOOL.cmd`** (no admin rights needed). It installs the app to
   `%LOCALAPPDATA%\PDF-TOOL`, sets up Python packages, and adds the `PDF-TOOL` command,
   a Start-menu entry and a Desktop shortcut. Requires Python 3.10–3.13 (the installer tries
   `winget` to get it if it is missing).
2. Open it by typing **`PDF-TOOL`** in the Start menu, Win+R, `cmd` or PowerShell.
   It opens in its own window; closing the window stops the engine.
3. Your files/settings: `%LOCALAPPDATA%\PDF-TOOL\data` (put an optional free `GROQ_API_KEY`
   for AI summaries in `data\.env`). Everything stays on your PC.
4. Update: pull/copy new code, run the installer again (`-Rebuild` rebuilds the UI; needs Node.js).
   Remove: `Uninstall-PDF-TOOL.cmd`.

How it works: `npm run build:desktop` exports the Next.js UI as static files; the FastAPI engine
serves them and the API from one local address (`127.0.0.1:8765`); `desktop/launcher.py` starts
the engine and opens an Edge/Chrome app-mode window.

## What is built (26 tools + workspace + workflows + history)
- Organize: merge, split, remove-pages, extract-pages, rotate, reorder
- Convert to PDF: images-to-pdf (JPG/PNG→PDF), office-to-pdf (DOCX/XLSX/PPTX/HTML/TXT→PDF)
- Convert from PDF: pdf-to-office (→DOCX/XLSX/PPTX/MD), pdf-to-images (→PNG/JPG)
- Edit: watermark, page-numbers, crop
- Security: protect, unlock (password-gated), redact (permanent + verified), compare, sign (PNG placement; PAdES later)
- Optimize: compress (shows % saved), repair (best-effort), ocr (Tesseract/OCRmyPDF when installed, graceful otherwise)
- AI (Groq free-tier LLM when `GROQ_API_KEY` is set, offline fallback otherwise): summarize, ask (both with page citations), markdown, form-detect, translate shell (Ollama/LibreTranslate upgrade, honestly labeled)
- Workflows: `/workflows` chains ocr→repair→compress→crop→watermark→protect→download as one job
- AI workspace: `/ai` — upload once, summarize/ask/markdown/fields
- History: `/history` — localStorage, no account needed
- Multi-file results: split and PDF→images list every part + one-click **Download all (.zip)**
- Ephemeral hygiene: files/jobs auto-expire (~24h), cleanup on boot + `POST /api/maintenance/cleanup`

## Run locally (free)
Backend:
```powershell
cd pdf-platform/backend
pip install -r requirements.txt
python -m pytest tests/ -v
uvicorn app.main:app --reload --port 8000
```
Frontend:```powershell
cd ../frontend
npm install
npm run dev
# http://localhost:3000/tools/merge, /ai, /workflows, /history
```

## API shape (every tool same flow)
`POST /api/files/upload` (PDF) or `/api/files/upload-any` (PDF/JPG/PNG/DOCX/XLSX/PPTX/HTML/TXT)
→ `POST /api/tools/{tool}` → 202 `{job_id}` → `GET /api/jobs/{job_id}` → `GET /api/download/{file}`

## Honest limitations (by design)
- PDF→Office is best-effort; complex layouts won't round-trip perfectly.
- Repair is best-effort; badly damaged files may fail with a clear message.
- OCR without Tesseract installed reports engine status instead of paywalling.
- Translate without Ollama/LibreTranslate preserves layout and labels provider `offline-passthrough`.
