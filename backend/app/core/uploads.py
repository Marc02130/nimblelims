"""Upload size limits (S8 — security-med-low-s7-s15)."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, UploadFile, status

# 10 MB — align with data_parser setup caps and packet FR-S8
MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024


async def read_upload_capped(
    file: UploadFile,
    *,
    max_bytes: int = MAX_UPLOAD_FILE_BYTES,
    field_name: Optional[str] = None,
) -> bytes:
    """
    Read an UploadFile and reject if larger than max_bytes.

    Uses Content-Length when present, then enforces on actual bytes read.
    """
    label = field_name or (file.filename or "file")
    cl = file.headers.get("content-length") if file.headers else None
    if cl is not None:
        try:
            if int(cl) > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "code": "upload_too_large",
                        "message": f"{label} exceeds {max_bytes} bytes",
                        "max_bytes": max_bytes,
                    },
                )
        except ValueError:
            pass

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "upload_too_large",
                "message": f"{label} exceeds {max_bytes} bytes",
                "max_bytes": max_bytes,
            },
        )
    return content
