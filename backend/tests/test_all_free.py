from fastapi.testclient import TestClient
from pathlib import Path
from pypdf import PdfWriter
from app.main import app

client = TestClient(app)


def _make_pdf(path: Path, pages=1, text=None):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(612, 792)
    with open(path, "wb") as f:
        w.write(f)


def _upload(p: Path, any_api=False):
    url = "/api/files/upload-any" if any_api else "/api/files/upload"
    with open(p, "rb") as f:
        r = client.post(url, files={"file": (p.name, f, "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()["file_id"]


def _run(tool, payload):
    r = client.post(f"/api/tools/{tool}", json=payload)
    assert r.status_code == 202, r.text
    job = client.get(f"/api/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "completed", job
    return job


def test_full_matrix(tmp_path):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _make_pdf(a, 2)
    _make_pdf(b, 1)
    ida = _upload(a)
    idb = _upload(b)

    _run("merge", {"file_ids": [ida, idb]})
    _run("remove-pages", {"file_id": ida, "pages": "2"})
    _run("extract-pages", {"file_id": ida, "pages": "1"})
    _run("rotate", {"file_id": ida, "angle": 90})
    _run("reorder", {"file_id": ida, "order": [2, 1]})
    _run("compress", {"file_id": ida, "level": "recommended"})
    _run("repair", {"file_id": ida})
    _run("watermark", {"file_id": ida, "text": "FREE"})
    _run("page-numbers", {"file_id": ida})
    _run("crop", {"file_id": ida, "margin_pct": 5})
    _run("split", {"file_id": ida})
    _run("pdf-to-images", {"file_id": ida, "dpi": 72, "fmt": "png"})
    _run("protect", {"file_id": ida, "password": "secret123"})

    # protect then unlock
    prot = _run("protect", {"file_id": ida, "password": "secret123"})
    # download protected file, re-upload, unlock
    dl = client.get(f"/api/download/{prot['output_file']}")
    assert dl.status_code == 200
    pp = tmp_path / "prot.pdf"
    pp.write_bytes(dl.content)
    idp = _upload(pp)
    _run("unlock", {"file_id": idp, "password": "secret123"})

    # redact needs real text; create via reportlab
    from reportlab.pdfgen import canvas
    rp = tmp_path / "r.pdf"
    c = canvas.Canvas(str(rp))
    c.drawString(100, 700, "hello secretword world")
    c.showPage()
    c.save()
    idr = _upload(rp)
    _run("redact", {"file_id": idr, "phrases": ["secretword"]})

    _run("compare", {"file_a": ida, "file_b": idb})
    _run("summarize", {"file_id": idr, "mode": "quick"})
    _run("ask", {"file_id": idr, "question": "what is the secret word?"})
    _run("markdown", {"file_id": idr})
    _run("form-detect", {"file_id": idr})
    _run("translate", {"file_id": idr, "target": "es"})
    _run("pdf-to-office", {"file_id": idr, "kind": "docx"})
    _run("workflow", {"file_id": idr, "steps": [{"op": "compress", "params": {"level": "low"}}, {"op": "page-numbers", "params": {}}]})
