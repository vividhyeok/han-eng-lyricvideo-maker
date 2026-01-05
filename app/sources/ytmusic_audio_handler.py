"""Download audio for YouTube Music tracks by video id with caching."""

from __future__ import annotations

import os
import shutil
from typing import Optional

import yt_dlp

from app.config.paths import CACHE_DIR, TEMP_DIR, ensure_data_dirs, FFMPEG_DIR
from app.sources.youtube_utils import build_youtube_music_url


YTMUSIC_CACHE_DIR = os.path.join(CACHE_DIR, "ytmusic_audio")


def get_cached_audio_path(video_id: str) -> str:
    ensure_data_dirs()
    os.makedirs(YTMUSIC_CACHE_DIR, exist_ok=True)
    return os.path.join(YTMUSIC_CACHE_DIR, f"{video_id}.mp3")


def get_or_download_audio(video_id: str, title: str, artist: str, target_filename: Optional[str] = None) -> Optional[str]:
    """Return cached audio path, downloading it if necessary."""
    if not video_id:
        return None

    ensure_data_dirs()
    os.makedirs(YTMUSIC_CACHE_DIR, exist_ok=True)

    cached_path = get_cached_audio_path(video_id)
    if os.path.exists(cached_path) and os.path.getsize(cached_path) > 0:
        return _maybe_copy_to_target(cached_path, target_filename)

    url = build_youtube_music_url(video_id)
    base_path = os.path.join(YTMUSIC_CACHE_DIR, video_id)

    ydl_opts = {
        "format": "bestaudio/best",
        "extract_audio": True,
        "audio_format": "mp3",
        "audio_quality": "192K",
        "outtmpl": base_path + ".%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "ffmpeg_location": FFMPEG_DIR,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "overwrites": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"[DEBUG] Downloading YT Music audio: {artist} - {title} ({video_id})")
            ydl.download([url])
        if os.path.exists(cached_path):
            return _maybe_copy_to_target(cached_path, target_filename)
    except Exception as exc:  # pragma: no cover - network/yt-dlp dependent
        print(f"[ERROR] Failed to download YouTube Music audio: {exc}")
    return None


def _maybe_copy_to_target(cached_path: str, target_filename: Optional[str]) -> str:
    """Optionally copy the cached file to a temp location with the requested name."""
    if not target_filename:
        return cached_path

    ensure_data_dirs()
    os.makedirs(TEMP_DIR, exist_ok=True)
    target_path = os.path.join(TEMP_DIR, f"{target_filename}.mp3")
    if os.path.abspath(cached_path) == os.path.abspath(target_path):
        return cached_path

    try:
        shutil.copy2(cached_path, target_path)
        return target_path
    except Exception as exc:  # pragma: no cover - filesystem dependent
        print(f"[WARN] Failed to copy cached audio: {exc}")
        return cached_path
