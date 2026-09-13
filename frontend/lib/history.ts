export type HistoryEntry = {
  at: string;
  tool: string;
  file: string;
  status: string;
  output?: string | null;
};

const KEY = "pdf-platform-history";

export function pushHistory(e: HistoryEntry) {
  try {
    const cur = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    cur.unshift(e);
    localStorage.setItem(KEY, JSON.stringify(cur.slice(0, 100)));
  } catch {}
}

export function readHistory(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}
