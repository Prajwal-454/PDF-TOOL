"""File validation and secure storage helpers. Never trust filename or MIME type."""

from pathlib import Path
import uuid

ALLOWED_MAGIC = b"%PDF"
MAX_MAGIC_READ = 8


def secure_file_id(suffix: str = ".pdf") -> str:
    return f"{uuid.uuid4().hex}{suffix}"


def _strip_leading_junk(head: bytes) -> bytes:
    """Strip UTF-8 BOM + leading whitespace some generators prepend before %PDF."""
    if head.startswith(b"\xef\xbb\xbf"):
        head = head[3:]
    return head.lstrip(b"\x00 \t\r\n\x0b\x0c")


def validate_pdf_bytes(head: bytes, size: int, max_mb: int) -> str | None:
    """Return error message if invalid, else None."""
    if size == 0:
        return "Empty file is not allowed."
    if size > max_mb * 1024 * 1024:
        return f"File exceeds {max_mb} MB limit."
    if not _strip_leading_junk(head).startswith(ALLOWED_MAGIC):
        return "File is not a valid PDF (bad magic bytes)."
    return None


def safe_output_name() -> str:
    return f"{uuid.uuid4().hex}.pdf"
