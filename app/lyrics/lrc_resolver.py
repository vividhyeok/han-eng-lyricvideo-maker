"""Resolve LRC files via Genie or cached mappings."""

from __future__ import annotations

import os
import re
from typing import Optional

from app.config.paths import LYRICS_DIR, ensure_data_dirs
from app.lyrics import lrc_cache
from app.sources.genie_handler import get_genie_lyrics, search_genie_songs
from app.sources.youtube_utils import extract_video_id


def _sanitize_filename(text: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", text)


def resolve_lrc(title: str, artist: str, video_id: Optional[str] = None) -> Optional[str]:
    """Try to locate or fetch an LRC for the track."""
    entry = lrc_cache.get_entry(artist, title, video_id)
    if entry:
        cached_path = entry.get("lrc_path")
        if cached_path and os.path.exists(cached_path):
            return cached_path

    # Try Genie search
    query = f"{artist} {title}".strip()
    try:
        results = search_genie_songs(query, limit=1)
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"[WARN] Genie search failed for '{query}': {exc}")
        results = []

    if results:
        song_title, song_id, *_ = results[0]
        lyrics = get_genie_lyrics(song_id)
        if lyrics:
            ensure_data_dirs()
            os.makedirs(LYRICS_DIR, exist_ok=True)
            filename = _sanitize_filename(f"{artist} - {title}") or song_title or song_id
            lrc_path = os.path.join(LYRICS_DIR, f"{filename}.lrc")
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.write(lyrics.strip() + "\n")
            lrc_cache.upsert_entry(artist, title, video_id, genie_song_id=song_id, lrc_path=lrc_path)
            return lrc_path

    # No lyrics found
    return None


def save_manual_lrc(title: str, artist: str, video_id: Optional[str], lrc_content: str) -> str:
    """Persist manually-synced LRC and update cache."""
    ensure_data_dirs()
    os.makedirs(LYRICS_DIR, exist_ok=True)
    filename = _sanitize_filename(f"{artist} - {title}") or extract_video_id(video_id or "") or "manual"
    lrc_path = os.path.join(LYRICS_DIR, f"{filename}.lrc")
    with open(lrc_path, "w", encoding="utf-8") as f:
        f.write(lrc_content)
    lrc_cache.upsert_entry(artist, title, video_id, lrc_path=lrc_path)
    return lrc_path
