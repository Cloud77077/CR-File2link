"""HTTP streaming primitives."""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

CHUNK_SIZE = 1024 * 1024


def _parse_range_header(range_header: str, file_size: int) -> tuple[int, int] | None:
    if not range_header.startswith("bytes="):
        return None
    range_value = range_header.replace("bytes=", "", 1)
    if "," in range_value:
        # Multi-range is not needed for this bot.
        return None

    try:
        start_raw, end_raw = range_value.split("-", 1)
        if start_raw == "":
            length = int(end_raw)
            start = max(file_size - length, 0)
            end = file_size - 1
        else:
            start = int(start_raw)
            end = int(end_raw) if end_raw else file_size - 1
    except (ValueError, TypeError):
        return None

    if start > end or start < 0 or end >= file_size:
        return None
    return start, end


async def _iter_file_range(file_path: Path, start: int, end: int) -> AsyncIterator[bytes]:
    with file_path.open("rb") as file_handle:
        file_handle.seek(start)
        remaining = (end - start) + 1
        while remaining > 0:
            chunk = file_handle.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def stream_file_response(
    request: Request,
    file_path: Path,
    media_type: str,
    download_name: str | None = None,
    as_attachment: bool = False,
):
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    if not range_header:
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=download_name,
            content_disposition_type="attachment" if as_attachment else "inline",
        )

    parsed = _parse_range_header(range_header, file_size)
    if parsed is None:
        raise HTTPException(status_code=416, detail="Invalid Range header")

    start, end = parsed
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str((end - start) + 1),
    }
    if download_name:
        disposition = "attachment" if as_attachment else "inline"
        headers["Content-Disposition"] = f'{disposition}; filename="{download_name}"'

    return StreamingResponse(
        _iter_file_range(file_path, start, end),
        status_code=206,
        headers=headers,
        media_type=media_type,
    )
