from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Any, Dict


ALLOWED_UPLOAD_EXTENSIONS = {
    ".xlsx", ".xls", ".xlsm", ".csv", ".pdf", ".xer", ".xml", ".png", ".jpg", ".jpeg", ".webp"
}

DANGEROUS_UPLOAD_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".com", ".ps1", ".vbs", ".js", ".mjs", ".sh", ".php", ".py", ".jar", ".msi"
}

ALLOWED_MIME_TYPES = {
    "",
    "application/octet-stream",
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/csv",
    "text/plain",
    "application/xml",
    "text/xml",
    "image/png",
    "image/jpeg",
    "image/webp",
}


def _is_suspicious_filename(filename: str) -> bool:
    raw = filename or ""
    if any(ch in raw for ch in ("\x00", "/", "\\")):
        return True
    if ".." in raw:
        return True
    return bool(re.search(r"[\r\n\t]", raw))


def sanitize_filename(filename: str) -> str:
    name = Path(filename or "uploaded_file").name
    cleaned = re.sub(r"[^A-Za-z0-9._() -]+", "_", name).strip(" .")
    return cleaned[:160] or "uploaded_file"


def validate_upload_metadata(filename: str, mime_type: str | None, size_bytes: int | None, max_bytes: int) -> Dict[str, Any]:
    if _is_suspicious_filename(filename):
        raise ValueError("Unsafe filename.")
    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()
    suffixes = {suffix.lower() for suffix in Path(safe_name).suffixes}
    if suffixes & DANGEROUS_UPLOAD_EXTENSIONS:
        raise ValueError("Unsafe filename extension.")
    if not ext or ext in DANGEROUS_UPLOAD_EXTENSIONS or ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError(f"Unsupported or unsafe file extension: {ext or 'none'}")
    size = int(size_bytes or 0)
    if size < 0:
        raise ValueError("File size cannot be negative.")
    if max_bytes and size > max_bytes:
        raise ValueError(f"File is too large. Maximum allowed size is {max_bytes} bytes.")

    clean_mime = (mime_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream").split(";")[0].strip().lower()
    if clean_mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported MIME type: {clean_mime}")

    return {
        "original_filename": safe_name,
        "file_ext": ext.lstrip("."),
        "mime_type": clean_mime,
        "size_bytes": size,
    }


def validate_magic_signature(sample: bytes, filename: str) -> bool:
    """Validate parser-time file signatures before reading storage content."""
    ext = Path(filename or "").suffix.lower()
    prefix = sample[:16]
    if ext == ".pdf":
        return prefix.startswith(b"%PDF")
    if ext in {".xlsx", ".xlsm"}:
        return prefix.startswith(b"PK\x03\x04")
    if ext == ".xls":
        return prefix.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    if ext in {".png"}:
        return prefix.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {".jpg", ".jpeg"}:
        return prefix.startswith(b"\xff\xd8\xff")
    if ext == ".webp":
        return prefix.startswith(b"RIFF") and sample[8:12] == b"WEBP"
    if ext in {".csv", ".xml", ".xer"}:
        return b"\x00" not in sample[:4096]
    return False
