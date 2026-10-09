export default function ProcessingProgress({ status }: { status: string }) {
  if (status === "idle") return null;
  return (
    <div className="mt-4 rounded-xl border border-line bg-primaryLight px-4 py-3 text-sm" role="status">
      {status === "uploading" && "Uploading…"}
      {status === "queued" && "Queued…"}
      {status === "processing" && "Processing your PDF…"}
      {status === "failed" && "Something went wrong. Please retry."}
    </div>
  );
}
