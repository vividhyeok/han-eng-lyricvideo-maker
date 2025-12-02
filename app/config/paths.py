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
