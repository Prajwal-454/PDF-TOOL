"""Office/image/HTML <-> PDF conversion — 100% free, pure-Python stack.

Office -> PDF: python-docx / openpyxl / python-pptx READ + reportlab WRITE.
  (LibreOffice headless gives pixel-perfect output and is also free; if
  `soffice` is installed we prefer it, else fall back to this engine.)
PDF -> Office: PyMuPDF/pdfminer text+table extraction -> python-docx/openpyxl/pptx.
Limitation contract: layout preserved best-effort; complex PDFs won't round-trip perfectly.
"""

from pathlib import Path
import shutil
import subprocess
import fitz
from docx import Document
from docx.shared import Pt
from openpyxl import Workbook, load_workbook
from pptx import Presentation
from pptx.util import Inches
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from PIL import Image


def _try_libreoffice(src: Path, out_dir: Path) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    try:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(src)],
                       capture_output=True, timeout=120, check=True)
        pdf = out_dir / (src.stem + ".pdf")
        return pdf if pdf.exists() else None
    except Exception:
        return None


def _pdf_canvas(path: Path, title: str = ""):
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story: list = []
    if title:
        story += [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    return doc, styles, story


def docx_to_pdf(src: Path, dest: Path) -> dict:
    lo = _try_libreoffice(src, dest.parent)
    if lo and lo != dest:
        lo.rename(dest)
        return {"via": "libreoffice", "size": dest.stat().st_size}
    d = Document(str(src))
    doc, styles, story = _pdf_canvas(dest, src.stem)
    for p in d.paragraphs:
        if p.text.strip():
            story.append(Paragraph(p.text, styles["Normal"]))
    for t in d.tables:
        data = [[c.text for c in row.cells] for row in t.rows]
        if data:
            story.append(Table(data, style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)])))
    doc.build(story or [Paragraph("(empty document)", styles["Normal"])])
    return {"via": "reportlab-free", "size": dest.stat().st_size}


def xlsx_to_pdf(src: Path, dest: Path) -> dict:
    lo = _try_libreoffice(src, dest.parent)
    if lo and lo != dest:
        lo.rename(dest)
        return {"via": "libreoffice", "size": dest.stat().st_size}
    wb = load_workbook(str(src), data_only=True)
    doc, styles, story = _pdf_canvas(dest, src.stem)
    for ws in wb.worksheets:
        story.append(Paragraph(f"Sheet: {ws.title}", styles["Heading2"]))
        rows = [[str(c.value) if c.value is not None else "" for c in row] for row in ws.iter_rows()]
        rows = [r for r in rows if any(x.strip() for x in r)][:60]
        if rows:
            story.append(Table(rows, style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)])))
    doc.build(story)
    return {"via": "reportlab-free", "size": dest.stat().st_size}


def pptx_to_pdf(src: Path, dest: Path) -> dict:
    lo = _try_libreoffice(src, dest.parent)
    if lo and lo != dest:
        lo.rename(dest)
        return {"via": "libreoffice", "size": dest.stat().st_size}
    prs = Presentation(str(src))
    doc, styles, story = _pdf_canvas(dest, src.stem)
    for i, slide in enumerate(prs.slides):
        story.append(Paragraph(f"Slide {i + 1}", styles["Heading2"]))
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text.strip():
                story.append(Paragraph(shape.text, styles["Normal"]))
            if shape.has_table:
                data = [[c.text for c in row.cells] for row in shape.table.rows]
                story.append(Table(data, style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)])))
        story.append(PageBreak())
    doc.build(story)
    return {"via": "reportlab-free", "size": dest.stat().st_size}


def html_to_pdf(src: Path, dest: Path) -> dict:
    import re
    html = src.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [l.strip() for l in text.splitlines() if l.strip()][:500]
    doc, styles, story = _pdf_canvas(dest, src.stem)
    for ln in lines:
        story.append(Paragraph(ln, styles["Normal"]))
    doc.build(story or [Paragraph("(empty)", styles["Normal"])])
    return {"via": "reportlab-free", "size": dest.stat().st_size}


def txt_to_pdf(src: Path, dest: Path) -> dict:
    lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()[:1000]
    doc, styles, story = _pdf_canvas(dest, src.stem)
    for ln in lines:
        story.append(Paragraph(ln or " ", styles["Normal"]))
    doc.build(story or [Paragraph("(empty)", styles["Normal"])])
    return {"via": "reportlab-free", "size": dest.stat().st_size}


def pdf_to_docx(src: Path, dest: Path) -> dict:
    pages = fitz.open(str(src))
    d = Document()
    for page in pages:
        for block in page.get_text("blocks"):
            txt = block[4].strip()
            if txt:
                d.add_paragraph(txt)
        # tables best-effort
        try:
            for tab in page.find_tables().tables:
                t = d.add_table(rows=len(tab.cells), cols=len(tab.cells[0]))
                for r, row in enumerate(tab.cells):
                    for c, cell in enumerate(row):
                        t.cell(r, c).text = page.get_text(clip=cell).strip()
        except Exception:
            pass
    pages.close()
    d.save(str(dest))
    return {"size": dest.stat().st_size, "note": "Layout best-effort; scanned PDFs need OCR first."}


def pdf_to_xlsx(src: Path, dest: Path) -> dict:
    pages = fitz.open(str(src))
    wb = Workbook()
    ws = wb.active
    ws.title = "text"
    r = 1
    for i, page in enumerate(pages):
        ws.cell(r, 1, f"--- Page {i + 1} ---")
        r += 1
        try:
            tables = list(page.find_tables())
            if tables:
                for tab in tables:
                    for row in tab.extract():
                        for c, val in enumerate(row, 1):
                            ws.cell(r, c, val)
                        r += 1
                continue
        except Exception:
            pass
        for line in page.get_text().splitlines():
            if line.strip():
                ws.cell(r, 1, line.strip())
                r += 1
    pages.close()
    wb.save(str(dest))
    return {"size": dest.stat().st_size}


def pdf_to_pptx(src: Path, dest: Path) -> dict:
    pages = fitz.open(str(src))
    prs = Presentation()
    blank = prs.slide_layouts[6]
    for page in pages:
        slide = prs.slides.add_slide(blank)
        tx = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(6))
        tx.text_frame.text = page.get_text().strip()[:3000]
    pages.close()
    prs.save(str(dest))
    return {"size": dest.stat().st_size, "slides": len(prs.slides)}


def pdf_to_markdown_file(src: Path, dest: Path) -> dict:
    from .ai_service import pdf_to_markdown
    md = pdf_to_markdown(src)
    dest.write_text(md, encoding="utf-8")
    return {"size": dest.stat().st_size, "chars": len(md)}
