# PDF Platform — complete, 100% free (no paid services)

Modular iLovePDF-style platform. See `FREE_STACK.md` for the free-only guarantee.

## What is built (26 tools + workspace + workflows + history)
- Organize: merge, split, remove-pages, extract-pages, rotate, reorder
- Convert to PDF: images-to-pdf (JPG/PNG→PDF), office-to-pdf (DOCX/XLSX/PPTX/HTML/TXT→PDF)
- Convert from PDF: pdf-to-office (→DOCX/XLSX/PPTX/MD), pdf-to-images (→PNG/JPG)
- Edit: watermark, page-numbers, crop
- Security: protect, unlock (password-gated), redact (permanent + verified), compare, sign (PNG placement; PAdES later)
- Optimize: compress (shows % saved), repair (best-effort), ocr (Tesseract/OCRmyPDF when installed, graceful otherwise)
- AI (offline free): summarize, ask (both with page citations), markdown, form-detect, translate shell (Ollama/LibreTranslate upgrade, honestly labeled)
- Workflows: `/workflows` chains ocr→compress→watermark→protect→download as one job
- AI workspace: `/ai` — upload once, summarize/ask/markdown/fields
- History: `/history` — localStorage, no account needed

## Run locally (free)
Backend:
```powershell
cd pdf-platform/backend
pip install -r requirements.txt
python -m pytest tests/ -v
uvicorn app.main:app --reload --port 8000
```
Frontend:
```powershell
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
