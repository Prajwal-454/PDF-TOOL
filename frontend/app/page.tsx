import ToolCard from "@/components/ToolCard";
import { TOOLS } from "@/lib/tools";

const cats = ["Organize", "Convert to PDF", "Convert from PDF", "Edit", "Security", "Optimize", "AI"];

export default function Home() {
  return (
    <div>
      <section className="py-10 text-center">
        <h1 className="text-4xl font-semibold tracking-tight">Everything you need for PDFs.</h1>
        <p className="mx-auto mt-3 max-w-xl text-muted">
          Organize, convert, edit, secure, optimize and analyze documents. 100% free stack — no paid APIs.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <a href="/tools/merge" className="rounded-xl bg-primary px-5 py-3 text-white">Upload PDF</a>
          <a href="/ai" className="rounded-xl border border-line bg-card px-5 py-3">AI Workspace</a>
          <a href="/workflows" className="rounded-xl border border-line bg-card px-5 py-3">Workflows</a>
        </div>
      </section>
      {cats.map((c) => (
        <section key={c} className="mb-8">
          <h2 className="mb-3 text-lg font-medium">{c}</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {TOOLS.filter((t) => t.category === c).map((t) => (
              <ToolCard key={t.slug} href={`/tools/${t.slug}`} name={t.name} desc={t.desc} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
