"""OCR — free stack: OCRmyPDF + Tesseract when installed, graceful fallback otherwise.

Install (all free):
  Windows: install Tesseract-OCR (https://github.com/UB-Mannheim/tesseract/wiki) + `pip install ocrmypdf`
  Docker: apt-get install -y tesseract-ocr ocrmypdf
Without them the API still works: it reports whether the PDF already has text
and tells the user exactly what to install — never a paid gate.
"""

from pathlib import Path
import shutil
import subprocess
import fitz


def ocr_status() -> dict:
    return {
        "tesseract": shutil.which("tesseract") is not None,
        "ocrmypdf": shutil.which("ocrmypdf") is not None,
    }


def has_text_layer(pdf: Path, min_chars: int = 50) -> bool:
    doc = fitz.open(str(pdf))
    total = sum(len(p.get_text().strip()) for p in doc)
    doc.close()
    return total >= min_chars


def run_ocr(input_path: Path, output_path: Path, language: str = "eng") -> dict:
    st = ocr_status()
    if has_text_layer(input_path):
        # Already searchable — copy through so workflows don't break
        output_path.write_bytes(input_path.read_bytes())
        return {"already_searchable": True, "engines": st,
                "message": "PDF already contains selectable text; returned as-is."}
    if not (st["tesseract"] and st["ocrmypdf"]):
        raise ValueError(
            "OCR engines not installed. Install free Tesseract OCR + OCRmyPDF, "
            "or use a PDF that already has a text layer. "
            f"Detected: {st}")
    cmd = ["ocrmypdf", "-l", language, "--force-ocr", str(input_path), str(output_path)]
    try:
        subprocess.run(cmd, capture_output=True, timeout=600, check=True)
    except subprocess.CalledProcessError as e:
        raise ValueError(f"OCR failed: {e.stderr.decode()[-500:]}")
    return {"already_searchable": False, "language": language,
            "size": output_path.stat().st_size}
