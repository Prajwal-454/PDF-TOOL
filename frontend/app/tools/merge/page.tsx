"use client";
import { useState } from "react";
import ToolHeader from "@/components/ToolHeader";
import FileUploader from "@/components/FileUploader";
import FileList from "@/components/FileList";
import ProcessingProgress from "@/components/ProcessingProgress";
import ResultCard from "@/components/ResultCard";
import { startMerge, getJob, type UploadedFile } from "@/lib/api";

export default function MergePage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [status, setStatus] = useState("idle");
  const [output, setOutput] = useState<string | null>(null);
  const [pages, setPages] = useState<number | undefined>(undefined);

  function move(from: number, to: number) {
    setFiles((prev) => {
      const next = [...prev];
      const [it] = next.splice(from, 1);
      next.splice(to, 0, it);
      return next;
    });
  }

  async function poll(job_id: string) {
    for (let i = 0; i < 60; i++) {
      const job = await getJob(job_id);
      if (job.status === "completed" && job.output_file) {
        setOutput(job.output_file);
        setPages(job.result?.pages);
        setStatus("idle");
        return;
      }
      if (job.status === "failed") {
        setStatus("failed");
        return;
      }
      setStatus(job.status);
      await new Promise((r) => setTimeout(r, 1000));
    }
    setStatus("failed");
  }

  async function onMerge() {
    if (files.length < 2) return;
    setStatus("queued");
    setOutput(null);
    try {
      const { job_id } = await startMerge(files.map((f) => f.file_id));
      await poll(job_id);
    } catch {
      setStatus("failed");
    }
  }

  return (
    <div>
      <ToolHeader title="Merge PDF" desc="Combine multiple PDF files into one file. Upload → reorder → merge → download." />
      <FileUploader onUploaded={(f) => setFiles((prev) => [...prev, f])} />
      <FileList files={files} onMove={move} onRemove={(i) => setFiles((p) => p.filter((_, x) => x !== i))} />
      <button
        onClick={onMerge}
        disabled={files.length < 2 || status === "processing" || status === "queued"}
        className="mt-4 rounded-xl bg-primary px-5 py-3 text-white disabled:opacity-40"
      >
        Merge PDFs
      </button>
      <ProcessingProgress status={status} />
      {output && <ResultCard outputFile={output} pages={pages} />}
    </div>
  );
}
