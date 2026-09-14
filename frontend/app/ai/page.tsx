"use client";
import { useState } from "react";
import { useDropzone } from "react-dropzone";
import ToolHeader from "@/components/ToolHeader";
import { uploadPdf, startTool, pollJob } from "@/lib/api";

export default function AIWorkspace() {
  const [fileId, setFileId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [q, setQ] = useState("What are the key points?");
  const [out, setOut] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getRootProps, getInputProps } = useDropzone({
    multiple: false,
    accept: { "application/pdf": [".pdf"] },
    onDrop: async ([f]) => {
      if (!f) return;
      setBusy(true);
      setError(null);
      try {
        const up = await uploadPdf(f);
        setFileId(up.file_id);
        setName(up.original_name);
      } catch (e: any) {
        setError(e?.message || "Upload failed. Only valid PDFs under 50 MB are accepted.");
      } finally {
        setBusy(false);
      }
    }
  });

  async function run(tool: string, payload: any) {
    if (!fileId) return;
    setBusy(true);
    setOut(null);
    try {
      const { job_id } = await startTool(tool, { file_id: fileId, ...payload });
      const done = await pollJob(job_id);
      setOut(done.result);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <ToolHeader title="AI PDF Workspace" desc="Free offline AI: summarize, ask, markdown, form fields, translate shell. No API keys." />
      <div {...getRootProps()} className="cursor-pointer rounded-2xl border-2 border-dashed border-line bg-card p-8 text-center">
        <input {...getInputProps()} aria-label="Upload PDF for AI" />
        <p className="font-medium">{fileId ? `${name} ✓` : "Drop PDF here"}</p>
        <p className="text-sm text-muted">{busy ? "Working…" : "Ask anything about your document"}</p>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
      <div className="mt-4 flex flex-wrap gap-2">
        <button disabled={!fileId || busy} onClick={() => run("summarize", { mode: "key-points" })} className="rounded-xl bg-primary px-4 py-2 text-white disabled:opacity-40">Summarize</button>
        <button disabled={!fileId || busy} onClick={() => run("markdown", {})} className="rounded-xl border border-line bg-card px-4 py-2">→ Markdown</button>
        <button disabled={!fileId || busy} onClick={() => run("form-detect", {})} className="rounded-xl border border-line bg-card px-4 py-2">Detect fields</button>
      </div>
      <div className="mt-4 flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="What are the three main conclusions?" className="flex-1 rounded-xl border border-line p-3" aria-label="Ask about document" />
        <button disabled={!fileId || busy} onClick={() => run("ask", { question: q })} className="rounded-xl bg-primary px-4 py-2 text-white disabled:opacity-40">Ask</button>
      </div>
      {out && (
        <div className="mt-6 rounded-2xl border border-line bg-card p-5">
          <pre className="whitespace-pre-wrap text-sm">{out.summary ?? out.answer ?? JSON.stringify(out, null, 2)}</pre>
          {out.sources?.length > 0 && <p className="mt-2 text-sm text-muted">Sources: pages {out.sources.join(", ")} · {out.provider}</p>}
        </div>
      )}
    </div>
  );
}
