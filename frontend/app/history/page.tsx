"use client";
import { useEffect, useState } from "react";
import ToolHeader from "@/components/ToolHeader";
import { readHistory, type HistoryEntry } from "@/lib/history";
import { downloadUrl } from "@/lib/api";

export default function History() {
  const [rows, setRows] = useState<HistoryEntry[]>([]);
  useEffect(() => setRows(readHistory()), []);
  return (
    <div>
      <ToolHeader title="History" desc="Recent jobs on this device (localStorage, free — no account needed)." />
      {rows.length === 0 && <p className="text-sm text-muted">No jobs yet. Run any tool first.</p>}
      <ul className="space-y-2">
        {rows.map((r, i) => (
          <li key={i} className="flex items-center justify-between rounded-xl border border-line bg-card px-4 py-3 text-sm">
            <div>
              <p className="font-medium">{r.file || "(file)"} · {r.tool}</p>
              <p className="text-xs text-muted">{new Date(r.at).toLocaleString()} · {r.status}</p>
            </div>
            {r.output && <a className="text-primary" href={downloadUrl(r.output)} download>Download</a>}
          </li>
        ))}
      </ul>
    </div>
  );
}
