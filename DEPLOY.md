# Deploy — frontend on Vercel, backend on Render (both free)

Order matters: backend first, then frontend, then wire the URLs together.

## 1. Backend → Render (free web service)

Render reads `render.yaml` in this repo, so this is mostly clicks:

1. Push this repo to GitHub (done — Render deploys from git).
2. Render dashboard → **New → Blueprint** → select `Prajwal-454/PDF-TOOL`.
3. Name: `pdf-tool-api`, plan: **Free** → Apply. First build takes ~5–10 min
   (`pip install` + PyMuPDF wheels).
4. When live, copy the URL: `https://pdf-tool-api-xxxx.onrender.com`.
   Health check: open `https://<yours>/api/health` → `{"status":"ok"}`.

Notes:
- Start command binds `$PORT` automatically (see `render.yaml`).
- Free tier **sleeps after ~15 min idle** → first request takes ~30–60s (cold start).
  The frontend polling (`pollJob`, 1s interval) tolerates this; users just wait a bit.
- Disks are **ephemeral**: uploads/results vanish on restart/redeploy. History in the
  frontend keeps filenames but old download links expire — expected on free tier.

## 1b. Enable Groq AI (free tier, optional but recommended)

`summarize`/`ask` use Groq when `GROQ_API_KEY` is set, else offline fallback:

1. Get a free key: https://console.groq.com → API Keys → Create (`gsk_...`).
2. Render → your service → **Environment** → add:
   - `GROQ_API_KEY` = `gsk_...` (secret — never commit it)
   - `GROQ_MODEL` = `openai/gpt-oss-120b`
   - `GROQ_MAX_CHARS` = `15000`
   Saving restarts the service. `render.yaml` already declares these keys
   (`GROQ_API_KEY` with `sync: false` so Blueprint prompts for it).
3. Verify: open `https://<yours>/api/tools/ai/status` →
   `{"configured":true,"model":"openai/gpt-oss-120b",...}` means real LLM answers.
   `configured:false` means offline fallback (app still works).

## 2. Frontend → Vercel (free project)

1. Vercel dashboard → **Add New → Project** → import `Prajwal-454/PDF-TOOL`.
2. **Root Directory: `frontend`** (important — the Next.js app is not at repo root).
   Framework preset: Next.js (auto-detected). Leave build settings default.
3. **Environment Variables** → add:
   - `NEXT_PUBLIC_API_BASE` = `https://<your-render-service>.onrender.com`
   - (no trailing slash; `NEXT_PUBLIC_` bakes in at build time, so set before deploying)
4. Deploy → copy the URL: `https://<your-app>.vercel.app`.

## 3. Wire them together (CORS)

The API only accepts browsers from origins in `CORS_ORIGINS`:

1. Render → your service → **Environment** → set:
   `CORS_ORIGINS=https://<your-app>.vercel.app,http://localhost:3000`
   (keep localhost so local dev still works). Saving restarts the service.
2. Hard-refresh the Vercel site and run any tool end to end.

## 4. Later deploys

- `git push` → Render auto-redeploys backend, Vercel auto-redeploys frontend.
- If you change `NEXT_PUBLIC_API_BASE`, Vercel needs a **redeploy** (env is build-time).
- If you change `CORS_ORIGINS`, Render restarts automatically on save.

## 5. Verify (both local and live)

```powershell
# Local backends
.\scripts\verify-deploy.ps1 -ApiBase http://localhost:8000

# Live (Render + optional Vercel check)
$env:API_BASE = "https://<your-render-service>.onrender.com"
$env:FRONTEND_URL = "https://<your-app>.vercel.app"
.\scripts\verify-deploy.ps1
```

What it checks: `/api/health` (status + storage/jobs), `/api/tools` (26 tools),
`/api/maintenance/stats`, and a full upload → compress → job roundtrip.
First live run may take ~60s (Render cold start) — the script uses 60s timeouts.

Ephemeral-disk note: uploads/results auto-expire after `FILE_TTL_HOURS` (default 24h).
Cleanup runs on every boot plus on demand via `POST /api/maintenance/cleanup` —
no cron needed on the free tier. Old download links 404 after expiry; the UI says so.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Failed to fetch` / CORS error in browser console | `CORS_ORIGINS` missing the exact Vercel URL (no trailing slash) |
| First tool run slow (~60s), then fast | Render cold start — normal on free tier |
| Old download links 404 | Ephemeral disk restarted — re-run the tool |
| Vercel build can't reach API | `NEXT_PUBLIC_API_BASE` unset at build time — set it, then **Redeploy** |
| Render build fails on `pydantic-core` / Rust / `maturin` | Wrong Python version — keep `runtime.txt` on 3.12.x (3.14 has no wheels for pinned deps) |
| AI answers say `offline-extractive` / `offline-tfidf` | `GROQ_API_KEY` missing on Render — add it under Environment, then check `/api/tools/ai/status` shows `configured:true` |
