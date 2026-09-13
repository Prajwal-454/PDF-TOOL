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

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Failed to fetch` / CORS error in browser console | `CORS_ORIGINS` missing the exact Vercel URL (no trailing slash) |
| First tool run slow (~60s), then fast | Render cold start — normal on free tier |
| Old download links 404 | Ephemeral disk restarted — re-run the tool |
| Vercel build can't reach API | `NEXT_PUBLIC_API_BASE` unset at build time — set it, then **Redeploy** |
| Render build fails on `pydantic-core` / Rust / `maturin` | Wrong Python version — keep `runtime.txt` on 3.12.x (3.14 has no wheels for pinned deps) |
