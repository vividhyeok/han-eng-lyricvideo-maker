import sys
import os
import asyncio
import traceback

# Add project root to path
sys.path.append(os.getcwd())

from app.config import paths
from app.sources.youtube_handler import download_youtube_audio
from app.sources.genie_handler import search_genie_songs

async def test_step_0_env():
    print("\n[Step 0] Environment Check")
    print(f"FFMPEG_PATH: {paths.FFMPEG_PATH}")
    print(f"Exists: {os.path.exists(paths.FFMPEG_PATH) if paths.FFMPEG_PATH else False}")
    import shutil
    print(f"spotdl: {shutil.which('spotdl')}")

async def test_step_1_search(query):
    print(f"\n[Step 1] Search '{query}'")
    results = search_genie_songs(query, limit=1)
    print(f"Found {len(results)} results.")
    if results:
        # results structure: (title, id, extra_info, album_art, duration)
        print(f"Top result: {results[0][0]} - {results[0][2]}")
        return results[0]
    return None

async def test_step_2_download(url, filename):
    print(f"\n[Step 2] Download Audio from {url}")
    try:
        path = download_youtube_audio(url, filename)
        if path and os.path.exists(path):
            print(f"Download success: {path}")
            return path
        else:
            print("Download returned None or file missing.")
    except Exception as e:
        print(f"Download Error: {e}")
        traceback.print_exc()

from app.lyrics.openai_handler import parse_lrc_and_translate
from app.media.video_maker import make_lyric_video

# ... (previous imports)

async def test_step_3_lyrics(lrc_path, json_path, duration):
    print(f"\n[Step 3] Lyrics Processing")
    # Create dummy LRC if not exists
    if not os.path.exists(lrc_path):
        print("Creating dummy LRC for testing...")
        with open(lrc_path, "w", encoding="utf-8") as f:
            f.write("[00:00.00]Test Song - Test Artist\n")
            f.write("[00:05.00]This is line 1\n")
            f.write("[00:10.00]This is line 2\n")
    
    try:
        result_path = await parse_lrc_and_translate(lrc_path, json_path, duration)
        if os.path.exists(result_path):
            print(f"Lyrics processed: {result_path}")
            return result_path
    except Exception as e:
        print(f"Lyrics Error: {e}")
        traceback.print_exc()

async def test_step_5_video(audio_path, image_path, json_path, output_path):
    print(f"\n[Step 5] Video Assembly")
    # Create dummy image if not exists (in case download failed or skipping)
    if not os.path.exists(image_path):
        print("Creating dummy album art...")
        from PIL import Image
        img = Image.new('RGB', (600, 600), color = 'red')
        img.save(image_path)

    try:
        # Check if files exist
        if not os.path.exists(audio_path): raise Exception("Audio not found")
        if not os.path.exists(json_path): raise Exception("JSON Lyrics not found")
        
        make_lyric_video(audio_path, image_path, json_path, output_path)
        if os.path.exists(output_path):
            print(f"Video generated: {output_path}")
            return output_path
    except Exception as e:
        print(f"Video Error: {e}")
        traceback.print_exc()

async def main():
    print("=== Pipeline Debug Start ===")
    
    # Setup paths
    temp_dir = paths.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    
    # 0. Env
    await test_step_0_env()
    
    # 1. Search
    query = "Yin and Yang"
    song_info = await test_step_1_search(query) # returns (title, id, extra, art, dur)
    
    # 2. Download
    target_url = "https://youtu.be/dbBwv38Ycaw?si=Yl-IOnQAPY7lH-Mw"
    filename = "test_yin_and_yang"
    audio_path = await test_step_2_download(target_url, filename)
    
    # Prepare dummy paths for next steps
    lrc_path = os.path.join(temp_dir, f"{filename}.lrc")
    json_path = os.path.join(temp_dir, f"{filename}.json")
    image_path = os.path.join(temp_dir, f"{filename}.jpg")
    output_path = os.path.join(temp_dir, f"{filename}_output.mp4")
    
    # Mock duration if audio exists
    duration = 30.0 
    if audio_path and os.path.exists(audio_path):
        from app.media.video_maker import get_audio_duration
        duration = get_audio_duration(audio_path)
    
    # 3. Lyrics
    await test_step_3_lyrics(lrc_path, json_path, duration)
    
    # 5. Video (Skipping step 4 as it's internal logic)
    # Use real album art if search found it, otherwise dummy
    if song_info and song_info[3]:
        # Try to download real art? or just use dummy for speed.
        # Let's use dummy for reliability of the pipeline test itself, unless we want to test art download.
        pass 
        
    await test_step_5_video(audio_path or "missing.mp3", image_path, json_path, output_path)

if __name__ == "__main__":
    asyncio.run(main())
