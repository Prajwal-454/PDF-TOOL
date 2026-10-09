"""Mobile intake: phone photos (WEBP/GIF/BMP/TIFF/AVIF/HEIC) must upload.

Regression test for mobile "Upload failed. Check file type" reports:
phones shoot WEBP (Android/WhatsApp) or HEIC (iPhone), which the old
magic-check rejected with HTTP 400. upload-any now auto-converts via Pillow.
"""
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _img_bytes(fmt: str) -> bytes:
    im = Image.new("RGB", (60, 40), "red")
    buf = BytesIO()
    im.save(buf, fmt)
    return buf.getvalue()


def _upload_any(name: str, data: bytes, mime: str):
    return client.post("/api/files/upload-any", files={"file": (name, data, mime)})


def test_webp_photo_converts_to_jpg():
    r = _upload_any("photo.webp", _img_bytes("WEBP"), "image/webp")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["file_id"].endswith(".jpg")
    assert body["kind"] == "image"


def test_gif_and_bmp_photos_convert():
    for name, fmt, mime in [("a.gif", "GIF", "image/gif"), ("b.bmp", "BMP", "image/bmp")]:
        r = _upload_any(name, _img_bytes(fmt), mime)
        assert r.status_code == 200, r.text
        assert r.json()["kind"] == "image"


def test_converted_photo_flows_into_images_to_pdf():
    r = _upload_any("photo.webp", _img_bytes("WEBP"), "image/webp")
    assert r.status_code == 200, r.text
    fid = r.json()["file_id"]
    j = client.post("/api/tools/images-to-pdf", json={"file_ids": [fid]})
    assert j.status_code == 202, j.text
    job = client.get(f"/api/jobs/{j.json()['job_id']}").json()
    assert job["status"] == "completed", job


def test_truly_unsupported_still_400():
    r = _upload_any("x.zip", b"PK\x03\x04" + b"0" * 100, "application/zip")
    assert r.status_code == 400, r.text
