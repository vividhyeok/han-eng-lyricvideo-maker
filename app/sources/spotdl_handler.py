"""spotDL handler for downloading audio via the CLI interface."""

from __future__ import annotations

import os
import shlex
import subprocess
from shutil import which
from typing import Optional

from app.config.paths import TEMP_DIR, ensure_data_dirs


def _ensure_spotdl_exists() -> None:
    """Raise helpful error when spotdl CLI is missing."""
    if which("spotdl") is None:
        raise FileNotFoundError(
            "spotdl CLI not found. Install with 'pip install spotdl' and ensure it is on PATH."
        )


def _run_spotdl_download(query: str, output_template: str) -> subprocess.CompletedProcess[str]:
    """Execute spotdl CLI download command."""
    cmd = [
        "spotdl",
        "download",
        query,
        "--output",
        output_template,
        "--format",
        "mp3",
        "--bitrate",
        "320k",
    ]
    print(f"[DEBUG] spotDL CLI 실행: {' '.join(shlex.quote(part) for part in cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def download_audio_with_spotdl(artist: str, title: str, output_dir: str = TEMP_DIR) -> Optional[str]:
    """Download audio using spotDL CLI.

    Args:
        artist: Artist name
        title: Track title
        output_dir: Directory for the downloaded audio file

    Returns:
        Path to downloaded MP3 or None when the download failed
    """
    try:
        _ensure_spotdl_exists()
        ensure_data_dirs()
        os.makedirs(output_dir, exist_ok=True)

        query = f"{artist} - {title}"
        output_template = os.path.join(output_dir, "{artist} - {title}.{output-ext}")

        result = _run_spotdl_download(query, output_template)
        if result.returncode != 0:
            print(f"[ERROR] spotDL CLI 실패: {result.stderr.strip()}")
            return None

        expected_file = os.path.join(output_dir, f"{artist} - {title}.mp3")
        if os.path.exists(expected_file):
            print(f"[DEBUG] spotDL 다운로드 완료: {expected_file}")
            return expected_file

        print(f"[ERROR] spotDL 다운로드 결과 파일을 찾을 수 없습니다: {expected_file}")
        return None

    except Exception as exc:
        print(f"[ERROR] spotDL 다운로드 실패: {exc}")
        import traceback
        traceback.print_exc()
        return None


def download_audio_simple(artist: str, title: str, output_dir: str = TEMP_DIR) -> Optional[str]:
    """Backward-compatible alias that wraps ``download_audio_with_spotdl``."""

    return download_audio_with_spotdl(artist, title, output_dir)
