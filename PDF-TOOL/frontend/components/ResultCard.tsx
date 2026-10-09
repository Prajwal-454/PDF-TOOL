import { downloadUrl } from "@/lib/api";

export default function ResultCard({ outputFile, pages }: { outputFile: string; pages?: number }) {
  return (
    <div className="mt-6 rounded-2xl border border-line bg-card p-5">
      <p className="font-medium text-success">Done — your merged PDF is ready.</p>
      {pages ? <p className="mt-1 text-sm text-muted">{pages} pages combined.</p> : null}
      <a
        href={downloadUrl(outputFile)}
        className="mt-4 inline-block rounded-xl bg-primary px-5 py-3 text-white"
        download
      >
        Download merged PDF
      </a>
    </div>
  );
}
