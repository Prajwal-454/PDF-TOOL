"""Core PDF operations — 100% free/open-source (pypdf + PyMuPDF + Pillow).

All functions raise ValueError with human-readable messages on bad input.
"""

from pathlib import Path
import fitz  # PyMuPDF (AGPL, free)
from pypdf import PdfReader, PdfWriter
from PIL import Image


def get_page_count(pdf_path: Path) -> int:
    return len(PdfReader(str(pdf_path)).pages)


def _require_exists(p: Path) -> None:
    if not p.exists():
        raise ValueError(f"Input file not found or expired: {p.name}")


def merge_pdfs(input_paths: list[Path], output_path: Path) -> dict:
    if len(input_paths) < 2:
        raise ValueError("At least 2 PDF files are required to merge.")
    writer = PdfWriter()
    total = 0
    for p in input_paths:
        _require_exists(p)
        r = PdfReader(str(p))
        if r.is_encrypted:
            raise ValueError(f"File is encrypted: {p.name}")
        for page in r.pages:
            writer.add_page(page)
            total += 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return {"pages": total, "size": output_path.stat().st_size}


def _parse_ranges(spec: str, num_pages: int) -> list[int]:
    """Parse '1-3,5' (1-based) into 0-based indices. 'all' not allowed here."""
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a) - 1, int(b) - 1
            if start < 0 or end >= num_pages or start > end:
                raise ValueError(f"Invalid page range: {part}")
            out.extend(range(start, end + 1))
        else:
            i = int(part) - 1
            if i < 0 or i >= num_pages:
                raise ValueError(f"Invalid page number: {part}")
            out.append(i)
    if not out:
        raise ValueError("No pages selected.")
    return out


def split_pdf(input_path: Path, out_dir: Path, ranges: str | None = None) -> dict:
    """Split into one PDF per range part. ranges like '1-2,3-5' else every page separate."""
    _require_exists(input_path)
    reader = PdfReader(str(input_path))
    n = len(reader.pages)
    parts = [p.strip() for p in ranges.split(",")] if ranges else [str(i + 1) for i in range(n)]
    # regroup bare numbers into single-page parts; ranges stay grouped
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for idx, part in enumerate(parts):
        indices = _parse_ranges(part, n)
        w = PdfWriter()
        for i in indices:
            w.add_page(reader.pages[i])
        name = f"split-{idx + 1}.pdf"
        with open(out_dir / name, "wb") as f:
            w.write(f)
        files.append(name)
    return {"parts": files, "count": len(files)}


def remove_pages(input_path: Path, output_path: Path, pages: str) -> dict:
    _require_exists(input_path)
    reader = PdfReader(str(input_path))
    drop = set(_parse_ranges(pages, len(reader.pages)))
    w = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in drop:
            w.add_page(page)
    if not len(w.pages):
        raise ValueError("Cannot remove all pages.")
    with open(output_path, "wb") as f:
        w.write(f)
    return {"pages": len(w.pages), "size": output_path.stat().st_size}


def extract_pages(input_path: Path, output_path: Path, pages: str) -> dict:
    _require_exists(input_path)
    reader = PdfReader(str(input_path))
    keep = _parse_ranges(pages, len(reader.pages))
    w = PdfWriter()
    for i in keep:
        w.add_page(reader.pages[i])
    with open(output_path, "wb") as f:
        w.write(f)
    return {"pages": len(w.pages), "size": output_path.stat().st_size}


def rotate_pages(input_path: Path, output_path: Path, pages: str | None, angle: int) -> dict:
    if angle not in (90, 180, 270):
        raise ValueError("Angle must be 90, 180 or 270.")
    _require_exists(input_path)
    reader = PdfReader(str(input_path))
    targets = set(_parse_ranges(pages, len(reader.pages))) if pages else set(range(len(reader.pages)))
    w = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in targets:
            page.rotate(angle)
        w.add_page(page)
    with open(output_path, "wb") as f:
        w.write(f)
    return {"pages": len(w.pages), "size": output_path.stat().st_size}


def reorder_pages(input_path: Path, output_path: Path, order: list[int]) -> dict:
    """order is 1-based page numbers in desired sequence."""
    _require_exists(input_path)
    reader = PdfReader(str(input_path))
    n = len(reader.pages)
    if sorted(order) != list(range(1, n + 1)):
        raise ValueError("Order must contain each page number exactly once.")
    w = PdfWriter()
    for p in order:
        w.add_page(reader.pages[p - 1])
    with open(output_path, "wb") as f:
        w.write(f)
    return {"pages": n, "size": output_path.stat().st_size}


