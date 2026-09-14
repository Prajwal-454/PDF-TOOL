// NEXT_PUBLIC_API_BASE is baked at build time. Fall back to localhost for `npm run dev`.
// NOTE: an empty string (unset in Vercel) must also fall back — `??` alone would keep "".
const _raw = (process.env.NEXT_PUBLIC_API_BASE || "").trim();
export const API_BASE = _raw ? _raw.replace(/\/+$/, "") : "http://localhost:8000";

// True when the deployed frontend was built without NEXT_PUBLIC_API_BASE,
// i.e. it is still pointing at localhost and every tool call will fail with
// "Failed to fetch" in production. UI surfaces this as a config hint.
export const isLocalApiDefault =
  API_BASE === "http://localhost:8000" || API_BASE === "http://127.0.0.1:8000";

async function errText(res: Response, fallback: string): Promise<Error> {
  let body = "";
  try {
    body = (await res.text()).slice(0, 500);
  } catch {
    /* ignore */
  }
  // Surface backend detail (FastAPI {"detail": "..."}) instead of swallowing it.
  // Parse JSON detail so the UI shows a clean message, not raw {"detail":...}.
  let msg = body || `${res.status} ${res.statusText}`;
  try {
    const parsed = JSON.parse(body);
    if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
      msg = parsed.detail;
    } else if (Array.isArray(parsed?.detail) && parsed.detail[0]?.msg) {
      msg = parsed.detail.map((d: any) => d.msg).join("; ");
    }
  } catch {
    /* body was not JSON — keep raw text */
  }
  return new Error(`${fallback} (HTTP ${res.status}): ${msg}`);
}

async function safeFetch(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (e: any) {
    // Network/CORS failure: give an actionable message instead of bare "Failed to fetch".
    const hint = isLocalApiDefault
      ? " Backend not configured (NEXT_PUBLIC_API_BASE missing at build time)."
      : " Check backend URL and CORS_ORIGINS.";
    throw new Error(`Cannot reach API at ${API_BASE}.${hint}`);
  }
}

export type UploadedFile = {
  file_id: string;
  original_name: string;
  size: number;
  pages: number;
  kind?: string;
};

export type Job = {
  id: string;
  tool: string;
  status: "queued" | "processing" | "completed" | "failed";
  output_file: string | null;
  error: string | null;
  result?: any;
};

export async function uploadPdf(file: File): Promise<UploadedFile> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await safeFetch(`${API_BASE}/api/files/upload`, { method: "POST", body: fd });
  if (!res.ok) throw await errText(res, "Upload failed");
  return res.json();
}

export async function uploadAny(file: File): Promise<UploadedFile> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await safeFetch(`${API_BASE}/api/files/upload-any`, { method: "POST", body: fd });
  if (!res.ok) throw await errText(res, "Upload failed");
  return res.json();
}

export async function startMerge(file_ids: string[]): Promise<{ job_id: string }> {
  const res = await safeFetch(`${API_BASE}/api/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids })
  });
  if (!res.ok) throw await errText(res, "Could not start merge");
  return res.json();
}

export async function startTool(tool: string, payload: any): Promise<{ job_id: string }> {
  const res = await safeFetch(`${API_BASE}/api/tools/${tool}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw await errText(res, "Could not start tool");
  return res.json();
}

export async function getJob(job_id: string): Promise<Job> {
  const res = await safeFetch(`${API_BASE}/api/jobs/${job_id}`);
  if (!res.ok) throw await errText(res, "Job not found");
  return res.json();
}

export async function getHealth(): Promise<{ status: string }> {
  const res = await safeFetch(`${API_BASE}/api/health`);
  if (!res.ok) throw await errText(res, "Health check failed");
  return res.json();
}

export async function pollJob(job_id: string, onTick?: (j: Job) => void): Promise<Job> {
  for (let i = 0; i < 120; i++) {
    const job = await getJob(job_id);
    onTick?.(job);
    if (job.status === "completed" || job.status === "failed") return job;
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error("Timed out waiting for job.");
}

export function downloadUrl(file_name: string): string {
  return `${API_BASE}/api/download/${file_name}`;
}

export function downloadBundleUrl(subdir: string): string {
  return `${API_BASE}/api/download-bundle/${subdir}`;
}
