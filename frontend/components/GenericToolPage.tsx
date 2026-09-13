"use client";
import { useState } from "react";
import { useDropzone } from "react-dropzone";
import ToolHeader from "@/components/ToolHeader";
import ProcessingProgress from "@/components/ProcessingProgress";
import { uploadPdf, uploadAny, startTool, pollJob, downloadUrl, type UploadedFile, type Job } from "@/lib/api";
import { pushHistory } from "@/lib/history";
import type { Tool } from "@/lib/tools";

function toPayload(tool: Tool, files: UploadedFile[], params: Record<string, string>): any {
  const p: any = { ...params };
  if (tool.slug === "merge" || tool.slug === "images-to-pdf") return { ...p, file_ids: files.map((f) => f.file_id) };
  if (tool.slug === "compare") return { file_a: files[0]?.file_id, file_b: files[1]?.file_id };
  if (tool.slug === "sign") {
    const pdf = files.find((f) => f.file_id.endsWith(".pdf"));
    const img = files.find((f) => !f.file_id.endsWith(".pdf"));
    return { ...p, file_id: pdf?.file_id, image_id: img?.file_id, page: Number(p.page || 1) };
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
    accept: tool.slug === "merge" ? { "application/pdf": [".pdf"] } : undefined,
    multiple: Boolean(tool.multi),
    onDrop: async (dropped: File[]) => {
      setError(null);
      setStatus("uploading");
      try {
        for (const f of dropped) {
          const up = tool.anyUpload || tool.slug === "sign" ? await uploadAny(f) : await uploadPdf(f).catch(async () => await uploadAny(f));
          setFiles((prev) => [...prev, up]);
        }
      } catch {
        setError("Upload failed. Check file type (free intake: PDF/JPG/PNG/DOCX/XLSX/PPTX/HTML/TXT, 50 MB max).");
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
      setError("Request failed. The backend message (if any) is shown in History/logs.");
    }
  }

  const res: any = job?.result ?? {};
  const showJson = ["summarize", "ask", "form-detect", "translate", "compare"].includes(tool.slug);

  return (
    <div>
      <ToolHeader title={tool.name} desc={tool.desc} />
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
      <button onClick={run} disabled={status === "queued" || status === "processing" || status === "uploading"} className="mt-4 rounded-xl bg-primary px-5 py-3 text-white disabled:opacity-40">
        Run {tool.name}
      </button>
      <ProcessingProgress status={status} />
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
      {job?.status === "completed" && job.output_file && (
        <div className="mt-6 rounded-2xl border border-line bg-card p-5">
          <p className="font-medium text-success">Done.</p>
          {res.saved_pct !== undefined && <p className="text-sm text-muted">Saved {res.saved_pct}% ({res.original} → {res.size} bytes).</p>}
          {res.redactions !== undefined && <p className="text-sm text-muted">{res.redactions} redactions applied. Verification leftover: {res.verify_leftover}.</p>}
          <a href={downloadUrl(job.output_file)} className="mt-4 inline-block rounded-xl bg-primary px-5 py-3 text-white" download>Download result</a>
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
