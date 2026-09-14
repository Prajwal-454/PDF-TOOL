import os
import time
from pathlib import Path
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from app.main import app
from app.utils import storage
from app.utils.config import settings
from app.workers import job_store

client = TestClient(app)


def _make_pdf(path: Path, pages=2):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(612, 792)
    with open(path, "wb") as f:
        w.write(f)


def _upload(p: Path):
    with open(p, "rb") as f:
        r = client.post("/api/files/upload", files={"file": (p.name, f, "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()["file_id"]


def _run(tool, payload):
    r = client.post(f"/api/tools/{tool}", json=payload)
    assert r.status_code == 202, r.text
    return client.get(f"/api/jobs/{r.json()['job_id']}").json()


def test_health_extended(tmp_path):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "storage" in body and "jobs" in body


def test_maintenance_stats_and_cleanup():
    r = client.get("/api/maintenance/stats")
    assert r.status_code == 200
    body = r.json()
    assert "storage" in body and "limits" in body
    r = client.post("/api/maintenance/cleanup")
    assert r.status_code == 200
    assert "files" in r.json() and "jobs_pruned" in r.json()


def test_storage_cleanup_removes_old_files():
    storage.ensure_dirs()
    p = storage.tmp_path("test-old-cleanup.pdf")
    p.write_bytes(b"%PDF-1.4 old")
    old = time.time() - 49 * 3600
    os.utime(p, (old, old))
    removed = storage.cleanup_old_files(max_age_hours=24)
    assert removed["tmp"] >= 1
    assert not p.exists()


def test_job_prune_removes_old():
    job = job_store.create_job(tool="merge", input_files=[])
    # backdate in-place, then prune with tiny TTL
    job_store._jobs[job["id"]]["created_at"] = "2000-01-01T00:00:00+00:00"
    assert job_store.prune_old(max_age_hours=24) >= 1
    assert job_store.get_job(job["id"]) is None


def test_pdf_to_images_dpi_guard(tmp_path):
    a = tmp_path / "a.pdf"
    _make_pdf(a, 1)
    fid = _upload(a)
    job = _run("pdf-to-images", {"file_id": fid, "dpi": 9999, "fmt": "png"})
    assert job["status"] == "failed"
    assert "DPI" in (job["error"] or "")


def test_split_and_bundle_zip(tmp_path):
    a = tmp_path / "b.pdf"
    _make_pdf(a, 2)
    fid = _upload(a)
    job = _run("split", {"file_id": fid})
    assert job["status"] == "completed", job
    parts = job["result"]["parts"]
    assert len(parts) == 2 and "/" in parts[0]
    subdir = parts[0].split("/")[0]
    r = client.get(f"/api/download-bundle/{subdir}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert r.content[:2] == b"PK"
    # traversal rejected
    assert client.get("/api/download-bundle/..").status_code in (400, 404)


def test_workflow_new_ops(tmp_path):
    a = tmp_path / "c.pdf"
    _make_pdf(a, 2)
    fid = _upload(a)
    job = _run("workflow", {"file_id": fid, "steps": [
        {"op": "repair", "params": {}},
        {"op": "crop", "params": {"margin_pct": 5}},
    ]})
    assert job["status"] == "completed", job
