"""FastAPI backend for the Han-Eng Lyric Video Maker pipeline."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ytmusicapi import YTMusic

from app.pipeline.process_manager import ProcessConfig, ProcessManager
from app.sources.youtube_utils import build_youtube_music_url

app = FastAPI(title="Han-Eng Lyric Video Maker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state. Replace with persistent storage if needed.
queue_items: List[Dict[str, Any]] = []
progress_queue: asyncio.Queue = asyncio.Queue()
run_lock = asyncio.Lock()


def _yt() -> YTMusic:
    """Return a YTMusic client (unauthenticated by default)."""
    return YTMusic()


def _track_from_playlist_item(item: dict, list_id: str) -> Dict[str, Any]:
    artists = item.get("artists") or []
    title = item.get("title") or ""
    video_id = item.get("videoId") or item.get("video_id")
    thumbs = item.get("thumbnails") or []
    album_art_url = thumbs[0]["url"] if thumbs else None

    return {
        "title": title,
        "artist": artists[0]["name"] if artists else "Unknown Artist",
        "videoId": video_id,
        "listId": list_id,
        "albumArtUrl": album_art_url,
        "duration": item.get("duration"),
    }


def _track_from_song(song: dict, list_id: Optional[str]) -> Dict[str, Any]:
    video_details = song.get("videoDetails") or {}
    microformat = (song.get("microformat") or {}).get("microformatDataRenderer") or {}
    thumbs = video_details.get("thumbnail", {}).get("thumbnails") or []
    album_art_url = thumbs[-1]["url"] if thumbs else None
    artists = video_details.get("author")

    return {
        "title": video_details.get("title"),
        "artist": artists,
        "videoId": video_details.get("videoId"),
        "listId": list_id,
        "albumArtUrl": album_art_url,
        "duration": video_details.get("lengthSeconds"),
        "description": microformat.get("description"),
    }


async def _emit_progress(message: str, percent: Optional[int] = None) -> None:
    payload = {"message": message, "timestamp": datetime.utcnow().isoformat() + "Z"}
    if percent is not None:
        payload["percent"] = percent
    await progress_queue.put(payload)


async def _stream_progress() -> AsyncGenerator[bytes, None]:
    # Replay last known state? For now, stream new events only.
    while True:
        data = await progress_queue.get()
        yield f"data: {json.dumps(data)}\n\n".encode("utf-8")


async def _resolve_list(list_id: str) -> List[Dict[str, Any]]:
    playlist = _yt().get_playlist(list_id, limit=500)
    tracks = playlist.get("tracks") or []
    return [_track_from_playlist_item(track, list_id) for track in tracks if track.get("videoId")]


async def _resolve_watch(video_id: str, list_id: Optional[str]) -> List[Dict[str, Any]]:
    song = _yt().get_song(video_id)
    track = _track_from_song(song, list_id)
    if not track.get("videoId"):
        raise HTTPException(status_code=400, detail="videoId를 확인할 수 없습니다.")
    return [track]


@app.post("/api/resolve")
async def resolve(payload: Dict[str, Any]):
    """Resolve extension JSON (v2) into a concrete track list using ytmusicapi."""
    if payload.get("version") != 2:
        raise HTTPException(status_code=400, detail="지원하지 않는 version입니다. v2 JSON을 전달해주세요.")

    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="items 배열이 비어있습니다.")

    resolved: List[Dict[str, Any]] = []
    for item in items:
        item_type = item.get("type")
        if item_type == "list":
            list_id = item.get("listId")
            if not list_id:
                raise HTTPException(status_code=400, detail="listId가 없습니다.")
            resolved.extend(await _resolve_list(list_id))
        elif item_type == "watch":
            video_id = item.get("videoId") or item.get("video_id")
            list_id = item.get("listId")
            if not video_id:
                raise HTTPException(status_code=400, detail="videoId가 없습니다.")
            resolved.extend(await _resolve_watch(video_id, list_id))
        else:
            raise HTTPException(status_code=400, detail=f"알 수 없는 item type: {item_type}")

    # Deduplicate by videoId while preserving order
    seen = set()
    deduped = []
    for track in resolved:
        vid = track.get("videoId")
        if vid and vid not in seen:
            seen.add(vid)
            deduped.append(track)

    return {"items": deduped, "count": len(deduped)}


@app.get("/api/queue")
async def get_queue():
    return {"items": queue_items, "count": len(queue_items)}


@app.post("/api/queue")
async def set_queue(payload: Dict[str, Any]):
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items 배열이 필요합니다.")
    queue_items.clear()
    queue_items.extend(items)
    return {"ok": True, "count": len(queue_items)}


@app.post("/api/queue/add")
async def add_to_queue(payload: Dict[str, Any]):
    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items 배열이 필요합니다.")
    queue_items.extend(items)
    return {"ok": True, "count": len(queue_items)}


@app.delete("/api/queue/{index}")
async def remove_from_queue(index: int):
    if index < 0 or index >= len(queue_items):
        raise HTTPException(status_code=404, detail="index 범위를 벗어났습니다.")
    queue_items.pop(index)
    return {"ok": True, "count": len(queue_items)}


@app.post("/api/queue/reorder")
async def reorder_queue(payload: Dict[str, Any]):
    try:
        from_idx = int(payload.get("from"))
        to_idx = int(payload.get("to"))
    except Exception:
        raise HTTPException(status_code=400, detail="from/to 값이 필요합니다.")

    if any(idx < 0 or idx >= len(queue_items) for idx in (from_idx, to_idx)):
        raise HTTPException(status_code=404, detail="index 범위를 벗어났습니다.")

    item = queue_items.pop(from_idx)
    queue_items.insert(to_idx, item)
    return {"ok": True, "items": queue_items}


async def _run_single_track(track: Dict[str, Any]) -> None:
    title = track.get("title") or ""
    artist = track.get("artist") or "Unknown Artist"
    video_id = track.get("videoId")
    album_art_url = track.get("albumArtUrl") or (track.get("thumbnails") or [{}])[-1].get("url")
    youtube_url = build_youtube_music_url(video_id) if video_id else ""

    upload_title = f"[HAN/ENG] {artist} - {title}"

    await _emit_progress(f"Start: {upload_title}", 0)

    def progress_cb(msg: str, pct: int) -> None:
        asyncio.create_task(_emit_progress(f"{msg} ({upload_title})", pct))

    manager = ProcessManager(progress_cb)
    config = ProcessConfig(
        title=title,
        artist=artist,
        album_art_url=album_art_url or "",
        youtube_url=youtube_url,
        video_id=video_id,
        output_mode="video",
    )

    error = manager.validate_config(config)
    if error:
        await _emit_progress(f"구성 오류: {error}", 0)
        raise HTTPException(status_code=400, detail=error)

    await manager.process_async(config)
    await _emit_progress(f"완료: {upload_title}", 100)


async def _run_queue_worker() -> None:
    for idx, track in enumerate(queue_items):
        await _emit_progress(f"Queue {idx + 1}/{len(queue_items)} 시작", None)
        await _run_single_track(track)


@app.post("/api/run")
async def run_queue(background_tasks: BackgroundTasks):
    if run_lock.locked():
        raise HTTPException(status_code=409, detail="이미 실행 중입니다.")

    async def runner():
        async with run_lock:
            try:
                await _emit_progress("큐 실행 시작", 0)
                await _run_queue_worker()
                await _emit_progress("큐 실행 완료", 100)
            except Exception as exc:
                await _emit_progress(f"실행 중 오류: {exc}", 0)

    background_tasks.add_task(asyncio.create_task, runner())
    return {"ok": True}


@app.get("/api/progress")
async def progress_stream():
    headers = {"Cache-Control": "no-cache", "Content-Type": "text/event-stream"}
    return StreamingResponse(_stream_progress(), headers=headers)