def compress_pdf(input_path: Path, output_path: Path, level: str = "recommended") -> dict:
    """Free compression: re-save with deflate + garbage collection + image downscale."""
    _require_exists(input_path)
    orig = input_path.stat().st_size
    doc = fitz.open(str(input_path))
    # Downscale large images (free, lossy but effective)
    zoom = {"extreme": 0.4, "recommended": 0.65, "low": 0.85}.get(level, 0.65)
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width > 1200 or pix.height > 1200:
                    nw, nh = int(pix.width * zoom), int(pix.height * zoom)
                    pix2 = fitz.Pixmap(pix, fitz.Matrix(nw / pix.width, nh / pix.height), None)
                    doc.update_stream(xref, pix2.tobytes("jpg", jpg_quality=65 if level == "extreme" else 75))
            except Exception:
                continue
    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()
    new = output_path.stat().st_size
    saved = round((1 - new / orig) * 100, 1) if orig else 0
    return {"original": orig, "size": new, "saved_pct": saved, "pages": get_page_count(output_path)}


def repair_pdf(input_path: Path, output_path: Path) -> dict:
    """Best-effort rebuild via PyMuPDF + pypdf. Never promises full recovery."""
    _require_exists(input_path)
    try:
        doc = fitz.open(str(input_path))
        doc.save(str(output_path), garbage=4, deflate=True)
        doc.close()
        return {"pages": get_page_count(output_path), "size": output_path.stat().st_size}
    except Exception:
        # fallback: pypdf rewrite page-by-page, skipping broken pages
        reader = PdfReader(str(input_path), strict=False)
        w = PdfWriter()
        skipped = 0
        for page in reader.pages:
            try:
                w.add_page(page)
            except Exception:
                skipped += 1
        if not len(w.pages):
            raise ValueError("PDF could not be repaired — file is too damaged.")
        with open(output_path, "wb") as f:
            w.write(f)
        return {"pages": len(w.pages), "skipped": skipped, "size": output_path.stat().st_size}


def watermark_pdf(input_path: Path, output_path: Path, text: str, opacity: float = 0.15) -> dict:
    _require_exists(input_path)
    if not text.strip():
        raise ValueError("Watermark text is required.")
    doc = fitz.open(str(input_path))
    for page in doc:
        page.insert_text((50, page.rect.height / 2), text, fontsize=48, color=(0.6, 0.6, 0.6))
    doc.save(str(output_path), garbage=3, deflate=True)
    doc.close()
    return {"pages": get_page_count(output_path), "size": output_path.stat().st_size}


def add_page_numbers(input_path: Path, output_path: Path, position: str = "bottom-center") -> dict:
    _require_exists(input_path)
    doc = fitz.open(str(input_path))
    n = len(doc)
    for i, page in enumerate(doc):
        txt = f"{i + 1} / {n}"
        x = page.rect.width / 2 - 20
        y = page.rect.height - 30 if "bottom" in position else 30
        page.insert_text((x, y), txt, fontsize=9, color=(0.4, 0.4, 0.4))
    doc.save(str(output_path), garbage=3, deflate=True)
    doc.close()
    return {"pages": n, "size": output_path.stat().st_size}


def crop_pdf(input_path: Path, output_path: Path, margin_pct: float = 10.0) -> dict:
    _require_exists(input_path)
    if not (0 < margin_pct < 40):
        raise ValueError("Margin must be between 0 and 40 (%).")
    doc = fitz.open(str(input_path))
    for page in doc:
        r = page.rect
        mx, my = r.width * margin_pct / 100, r.height * margin_pct / 100
        page.set_cropbox(fitz.Rect(r.x0 + mx, r.y0 + my, r.x1 - mx, r.y1 - my))
    doc.save(str(output_path), garbage=3, deflate=True)
    doc.close()
    return {"pages": get_page_count(output_path), "size": output_path.stat().st_size}


def protect_pdf(input_path: Path, output_path: Path, password: str) -> dict:
    _require_exists(input_path)
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")
    w = PdfWriter()
    for page in PdfReader(str(input_path)).pages:
        w.add_page(page)
    w.encrypt(password)
    with open(output_path, "wb") as f:
        w.write(f)
    return {"pages": len(w.pages), "size": output_path.stat().st_size}


