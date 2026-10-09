"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-8 text-center">
      <h2 className="text-lg font-medium">Something went wrong.</h2>
      <p className="mt-2 text-sm text-muted">{error?.message || "Unexpected error."}</p>
      <button onClick={reset} className="mt-4 rounded-xl bg-primary px-5 py-3 text-white">
        Try again
      </button>
    </div>
  );
}
