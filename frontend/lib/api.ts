export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

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
  const res = await fetch(`${API_BASE}/api/files/upload`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadAny(file: File): Promise<UploadedFile> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/api/files/upload-any`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startMerge(file_ids: string[]): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/api/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startTool(tool: string, payload: any): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/api/tools/${tool}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJob(job_id: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/jobs/${job_id}`);
  if (!res.ok) throw new Error("Job not found");
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
