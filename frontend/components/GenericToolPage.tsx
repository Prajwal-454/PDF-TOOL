"use client";
import { useState } from "react";
import { useDropzone } from "react-dropzone";
import ToolHeader from "@/components/ToolHeader";
import ProcessingProgress from "@/components/ProcessingProgress";
import { uploadPdf, uploadAny, startTool, pollJob, downloadUrl, downloadBundleUrl, API_BASE, isLocalApiDefault, type UploadedFile, type Job } from "@/lib/api";
import { pushHistory } from "@/lib/history";
import type { Tool } from "@/lib/tools";

function dropzoneAccept(tool: Tool): Record<string, string[]> | undefined {
  // Map tool.accept to a react-dropzone accept object for the file picker.
  // Server (upload-any / upload) remains the source of truth.
  if (tool.slug === "sign") return undefined; // needs PDF + PNG together
  const a = (tool.accept || "").toLowerCase();
  if (a.includes("application/pdf") && !a.includes(".docx")) return { "application/pdf": [".pdf"] };
  const mimeFor: Record<string, string> = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".csv": "text/csv",
  };
  const exts = tool.accept.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  if (exts.length === 0 || (exts.length === 1 && exts[0] === "image/*")) {
    return { "image/jpeg": [".jpg", ".jpeg"], "image/png": [".png"] };
  }
  const out: Record<string, string[]> = {};
  for (const e of exts) {
    const mime = mimeFor[e] || "application/octet-stream";
    (out[mime] ||= []).push(e);
  }
  return Object.keys(out).length ? out : undefined;
}

function toPayload(tool: Tool, files: UploadedFile[], params: Record<string, string>): any {
  const p: any = { ...params };
  if (tool.slug === "merge" || tool.slug === "images-to-pdf") return { ...p, file_ids: files.map((f) => f.file_id) };
  if (tool.slug === "compare") return { file_a: files[0]?.file_id, file_b: files[1]?.file_id };
  if (tool.slug === "sign") {
    const pdf = files.find((f) => f.file_id.endsWith(".pdf"));
    const img = files.find((f) => !f.file_id.endsWith(".pdf"));
    return { ...p, file_id: pdf?.file_id, image_id: img?.file_id, page: Number(p.page || 1), x: Number(p.x || 100), y: Number(p.y || 100) };
  }
  if (tool.slug === "reorder") return { order: String(p.order || "").split(",").map((x: string) => Number(x.trim())).filter(Boolean) };
  if (tool.slug === "redact") return { phrases: String(p.phrases || "").split(",").map((x: string) => x.trim()).filter(Boolean) };
  if (tool.slug === "rotate" || tool.slug === "crop" || tool.slug === "page") { /* fallthrough */ }
  if (tool.slug === "rotate") return { file_id: files[0]?.file_id, pages: p.pages || undefined, angle: Number(p.angle || 90) };
  if (tool.slug === "crop") return { file_id: files[0]?.file_id, margin_pct: Number(p.margin_pct || 10) };
  return { ...p, file_id: files[0]?.file_id };
}

