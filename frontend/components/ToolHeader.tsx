export default function ToolHeader({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-1 text-muted">{desc}</p>
    </div>
  );
}
