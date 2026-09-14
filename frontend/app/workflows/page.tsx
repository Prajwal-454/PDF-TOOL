"use client";
import { useState } from "react";
import { useDropzone } from "react-dropzone";
import ToolHeader from "@/components/ToolHeader";
import { uploadPdf, startTool, pollJob, downloadUrl, API_BASE } from "@/lib/api";

const OPS = ["ocr", "compress", "watermark", "page-numbers", "protect", "rotate", "repair", "crop"];

export default function Workflows() {
  const [fileId, setFileId] = useState<string | null>(null);
  const [steps, setSteps] = useState<any[]>([{ op: "compress", params: { level: "recommended" } }]);
  const [out, setOut] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getRootProps, getInputProps } = useDropzone({
    multiple: false,
    accept: { "application/pdf": [".pdf"] },
    onDrop: async ([f]) => {
      if (!f) return;
      setError(null);
      try {
        const up = await uploadPdf(f);
        setFileId(up.file_id);
      } catch (e: any) {
        const detail = e?.message ? String(e.message) : "";
        setError(detail
          ? `${detail} — API: ${API_BASE}`
          : `Upload failed. Only valid PDFs under 50 MB are accepted. API: ${API_BASE}. If every file fails, check NEXT_PUBLIC_API_BASE (Vercel redeploy needed) and ${API_BASE}/api/health.`);
      }
    }
  });

  return (
    <div>
      <ToolHeader title="Workflow builder" desc="Chain free operations: Upload → OCR → Repair → Compress → Crop → Watermark → Protect → Download." />
      <div {...getRootProps()} className="cursor-pointer rounded-2xl border-2 border-dashed border-line bg-card p-6 text-center">
        <input {...getInputProps()} aria-label="Upload PDF for workflow" />
        <p className="font-medium">{fileId ? "PDF ready ✓" : "Upload PDF"}</p>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
      <div className="mt-4 space-y-2">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-2 rounded-xl border border-line bg-card p-3">
            <span className="text-sm text-muted">{i + 1}.</span>
            <select value={s.op} onChange={(e) => setSteps((p) => p.map((x, j) => (j === i ? { ...x, op: e.target.value } : x)))} className="rounded-lg border border-line p-2 text-sm" aria-label={`Step ${i + 1} operation`}>
              {OPS.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
            {(s.op === "watermark" || s.op === "protect") && (
              <input placeholder={s.op === "watermark" ? "Text" : "Password"} className="rounded-lg border border-line p-2 text-sm"
                value={s.params.text ?? s.params.password ?? ""} onChange={(e) => setSteps((p) => p.map((x, j) => (j === i ? { ...x, params: s.op === "watermark" ? { text: e.target.value } : { password: e.target.value } } : x)))} />
            )}
            {s.op === "rotate" && (
              <select value={String(s.params.angle ?? 90)} onChange={(e) => setSteps((p) => p.map((x, j) => (j === i ? { ...x, params: { angle: Number(e.target.value) } } : x)))} className="rounded-lg border border-line p-2 text-sm" aria-label={`Step ${i + 1} angle`}>
                {[90, 180, 270].map((a) => <option key={a} value={a}>{a}°</option>)}
              </select>
            )}
            {s.op === "crop" && (
              <input placeholder="Margin % (1-39)" inputMode="numeric" className="w-36 rounded-lg border border-line p-2 text-sm"
                value={s.params.margin_pct ?? "10"} onChange={(e) => setSteps((p) => p.map((x, j) => (j === i ? { ...x, params: { margin_pct: e.target.value } } : x)))} aria-label={`Step ${i + 1} margin percent`} />
            )}
            {s.op === "compress" && (
              <select value={String(s.params.level ?? "recommended")} onChange={(e) => setSteps((p) => p.map((x, j) => (j === i ? { ...x, params: { level: e.target.value } } : x)))} className="rounded-lg border border-line p-2 text-sm" aria-label={`Step ${i + 1} level`}>
                {["low", "recommended", "extreme"].map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            )}
            <button className="ml-auto text-sm text-danger" onClick={() => setSteps((p) => p.filter((_, j) => j !== i))}>Remove</button>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button onClick={() => setSteps((p) => [...p, { op: "watermark", params: { text: "CONFIDENTIAL" } }])} className="rounded-xl border border-line bg-card px-4 py-2 text-sm">+ Add step</button>
        <button disabled={!fileId || busy} onClick={async () => {
          setBusy(true);
          setOut(null);
          try {
            const { job_id } = await startTool("workflow", { file_id: fileId, steps });
            const done = await pollJob(job_id);
            if (done.status === "completed") setOut(done.output_file);
          } finally {
            setBusy(false);
          }
        }} className="rounded-xl bg-primary px-4 py-2 text-sm text-white disabled:opacity-40">{busy ? "Running…" : "Run workflow"}</button>
      </div>
      {out && <a href={downloadUrl(out)} download className="mt-4 inline-block rounded-xl bg-primary px-5 py-3 text-white">Download result</a>}
      <p className="mt-4 text-sm text-muted">Preset: scanned doc → OCR → Compress → Watermark → Protect. All free, runs as one background job.</p>
    </div>
  );
}
