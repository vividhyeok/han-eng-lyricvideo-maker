"""Helper for formatting upload titles."""

from __future__ import annotations

import json
import os
from typing import Dict

from app.config.paths import UPLOAD_TITLE_TEMPLATE_PATH, ensure_data_dirs

DEFAULT_TEMPLATE = "[HAN/ENG] {ARTIST} - {TITLE}"


def _load_template_config() -> Dict[str, str]:
    ensure_data_dirs()
    if os.path.exists(UPLOAD_TITLE_TEMPLATE_PATH):
        try:
            with open(UPLOAD_TITLE_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "template" in data:
                    return data
        except Exception:  # pragma: no cover - best effort read
            return {"template": DEFAULT_TEMPLATE}
    return {"template": DEFAULT_TEMPLATE}


def format_upload_title(title: str, artist: str) -> str:
    """Format a YouTube upload title using the configured template."""
    config = _load_template_config()
    template = config.get("template", DEFAULT_TEMPLATE)
    try:
        return template.format(TITLE=title, ARTIST=artist)
    except Exception:
        return DEFAULT_TEMPLATE.format(TITLE=title, ARTIST=artist)
