"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { uploadPdf, type UploadedFile } from "@/lib/api";

export default function FileUploader({ onUploaded }: { onUploaded: (f: UploadedFile) => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onDrop = useCallback(
    async (files: File[]) => {
      setError(null);
      setBusy(true);
      try {
        for (const f of files) {
          const up = await uploadPdf(f);
          onUploaded(up);
        }
      } catch (e: any) {
        setError(e?.message || "Upload failed. Only valid PDFs under 50 MB are accepted.");
      } finally {
        setBusy(false);
      }
    },
    [onUploaded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed bg-card p-10 text-center ${
          isDragActive ? "border-primary bg-primaryLight" : "border-line"
        }`}
      >
        <input {...getInputProps()} aria-label="Upload PDF files" />
        <p className="font-medium">+ Add PDF files</p>
        <p className="mt-1 text-sm text-muted">{busy ? "Uploading…" : "Drag & drop your files here"}</p>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  );
}
