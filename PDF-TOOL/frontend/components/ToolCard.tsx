export default function ToolCard({ href, name, desc }: { href: string; name: string; desc: string }) {
  return (
    <a href={href} className="block rounded-2xl border border-line bg-card p-5 shadow-sm transition hover:border-primary hover:shadow">
      <p className="font-medium">{name}</p>
      <p className="mt-1 text-sm text-muted">{desc}</p>
    </a>
  );
}