def unlock_pdf(input_path: Path, output_path: Path, password: str) -> dict:
    """Only for files the user is authorized to open (they must supply the password)."""
    _require_exists(input_path)
    reader = PdfReader(str(input_path))
    if not reader.is_encrypted:
        raise ValueError("PDF is not password-protected.")
    if reader.decrypt(password) == 0:
        raise ValueError("Wrong password.")
    w = PdfWriter()
    for page in reader.pages:
        w.add_page(page)
    with open(output_path, "wb") as f:
        w.write(f)
    return {"pages": len(w.pages), "size": output_path.stat().st_size}


def redact_pdf(input_path: Path, output_path: Path, phrases: list[str]) -> dict:
    """PERMANENT redaction: remove matching text content, then burn black boxes."""
    _require_exists(input_path)
    clean = [p.strip() for p in phrases if p.strip()]
    if not clean:
        raise ValueError("Provide at least one phrase to redact.")
    doc = fitz.open(str(input_path))
    count = 0
    for page in doc:
        for phrase in clean:
            for inst in page.search_for(phrase):
                count += 1
                page.add_redact_annot(inst, fill=(0, 0, 0))
        page.apply_redactions()
    if count == 0:
        doc.close()
        raise ValueError("No matches found for the given phrases.")
    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()
    # verify underlying text is gone
    check = fitz.open(str(output_path))
    leftover = sum(check[p].get_text().lower().count(ph.lower()) for ph in clean for p in range(len(check)))
    check.close()
    return {"redactions": count, "verify_leftover": leftover, "size": output_path.stat().st_size}


def compare_pdfs(a_path: Path, b_path: Path) -> dict:
    """Free text comparison per page. Returns per-page diff summary."""
    _require_exists(a_path)
    _require_exists(b_path)
    da, db = fitz.open(str(a_path)), fitz.open(str(b_path))
    pages = max(len(da), len(db))
    diffs = []
    for i in range(pages):
        ta = da[i].get_text().strip() if i < len(da) else ""
        tb = db[i].get_text().strip() if i < len(db) else ""
        if ta != tb:
            diffs.append({"page": i + 1, "a_chars": len(ta), "b_chars": len(tb), "changed": True})
    da.close()
    db.close()
    na = get_page_count(a_path)
    nb = get_page_count(b_path)
    return {"pages_a": na, "pages_b": nb, "different_pages": diffs, "diff_count": len(diffs)}


def pdf_to_images(input_path: Path, out_dir: Path, dpi: int = 150, fmt: str = "png") -> dict:
    _require_exists(input_path)
    if fmt not in ("png", "jpg"):
        raise ValueError("Format must be png or jpg.")
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(input_path))
    files = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        name = f"page-{i + 1}.{fmt}"
        pix.save(str(out_dir / name))
        files.append(name)
    doc.close()
    return {"images": files, "count": len(files)}


def images_to_pdf(image_paths: list[Path], output_path: Path) -> dict:
    if not image_paths:
        raise ValueError("No images provided.")
    imgs = []
    for p in image_paths:
        _require_exists(p)
        im = Image.open(p)
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        imgs.append(im)
    imgs[0].save(str(output_path), save_all=True, append_images=imgs[1:])
    return {"pages": len(imgs), "size": output_path.stat().st_size}


def extract_text_with_pages(input_path: Path) -> list[dict]:
    """Return [{'page': n, 'text': ...}] — foundation for AI features."""
    _require_exists(input_path)
    doc = fitz.open(str(input_path))
    out = [{"page": i + 1, "text": page.get_text().strip()} for i, page in enumerate(doc)]
    doc.close()
    return out


def place_signature(input_path: Path, output_path: Path, image_path: Path, page_num: int = 1,
                    x: float = 100, y: float = 100, width: float = 160) -> dict:
    """Place typed/drawn signature image. For legal PAdES signing add a cert layer later."""
    _require_exists(input_path)
    _require_exists(image_path)
    doc = fitz.open(str(input_path))
    if page_num < 1 or page_num > len(doc):
        raise ValueError("Invalid signature page.")
    page = doc[page_num - 1]
    pix = Image.open(image_path)
    h = width * pix.height / pix.width
    page.insert_image(fitz.Rect(x, y, x + width, y + h), filename=str(image_path))
    doc.save(str(output_path), garbage=3, deflate=True)
    doc.close()
    return {"pages": get_page_count(output_path), "size": output_path.stat().st_size}
