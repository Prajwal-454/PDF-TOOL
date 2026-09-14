import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = (process.env.NEXT_PUBLIC_SITE_URL || "").trim().replace(/\/+$/, "");
  if (!base) return [];
  const tools = [
    "merge", "split", "compress", "pdf-to-images", "images-to-pdf",
    "office-to-pdf", "pdf-to-office", "watermark", "protect", "ocr",
    "summarize", "ask",
  ];
  return [
    { url: `${base}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/ai`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${base}/workflows`, changeFrequency: "weekly", priority: 0.8 },
    ...tools.map((t) => ({ url: `${base}/tools/${t}`, changeFrequency: "monthly" as const, priority: 0.7 })),
  ];
}
