"""Persistent cache for lyrics-to-track mappings."""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from app.config.paths import LYRIC_MAPPING_PATH, ensure_data_dirs

_cache: Optional[Dict[str, dict]] = None


def _load_cache() -> Dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache

    ensure_data_dirs()
    if os.path.exists(LYRIC_MAPPING_PATH):
        try:
            with open(LYRIC_MAPPING_PATH, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:  # pragma: no cover - defensive
            _cache = {}
    else:
        _cache = {}
    return _cache


def _save_cache() -> None:
    if _cache is None:
        return
    ensure_data_dirs()
    os.makedirs(os.path.dirname(LYRIC_MAPPING_PATH), exist_ok=True)
    with open(LYRIC_MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)


def _make_key(artist: str, title: str, video_id: str | None = None) -> str:
    return f"{artist.strip().lower()}::{title.strip().lower()}::{video_id or ''}"


def get_entry(artist: str, title: str, video_id: str | None = None) -> Optional[dict]:
    cache = _load_cache()
    return cache.get(_make_key(artist, title, video_id))


def upsert_entry(
    artist: str,
    title: str,
    video_id: str | None = None,
    genie_song_id: str | None = None,
    lrc_path: str | None = None,
) -> dict:
    cache = _load_cache()
    key = _make_key(artist, title, video_id)
    current = cache.get(key, {})
    if genie_song_id:
        current["genie_song_id"] = genie_song_id
    if lrc_path:
        current["lrc_path"] = lrc_path
    current["artist"] = artist
    current["title"] = title
    current["video_id"] = video_id
    cache[key] = current
    _save_cache()
    return current
