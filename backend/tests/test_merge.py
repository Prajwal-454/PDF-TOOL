from fastapi.testclient import TestClient
from pathlib import Path
from pypdf import PdfWriter
from app.main import app

client = TestClient(app)


def _make_pdf(path: Path, pages: int = 1):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(612, 792)
    with open(path, "wb") as f:
        w.write(f)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_upload_merge_download(tmp_path):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _make_pdf(a, 1)
    _make_pdf(b, 2)
    ids = []
    for p in (a, b):
        with open(p, "rb") as f:
            r = client.post("/api/files/upload", files={"file": (p.name, f, "application/pdf")})
        assert r.status_code == 200, r.text
        ids.append(r.json()["file_id"])
    r = client.post("/api/merge", json={"file_ids": ids})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    # BackgroundTasks run inline in TestClient
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "completed", job
    assert job["result"]["pages"] == 3
    dl = client.get(f"/api/download/{job['output_file']}")
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")


def test_reject_non_pdf():
    r = client.post("/api/files/upload", files={"file": ("evil.txt", b"hello", "text/plain")})
    assert r.status_code == 400
