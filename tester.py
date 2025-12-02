import os
import sys

from app.config.paths import TEMP_DIR, ensure_data_dirs
from app.sources.youtube_handler import download_youtube_audio

def test_download():
    # Problematic case from user logs
    artist = "식케이 (Sik-K) & Lil Moshpit"
    title = "LOV3 (Feat. Bryan Chase & Okasian)"
    
    # Simulate ProcessManager's filename generation
    filename = f"{artist} - {title}"
    # Sanitize (simple version matching ProcessManager)
    import re
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    
    print(f"Testing filename: {filename}")
    
    # YouTube URL from logs
    youtube_url = "https://www.youtube.com/watch?v=7mjg-7ibaQA"
    
    print("Attempting download...")
    # Ensure temp directory exists
    ensure_data_dirs()
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    success = download_youtube_audio(youtube_url, filename)
    
    if success:
        print("Download reported success.")
        expected_path = os.path.join(TEMP_DIR, f"{filename}.mp3")
        if os.path.exists(expected_path):
            print(f"SUCCESS: File exists at {expected_path}")
        else:
            print(f"FAILURE: File NOT found at {expected_path}")
            # Check what actually exists
            for f in os.listdir(TEMP_DIR):
                if f.startswith(filename[:10]): # Check for partial matches
                    print(f"Found similar file: {f}")
    else:
        print("Download reported failure.")

if __name__ == "__main__":
    test_download()
