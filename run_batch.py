import json
import asyncio
import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

from app.pipeline.process_manager import ProcessManager, ProcessConfig

def progress_callback(status, percent):
    print(f"[Progress {percent}%] {status}")

async def run_jobs():
    if not os.path.exists('batch_jobs.json'):
        print("batch_jobs.json not found.")
        return

    with open('batch_jobs.json', 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    manager = ProcessManager(progress_callback)

    for job in jobs:
        if not job['album_art_url']:
            print(f"Skipping {job['artist']} - {job['title']}: Missing album_art_url. Please fill it in batch_jobs.json")
            continue

        print(f"Processing {job['artist']} - {job['title']}...")
        
        config = ProcessConfig(
            title=job['title'],
            artist=job['artist'],
            album_art_url=job['album_art_url'],
            youtube_url=job['youtube_url'],
            lrc_path=job['lrc_path'],
            output_mode="video",
            prefer_youtube=True
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
