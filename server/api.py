"""FastAPI link server for downloads and streaming."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from bot.config import Settings
from bot.database import Database
from server.streaming import stream_file_response
from utils.file_manager import ensure_hls, ffmpeg_exists, guess_mime_type, verify_token


def create_app(settings: Settings, db: Database) -> FastAPI:
    app = FastAPI(title="Telegram File Link Bot API", version="1.0.0")
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

    app.state.settings = settings
    app.state.db = db
    app.state.templates = templates

    async def resolve_file(token: str) -> dict:
        try:
            payload = verify_token(token, settings.link_signing_secret)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        file_id = int(payload.get("file_id", 0))
        if not file_id:
            raise HTTPException(status_code=403, detail="Token payload is invalid")

        file_record = await db.get_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File index not found")

        file_path = Path(file_record["local_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        await db.touch_link(token)
        return file_record

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/d/{token}")
    async def direct_download(token: str, request: Request):
        file_record = await resolve_file(token)
        file_path = Path(file_record["local_path"])
        media_type = file_record.get("mime_type") or guess_mime_type(file_record["file_name"])
        return stream_file_response(
            request=request,
            file_path=file_path,
            media_type=media_type,
            download_name=file_record["file_name"],
            as_attachment=True,
        )

    @app.get("/s/{token}")
    async def stream_content(token: str, request: Request):
        file_record = await resolve_file(token)
        file_path = Path(file_record["local_path"])
        media_type = file_record.get("mime_type") or guess_mime_type(file_record["file_name"])
        return stream_file_response(
            request=request,
            file_path=file_path,
            media_type=media_type,
            download_name=file_record["file_name"],
            as_attachment=False,
        )

    @app.get("/player/{token}", response_class=HTMLResponse)
    async def player_page(token: str, request: Request):
        file_record = await resolve_file(token)
        stream_url = f"/s/{token}"
        hls_url = f"/hls/{token}/index.m3u8"
        download_url = f"/d/{token}"
        return templates.TemplateResponse(
            "player.html",
            {
                "request": request,
                "file_name": file_record["file_name"],
                "stream_url": stream_url,
                "download_url": download_url,
                "hls_url": hls_url,
                "mime_type": file_record.get("mime_type") or guess_mime_type(file_record["file_name"]),
            },
        )

    @app.get("/hls/{token}/index.m3u8")
    async def hls_playlist(token: str):
        if not settings.ffmpeg_enabled:
            raise HTTPException(status_code=404, detail="HLS endpoint disabled")
        if not await ffmpeg_exists():
            raise HTTPException(status_code=503, detail="ffmpeg is not available")

        file_record = await resolve_file(token)
        source_path = Path(file_record["local_path"])
        target_hls_dir = settings.hls_path / str(file_record["file_id"])
        try:
            playlist_path = await ensure_hls(source_path, target_hls_dir)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return FileResponse(
            path=str(playlist_path),
            media_type="application/vnd.apple.mpegurl",
            filename="index.m3u8",
        )

    @app.get("/hls/{token}/{segment_name}")
    async def hls_segment(token: str, segment_name: str):
        # Token validation keeps segment directory private.
        file_record = await resolve_file(token)
        segment_path = settings.hls_path / str(file_record["file_id"]) / segment_name
        if not segment_path.exists():
            raise HTTPException(status_code=404, detail="HLS segment not found")
        media_type = "video/MP2T" if segment_name.endswith(".ts") else "application/octet-stream"
        return FileResponse(path=str(segment_path), media_type=media_type)

    return app
