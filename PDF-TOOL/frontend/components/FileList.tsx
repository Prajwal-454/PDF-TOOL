"use client";
import type { UploadedFile } from "@/lib/api";

export default function FileList({
  files,
  onMove,
  onRemove
}: {
  files: UploadedFile[];
  onMove: (from: number, to: number) => void;
  onRemove: (i: number) => void;
}) {
  if (!files.length) return null;
  return (
    <ul className="mt-4 space-y-2">
      {files.map((f, i) => (
        <li key={f.file_id} className="flex items-center justify-between rounded-xl border border-line bg-card px-4 py-3">
          <div>
            <p className="text-sm font-medium">{f.original_name}</p>
            <p className="text-xs text-muted">
              {(f.size / 1024).toFixed(1)} KB · {f.pages} page(s)
            </p>
          </div>
          <div className="flex gap-2">
            <button disabled={i === 0} onClick={() => onMove(i, i - 1)} aria-label={`Move ${f.original_name} up`} className="rounded border border-line px-2 py-1 text-sm disabled:opacity-40">↑</button>
            <button disabled={i === files.length - 1} onClick={() => onMove(i, i + 1)} aria-label={`Move ${f.original_name} down`} className="rounded border border-line px-2 py-1 text-sm disabled:opacity-40">↓</button>
            <button onClick={() => onRemove(i)} className="rounded border border-line px-2 py-1 text-sm text-danger">Remove</button>
          </div>
        </li>
      ))}
    </ul>
  );
}
