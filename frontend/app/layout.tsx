import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PDF Tools — Everything you need for PDFs",
  description: "Organize, convert, edit, secure, optimize and analyze PDFs."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-line bg-card">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <a href="/" className="font-semibold text-ink">PDF Tools</a>
            <nav className="hidden gap-6 text-sm text-muted md:flex">
              <a href="/">Tools</a>
              <a href="/tools/merge">Merge</a>
              <a href="/ai">AI</a>
              <a href="/workflows">Workflows</a>
              <a href="/history">History</a>
            </nav>
            <div className="flex gap-3">
              <a href="/history" className="rounded-lg border border-line px-4 py-2 text-sm">History</a>
              <a href="/tools/merge" className="rounded-lg bg-primary px-4 py-2 text-sm text-white">Get Started</a>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