export default function GenericToolPage({ tool }: { tool: Tool }) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [params, setParams] = useState<Record<string, string>>(() =>
    Object.fromEntries(tool.fields.map((f) => [f.key, f.defaultValue ?? ""]))
  );
  const [status, setStatus] = useState("idle");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: dropzoneAccept(tool),
    multiple: Boolean(tool.multi),
    onDropRejected: (rejections) => {
      const names = rejections.map((r) => r.file.name).join(", ") || "file";
      setError(
        `${names} was blocked by the file picker. This tool accepts ${tool.accept} (free intake: PDF/JPG/PNG/DOCX/XLSX/PPTX/HTML/TXT/CSV, 50 MB max). If your file looks valid, try renaming it to the right extension and re-upload.`
      );
    },
    onDrop: async (dropped: File[]) => {
      setError(null);
      setStatus("uploading");
      try {
        for (const f of dropped) {
          // Client pre-check: give an instant message for obviously wrong extensions
          // instead of waiting for the server round-trip.
          const lower = f.name.toLowerCase();
          const isPdfTool = !tool.anyUpload && tool.slug !== "sign";
          if (isPdfTool && !(/\.pdf$/i.test(lower))) {
            // Still try server (it handles edge cases), but warn if server rejects.
          }
          let up;
          if (tool.anyUpload || tool.slug === "sign") {
            up = await uploadAny(f);
          } else {
            // PDF-only tools: try strict PDF endpoint first. Only fall back to
            // the multi-format endpoint on a 400 (bad magic); network/CORS
            // errors must surface as-is so "all files fail" is diagnosable.
            try {
              up = await uploadPdf(f);
            } catch (e1: any) {
              const m1 = String(e1?.message || "");
              if (m1.includes("HTTP 400")) {
                up = await uploadAny(f);
              } else {
                throw e1;
              }
            }
          }
          setFiles((prev) => [...prev, up]);
        }
      } catch (e: any) {
        const detail = e?.message ? String(e.message) : "";
        setError(detail
          ? `${detail} — Free intake: PDF/JPG/JPEG/PNG/DOCX/XLSX/PPTX/HTML/TXT/CSV (50 MB max). API: ${API_BASE}`
          : `Upload failed. Free intake: PDF/JPG/JPEG/PNG/DOCX/XLSX/PPTX/HTML/TXT/CSV (50 MB max). API: ${API_BASE}. If every file fails, the frontend is likely pointing at localhost (NEXT_PUBLIC_API_BASE unset at build time) or the Render backend is asleep/down — open ${API_BASE}/api/health.`);
      } finally {
        setStatus("idle");
      }
    }
  });

  async function run() {
    setError(null);
    setJob(null);
    const need = tool.slug === "merge" ? 2 : tool.slug === "compare" ? 2 : tool.slug === "images-to-pdf" ? 1 : 1;
    if (files.length < need) {
      setError(tool.slug === "merge" ? "Upload at least 2 PDFs." : "Upload a file first.");
      return;
    }
    // required text params
    for (const f of tool.fields) {
      if ((tool.slug === "split" && f.key === "ranges") || (tool.slug === "rotate" && f.key === "pages")) continue;
      if ((f.type === "text" || f.type === "question") && !String(params[f.key] || "").trim() && !["source"].includes(f.key)) {
        if (tool.slug === "translate" && f.key === "source") continue;
        setError(`"${f.label}" is required.`);
        return;
      }
    }
    setStatus("queued");
    try {
      const payload = toPayload(tool, files, params);
      const { job_id } = await startTool(tool.slug, payload);
      const done = await pollJob(job_id, (j) => setStatus(j.status));
      setJob(done);
      setStatus("idle");
      pushHistory({ at: new Date().toISOString(), tool: tool.slug, file: files[0]?.original_name ?? "", status: done.status, output: done.output_file });
      if (done.status === "failed") setError(done.error || "Processing failed.");
    } catch (e: any) {
      setStatus("failed");
      setError(e?.message || "Request failed.");
    }
  }

  const res: any = job?.result ?? {};
  const showJson = ["summarize", "ask", "form-detect", "translate", "compare"].includes(tool.slug);
  const multiFiles: string[] = Array.isArray(res.parts) ? res.parts : Array.isArray(res.images) ? res.images : [];
  const bundleDir = multiFiles.length > 0 && multiFiles[0].includes("/") ? multiFiles[0].split("/")[0] : null;

  function fmtBytes(n: any): string {
    const v = Number(n);
    if (!Number.isFinite(v)) return "";
    if (v < 1024) return `${v} B`;
    if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
    return `${(v / (1024 * 1024)).toFixed(2)} MB`;
  }

  return (
    <div>
      <ToolHeader title={tool.name} desc={tool.desc} />
      {isLocalApiDefault && typeof window !== "undefined" && window.location.hostname !== "localhost" && (
        <p role="alert" className="mb-4 rounded-xl border border-danger bg-card px-4 py-3 text-sm text-danger">
          Backend not configured: this site was built without NEXT_PUBLIC_API_BASE, so uploads go to {API_BASE} and fail.
          Set NEXT_PUBLIC_API_BASE to your Render URL in Vercel → Redeploy.
        </p>
      )}
      {tool.hint && <p className="mb-4 rounded-xl border border-line bg-primaryLight px-4 py-3 text-sm">{tool.hint}</p>}
      <div {...getRootProps()} className={`cursor-pointer rounded-2xl border-2 border-dashed bg-card p-8 text-center ${isDragActive ? "border-primary bg-primaryLight" : "border-line"}`}>
        <input {...getInputProps()} aria-label={`Upload for ${tool.name}`} />
        <p className="font-medium">+ Add {tool.multi ? "files" : "file"}</p>
        <p className="mt-1 text-sm text-muted">{tool.accept} · drag &amp; drop</p>
      </div>
      {files.length > 0 && (
        <ul className="mt-3 space-y-2">
          {files.map((f) => (
            <li key={f.file_id} className="flex items-center justify-between rounded-xl border border-line bg-card px-4 py-2 text-sm">
              <span>{f.original_name} {(f.pages ? `· ${f.pages}p` : "")}</span>
              <button className="text-danger" onClick={() => setFiles((p) => p.filter((x) => x.file_id !== f.file_id))}>Remove</button>
            </li>
          ))}
        </ul>
      )}
      {tool.fields.length > 0 && (
        <div className="mt-4 grid gap-3 rounded-2xl border border-line bg-card p-4">
          {tool.fields.map((f) =>
            f.type === "select" ? (
              <label key={f.key} className="text-sm">{f.label}
                <select className="mt-1 w-full rounded-lg border border-line p-2" value={params[f.key] ?? ""} onChange={(e) => setParams({ ...params, [f.key]: e.target.value })}>
                  {f.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </label>
            ) : (
              <label key={f.key} className="text-sm">{f.label}
                <input className="mt-1 w-full rounded-lg border border-line p-2" placeholder={f.placeholder} inputMode={f.type === "number" ? "numeric" : undefined}
                  value={params[f.key] ?? ""} onChange={(e) => setParams({ ...params, [f.key]: e.target.value })} />
              </label>
            )
          )}
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-3">
        <button onClick={run} disabled={status === "queued" || status === "processing" || status === "uploading"} className="rounded-xl bg-primary px-5 py-3 text-white disabled:opacity-40">
          Run {tool.name}
        </button>
        {(files.length > 0 || job) && (
          <button onClick={() => { setFiles([]); setJob(null); setError(null); setStatus("idle"); }} className="rounded-xl border border-line bg-card px-5 py-3">
            Reset
          </button>
        )}
      </div>
      <ProcessingProgress status={status} />
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
      {job?.status === "completed" && job.output_file && (
        <div className="mt-6 rounded-2xl border border-line bg-card p-5">
          <p className="font-medium text-success">Done.</p>
          {res.saved_pct !== undefined && <p className="text-sm text-muted">Saved {res.saved_pct}% ({fmtBytes(res.original)} → {fmtBytes(res.size)}).</p>}
          {res.size !== undefined && res.saved_pct === undefined && <p className="text-sm text-muted">Output size: {fmtBytes(res.size)}{res.pages ? ` · ${res.pages} page(s)` : ""}.</p>}
          {res.redactions !== undefined && <p className="text-sm text-muted">{res.redactions} redactions applied. Verification leftover: {res.verify_leftover}.</p>}
          {res.count !== undefined && multiFiles.length > 0 && <p className="text-sm text-muted">{res.count} file(s) produced.</p>}
          <div className="mt-4 flex flex-wrap gap-3">
            <a href={downloadUrl(job.output_file)} className="inline-block rounded-xl bg-primary px-5 py-3 text-white" download>Download result</a>
            {bundleDir && (
              <a href={downloadBundleUrl(bundleDir)} className="inline-block rounded-xl border border-line bg-card px-5 py-3" download>Download all (.zip)</a>
            )}
          </div>
          {multiFiles.length > 1 && (
            <ul className="mt-4 space-y-1 text-sm">
              {multiFiles.map((n: string) => (
                <li key={n}>
                  <a className="text-primary" href={downloadUrl(n)} download>{n.split("/").pop()}</a>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-muted">Links expire after ~24h on the free tier (ephemeral disk). Re-run the tool if a link 404s.</p>
        </div>
      )}
      {job?.status === "completed" && showJson && (
        <div className="mt-6 rounded-2xl border border-line bg-card p-5">
          <p className="font-medium text-success">Result (free offline engine{res.provider ? ` · ${res.provider}` : ""})</p>
          {res.summary && <pre className="mt-2 whitespace-pre-wrap text-sm">{res.summary}</pre>}
          {res.answer && <pre className="mt-2 whitespace-pre-wrap text-sm">{res.answer}</pre>}
          {res.sources?.length > 0 && <p className="mt-2 text-sm text-muted">Sources: pages {res.sources.join(", ")}</p>}
          {res.diff_count !== undefined && <p className="mt-2 text-sm">{res.diff_count} different page(s). {res.different_pages.map((d: any) => `p.${d.page}`).join(", ")}</p>}
          {res.fields && <pre className="mt-2 whitespace-pre-wrap text-sm">{JSON.stringify(res.fields.slice(0, 20), null, 2)}{res.count > 20 ? `\n… +${res.count - 20} more` : ""}</pre>}
          {res.segments && <p className="mt-2 text-sm text-muted">{res.segments.length} page(s) processed → {res.target}. {res.note ?? ""}</p>}
        </div>
      )}
    </div>
  );
}
