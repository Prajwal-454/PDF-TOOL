import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "PDF Tools — Merge, Split, Compress, Convert, AI (Free)",
    template: "%s · PDF Tools",
  },
  description: "Free PDF tools: merge, split, compress, convert, watermark, protect, OCR, summarize and ask. No sign-up, no paid APIs.",
  keywords: ["PDF", "merge PDF", "split PDF", "compress PDF", "PDF to Word", "OCR", "watermark PDF", "free PDF tools"],
  openGraph: {
    title: "PDF Tools — Everything you need for PDFs",
    description: "Organize, convert, edit, secure, optimize and analyze PDFs. 100% free stack.",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-line bg-white shadow-[0_1px_3px_rgba(15,23,42,0.06)]">
          <div className="mx-auto flex max-w-6xl items-center px-6 py-3">
            <a href="/" className="flex items-center gap-2" aria-label="PDF-TOOL home">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-white">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6" />
                </svg>
              </span>
              <span className="text-base font-semibold tracking-tight text-ink">PDF-TOOL</span>
            </a>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <footer className="border-t border-line bg-card">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-6 text-xs text-muted md:flex-row md:items-center md:justify-between">
            <p>PDF Tools · 100% free stack — no paid APIs, no account. Files auto-expire after ~24h.</p>
            <p>
              <a className="underline" href="/history">History</a>{" · "}
              <a className="underline" href="/workflows">Workflows</a>{" · "}
              <a className="underline" href="/ai">AI Workspace</a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
