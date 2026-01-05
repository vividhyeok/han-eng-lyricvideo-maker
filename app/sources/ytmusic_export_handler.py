"""Parse and validate YouTube Music export JSON files."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

from app.sources.youtube_utils import build_youtube_music_url


@dataclass
class TrackItem:
    title: str
    artist: str
    video_id: str
    source_url: str
    album: Optional[str] = None
    album_art_url: Optional[str] = None
    duration_ms: Optional[int] = None


def _normalize_item(raw: dict) -> TrackItem:
    if not isinstance(raw, dict):
        raise ValueError("Each item must be an object.")

    video_id = raw.get("videoId")
    title = raw.get("title")
    artist = raw.get("artist")
    if not all([video_id, title, artist]):
        raise ValueError("Track item missing required fields: videoId, title, artist.")

    album_art = None
    thumbnails = raw.get("thumbnails") or []
    if isinstance(thumbnails, list) and thumbnails:
        first_thumb = thumbnails[0]
        if isinstance(first_thumb, dict):
            album_art = first_thumb.get("url") or first_thumb.get("src")

    return TrackItem(
        title=str(title).strip(),
        artist=str(artist).strip(),
        video_id=str(video_id).strip(),
        source_url=raw.get("sourceUrl") or build_youtube_music_url(str(video_id).strip()),
        album=raw.get("album"),
        album_art_url=album_art,
        duration_ms=raw.get("durationMs"),
    )


def load_ytmusic_export(path: str) -> List[TrackItem]:
    """Load and validate a YouTube Music export JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Export file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Invalid export file: expected a JSON object.")

    if data.get("schema_version") != 1:
        raise ValueError("Unsupported schema_version. Expected 1.")

    if data.get("source") not in ("ytmusic", None):
        raise ValueError("Invalid source. Expected 'ytmusic'.")

    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Export file must include a non-empty 'items' array.")

    normalized: List[TrackItem] = []
    for item in items:
        normalized.append(_normalize_item(item))

    return normalized
