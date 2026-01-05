import json
import asyncio
import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

from app.pipeline.process_manager import ProcessManager, ProcessConfig
from app.sources.ytmusic_export_handler import load_ytmusic_export
from app.sources.youtube_utils import build_youtube_music_url, extract_video_id
from app.lyrics.lrc_resolver import resolve_lrc

def progress_callback(status, percent):
    print(f"[Progress {percent}%] {status}")

async def run_jobs():
    if not os.path.exists('batch_jobs.json'):
        print("batch_jobs.json not found.")
        return

    with open('batch_jobs.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    expanded_jobs = []
    for job in jobs:
        if isinstance(job, dict) and job.get("type") == "ytmusic_export":
            export_path = job.get("path")
            if not export_path:
                print("ytmusic_export job missing 'path'")
                continue
            try:
                tracks = load_ytmusic_export(export_path)
            except Exception as exc:
                print(f"Failed to load {export_path}: {exc}")
                continue
            for track in tracks:
                expanded_jobs.append(
                    {
                        "artist": track.artist,
                        "title": track.title,
                        "album_art_url": track.album_art_url or job.get("album_art_url", ""),
                        "youtube_url": track.source_url or build_youtube_music_url(track.video_id),
                        "video_id": track.video_id,
                        "prefer_youtube": True,
                    }
                )
        else:
            expanded_jobs.append(job)

    manager = ProcessManager(progress_callback)

    for job in expanded_jobs:
        if not job.get('album_art_url'):
            print(f"Skipping {job.get('artist')} - {job.get('title')}: Missing album_art_url. Please fill it in batch_jobs.json")
            continue

        print(f"Processing {job['artist']} - {job['title']}...")

        video_id = job.get("video_id") or extract_video_id(job.get("youtube_url", ""))
        lrc_path = job.get("lrc_path")
        if not lrc_path:
            lrc_path = resolve_lrc(job["title"], job["artist"], video_id)
            if not lrc_path:
                print(f"Skipping {job['artist']} - {job['title']}: Missing lyrics.")
                continue
            job["lrc_path"] = lrc_path
        
        config = ProcessConfig(
            title=job['title'],
            artist=job['artist'],
            album_art_url=job['album_art_url'],
            youtube_url=job['youtube_url'],
            video_id=video_id,
            lrc_path=job.get('lrc_path'),
            output_mode=job.get("output_mode", "video"),
            prefer_youtube=job.get("prefer_youtube", True)
        )
        
        try:
            await manager.process_async(config)
            print(f"Successfully processed {job['artist']} - {job['title']}")
        except Exception as e:
            print(f"Error processing {job['artist']} - {job['title']}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_jobs())
