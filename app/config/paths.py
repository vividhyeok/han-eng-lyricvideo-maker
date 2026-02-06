"""Centralized filesystem paths for runtime data."""

from __future__ import annotations

import os
from typing import Iterable

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DATA_DIR = os.path.join(BASE_DIR, "data")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
LYRICS_DIR = os.path.join(DATA_DIR, "lyrics")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
CONFIG_DIR = os.path.join(DATA_DIR, "config")

TRANSLATION_CACHE_PATH = os.path.join(CACHE_DIR, "translation_cache.json")
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.json")

# FFMPEG paths
def _find_ffmpeg() -> str | None:
    """Find ffmpeg.exe in common locations."""
    # Check if already in PATH
    import shutil
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path

    # Common winget location
    winget_packages_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.exists(winget_packages_dir):
        import glob
        # Search for any gyan.ffmpeg package
        patterns = [
            os.path.join(winget_packages_dir, "Gyan.FFmpeg*", "**", "ffmpeg.exe"),
            os.path.join(winget_packages_dir, "Gyan.FFmpeg*", "bin", "ffmpeg.exe"),
        ]
        for pattern in patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                return matches[0]

    # Essentials build in project root (as per existing FFMPEG_DIR)
    local_ffmpeg = os.path.join(BASE_DIR, "ffmpeg-8.0.1-essentials_build", "bin", "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg

    return None


FFMPEG_PATH = _find_ffmpeg()
FFPROBE_PATH = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe") if FFMPEG_PATH else None
FFMPEG_DIR = os.path.dirname(FFMPEG_PATH) if FFMPEG_PATH else None

# Configure pydub if ffmpeg is found
if FFMPEG_PATH:
    try:
        import sys
        import io
        from contextlib import redirect_stderr

        # Silence pydub's initial FFmpeg check warning
        f = io.StringIO()
        with redirect_stderr(f):
            from pydub import AudioSegment
        
        AudioSegment.converter = FFMPEG_PATH
        # Also try to set ffprobe specifically if it exists
        if FFMPEG_PATH.endswith("ffmpeg.exe"):
            probe_path = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe")
            if os.path.exists(probe_path):
                AudioSegment.ffprobe = probe_path
    except ImportError:
        pass

# Legacy locations retained for compatibility (do not remove without migration plan).
LEGACY_TEMP_DIR = os.path.join(BASE_DIR, "temp")
LEGACY_LYRICS_DIR = os.path.join(BASE_DIR, "result")


def _ensure_directories(paths: Iterable[str]) -> None:
    for path in paths:
        os.makedirs(path, exist_ok=True)


def ensure_data_dirs() -> None:
    """Create the runtime data directories if they are missing."""
    _ensure_directories((DATA_DIR, TEMP_DIR, OUTPUT_DIR, LYRICS_DIR, CACHE_DIR, CONFIG_DIR))


ensure_data_dirs()
