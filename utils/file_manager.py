"""File and token helper utilities."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any

SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]")
STREAMABLE_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".webm",
    ".mkv",
    ".mov",
    ".avi",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".wav",
    ".flac",
}

_ffmpeg_available: bool | None = None
_hls_locks: dict[str, asyncio.Lock] = {}


def now_ts() -> int:
    return int(time.time())


def sanitize_filename(name: str) -> str:
    clean = SAFE_FILENAME_PATTERN.sub("_", name.strip())
    return clean[:180] or "file.bin"


def guess_mime_type(file_name: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or fallback


def is_streamable(file_name: str, mime_type: str | None) -> bool:
    if mime_type and (mime_type.startswith("video/") or mime_type.startswith("audio/")):
        return True
    return Path(file_name).suffix.lower() in STREAMABLE_EXTENSIONS


def build_storage_path(storage_dir: Path, telegram_unique_id: str, file_name: str) -> Path:
    suffix = Path(file_name).suffix or ".bin"
    base = sanitize_filename(Path(file_name).stem)
    return storage_dir / f"{telegram_unique_id}_{base}{suffix}"


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


def sign_payload(payload: dict[str, Any], secret: str, expiry_seconds: int) -> tuple[str, int]:
    expires_at = now_ts() + max(1, expiry_seconds)
    payload_with_exp = {**payload, "exp": expires_at}
    encoded_payload = _urlsafe_b64encode(
        json.dumps(payload_with_exp, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).digest()
    token = f"{encoded_payload}.{_urlsafe_b64encode(signature)}"
    return token, expires_at


def verify_token(token: str, secret: str) -> dict[str, Any]:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)

        expected_signature = hmac.new(
            secret.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256
        ).digest()
        provided_signature = _urlsafe_b64decode(encoded_signature)
        if not hmac.compare_digest(expected_signature, provided_signature):
            raise ValueError("Invalid token signature")

        payload_raw = _urlsafe_b64decode(encoded_payload)
        payload = json.loads(payload_raw.decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp < now_ts():
            raise ValueError("Token expired")
        return payload
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Malformed token") from exc


async def ffmpeg_exists() -> bool:
    global _ffmpeg_available  # noqa: PLW0603
    if _ffmpeg_available is not None:
        return _ffmpeg_available
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-version",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    _ffmpeg_available = (await proc.wait()) == 0
    return _ffmpeg_available


async def ensure_hls(source_file: Path, hls_dir: Path) -> Path:
    hls_dir.mkdir(parents=True, exist_ok=True)
    playlist_path = hls_dir / "index.m3u8"
    if playlist_path.exists():
        return playlist_path

    key = str(hls_dir.resolve())
    lock = _hls_locks.setdefault(key, asyncio.Lock())
    async with lock:
        if playlist_path.exists():
            return playlist_path

        segment_pattern = str(hls_dir / "segment_%03d.ts")
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source_file),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-f",
            "hls",
            "-hls_time",
            "4",
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            segment_pattern,
            str(playlist_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            if playlist_path.exists():
                playlist_path.unlink(missing_ok=True)
            raise RuntimeError(f"ffmpeg failed: {stderr.decode('utf-8', errors='ignore')[:500]}")

    return playlist_path
