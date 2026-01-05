"""Utility helpers for YouTube and YouTube Music IDs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse
from typing import Optional


def extract_video_id(url: str) -> Optional[str]:
    """Extract a YouTube video ID from common URL formats."""
    if not url:
        return None

    # Standard query format
    parsed = urlparse(url)
    if parsed.query:
        query = parse_qs(parsed.query)
        if "v" in query and query["v"]:
            return query["v"][0]

    # youtu.be short links
    if parsed.netloc.endswith("youtu.be"):
        path_parts = parsed.path.split("/")
        if len(path_parts) >= 2 and path_parts[1]:
            return path_parts[1]

    # music.youtube.com/watch/VIDEO_ID format
    match = re.search(r"/watch/([\\w-]{11})", parsed.path or "")
    if match:
        return match.group(1)

    # Fallback: look for 11-character ID in URL
    match = re.search(r"([\\w-]{11})", url)
    if match:
        return match.group(1)

    return None


def build_youtube_music_url(video_id: str) -> str:
    """Return a stable YouTube Music URL for a given video id."""
    return f"https://music.youtube.com/watch?v={video_id}"
