"""Simple smoke test for YT Music export expansion."""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.sources.ytmusic_export_handler import load_ytmusic_export
from app.sources.youtube_utils import build_youtube_music_url


def main(export_path: str):
    tracks = load_ytmusic_export(export_path)
    jobs = []
    for track in tracks:
        jobs.append(
            {
                "title": track.title,
                "artist": track.artist,
                "youtube_url": track.source_url or build_youtube_music_url(track.video_id),
                "video_id": track.video_id,
                "album_art_url": track.album_art_url or "(none)",
            }
        )

    print(json.dumps(jobs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "ytmusic_export.sample.json")
    main(path)
