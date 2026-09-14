export type Field = {
  key: string;
  label: string;
  type: "text" | "select" | "number" | "question";
  placeholder?: string;
  options?: { value: string; label: string }[];
  defaultValue?: string;
};

export type Tool = {
  slug: string;
  name: string;
  desc: string;
  category: string;
  accept: string;
  multi?: boolean;
  anyUpload?: boolean;
  fields: Field[];
  hint?: string;
};

export const TOOLS: Tool[] = [
  { slug: "merge", name: "Merge PDF", desc: "Combine multiple PDFs into one.", category: "Organize", accept: "application/pdf", multi: true, fields: [] },
  { slug: "split", name: "Split PDF", desc: "Split by ranges, e.g. 1-2,3-5. Blank = every page.", category: "Organize", accept: "application/pdf", fields: [{ key: "ranges", label: "Ranges (1-based, e.g. 1-2,3)", type: "text", placeholder: "1-2,3-5" }] },
  { slug: "remove-pages", name: "Remove pages", desc: "Delete pages, e.g. 2,5-7.", category: "Organize", accept: "application/pdf", fields: [{ key: "pages", label: "Pages to remove", type: "text", placeholder: "2,5-7" }] },
  { slug: "extract-pages", name: "Extract pages", desc: "Keep only selected pages.", category: "Organize", accept: "application/pdf", fields: [{ key: "pages", label: "Pages to keep", type: "text", placeholder: "1-3" }] },
  { slug: "rotate", name: "Rotate pages", desc: "Rotate all or selected pages.", category: "Organize", accept: "application/pdf", fields: [{ key: "pages", label: "Pages (blank = all)", type: "text", placeholder: "1-3" }, { key: "angle", label: "Angle", type: "select", options: [{ value: "90", label: "90°" }, { value: "180", label: "180°" }, { value: "270", label: "270°" }], defaultValue: "90" }] },
  { slug: "reorder", name: "Reorder pages", desc: "New order, e.g. 3,1,2.", category: "Organize", accept: "application/pdf", fields: [{ key: "order", label: "Order (comma-separated)", type: "text", placeholder: "2,1,3" }], hint: "Must list every page exactly once." },
  { slug: "images-to-pdf", name: "JPG/PNG → PDF", desc: "Scan images into a PDF.", category: "Convert to PDF", accept: ".jpg,.jpeg,.png", multi: true, anyUpload: true, fields: [] },
  { slug: "office-to-pdf", name: "Office → PDF", desc: "DOCX/XLSX/PPTX/HTML/TXT → PDF. Free engine; LibreOffice used if installed.", category: "Convert to PDF", accept: ".docx,.xlsx,.pptx,.html,.htm,.txt,.csv", anyUpload: true, fields: [{ key: "kind", label: "Input type", type: "select", options: [{ value: "docx", label: "Word (.docx)" }, { value: "xlsx", label: "Excel (.xlsx)" }, { value: "pptx", label: "PowerPoint (.pptx)" }, { value: "html", label: "HTML" }, { value: "txt", label: "Text (.txt/.csv)" }], defaultValue: "docx" }] },
  { slug: "pdf-to-office", name: "PDF → Office/Markdown", desc: "Extract to DOCX/XLSX/PPTX/MD. Best-effort layout.", category: "Convert from PDF", accept: "application/pdf", fields: [{ key: "kind", label: "Output", type: "select", options: [{ value: "docx", label: "Word (.docx)" }, { value: "xlsx", label: "Excel (.xlsx)" }, { value: "pptx", label: "PowerPoint (.pptx)" }, { value: "md", label: "Markdown (.md)" }], defaultValue: "docx" }] },
  { slug: "pdf-to-images", name: "PDF → JPG/PNG", desc: "Render each page as an image.", category: "Convert from PDF", accept: "application/pdf", fields: [{ key: "fmt", label: "Format", type: "select", options: [{ value: "png", label: "PNG" }, { value: "jpg", label: "JPG" }], defaultValue: "png" }, { key: "dpi", label: "DPI", type: "select", options: [{ value: "100", label: "100" }, { value: "150", label: "150" }, { value: "200", label: "200" }], defaultValue: "150" }] },
  { slug: "watermark", name: "Watermark", desc: "Stamp text across pages.", category: "Edit", accept: "application/pdf", fields: [{ key: "text", label: "Watermark text", type: "text", placeholder: "CONFIDENTIAL" }] },
  { slug: "page-numbers", name: "Page numbers", desc: "Add 1/N footers.", category: "Edit", accept: "application/pdf", fields: [] },
  { slug: "crop", name: "Crop margins", desc: "Trim page margins by %.", category: "Edit", accept: "application/pdf", fields: [{ key: "margin_pct", label: "Margin %", type: "number", placeholder: "10" }] },
  { slug: "protect", name: "Protect PDF", desc: "Add a password (min 4 chars).", category: "Security", accept: "application/pdf", fields: [{ key: "password", label: "Password", type: "text", placeholder: "••••••" }] },
  { slug: "unlock", name: "Unlock PDF", desc: "Remove password with the correct password.", category: "Security", accept: "application/pdf", fields: [{ key: "password", label: "Current password", type: "text" }] },
  { slug: "redact", name: "Redact (permanent)", desc: "Permanently remove phrases + verify.", category: "Security", accept: "application/pdf", fields: [{ key: "phrases", label: "Phrases (comma-separated)", type: "text", placeholder: "SSN, secret" }], hint: "True removal, not a black box overlay." },
  { slug: "compare", name: "Compare PDFs", desc: "Text diff per page (two files).", category: "Security", accept: "application/pdf", multi: true, fields: [] },
  { slug: "sign", name: "E-sign", desc: "Place a PNG signature image.", category: "Security", accept: "application/pdf", fields: [{ key: "page", label: "Page", type: "number", placeholder: "1" }], hint: "Upload PDF below, then upload signature PNG when prompted. Image-of-signature now; PAdES certs later." },
  { slug: "compress", name: "Compress PDF", desc: "Downscale + deflate. Shows % saved.", category: "Optimize", accept: "application/pdf", fields: [{ key: "level", label: "Level", type: "select", options: [{ value: "extreme", label: "Extreme" }, { value: "recommended", label: "Recommended" }, { value: "low", label: "Low" }], defaultValue: "recommended" }] },
  { slug: "repair", name: "Repair PDF", desc: "Best-effort rebuild; never promises miracles.", category: "Optimize", accept: "application/pdf", fields: [] },
  { slug: "ocr", name: "OCR (searchable PDF)", desc: "Free Tesseract/OCRmyPDF when installed.", category: "Optimize", accept: "application/pdf", fields: [{ key: "language", label: "Language", type: "select", options: [{ value: "eng", label: "English" }, { value: "hin", label: "Hindi" }, { value: "tel", label: "Telugu" }, { value: "spa", label: "Spanish" }, { value: "fra", label: "French" }], defaultValue: "eng" }] },
  { slug: "summarize", name: "AI Summarize", desc: "Free offline extractive summary + page refs.", category: "AI", accept: "application/pdf", fields: [{ key: "mode", label: "Style", type: "select", options: [{ value: "quick", label: "Quick" }, { value: "detailed", label: "Detailed" }, { value: "executive", label: "Executive" }, { value: "key-points", label: "Key points" }], defaultValue: "key-points" }] },
  { slug: "ask", name: "Ask PDF", desc: "Free offline retrieval + page refs.", category: "AI", accept: "application/pdf", fields: [{ key: "question", label: "Your question", type: "question", placeholder: "What are the main conclusions?" }] },
  { slug: "markdown", name: "PDF → Markdown", desc: "Headings, lists, tables → clean MD.", category: "AI", accept: "application/pdf", fields: [] },
  { slug: "form-detect", name: "AI Form detection", desc: "Heuristic field finder; review before use.", category: "AI", accept: "application/pdf", fields: [] },
  { slug: "translate", name: "Translate PDF", desc: "Layout-preserving shell; Ollama/LibreTranslate upgrade free.", category: "AI", accept: "application/pdf", fields: [{ key: "target", label: "Target (e.g. es, hi, te)", type: "text", placeholder: "es" }, { key: "source", label: "Source (auto ok)", type: "text", placeholder: "auto" }] }
];

export const toolBySlug = (slug: string) => TOOLS.find((t) => t.slug === slug);
