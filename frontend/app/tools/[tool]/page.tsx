import GenericToolPage from "@/components/GenericToolPage";
import { TOOLS, toolBySlug } from "@/lib/tools";

export function generateStaticParams() {
  return TOOLS.map((t) => ({ tool: t.slug }));
}

export default function ToolRoute({ params }: { params: { tool: string } }) {
  const tool = toolBySlug(params.tool);
  if (!tool) return <div><h1 className="text-xl font-semibold">Unknown tool</h1><a className="text-primary" href="/">Back home</a></div>;
  return <GenericToolPage tool={tool} />;
}
