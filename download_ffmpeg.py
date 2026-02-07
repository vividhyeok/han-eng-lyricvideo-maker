
import os
import urllib.request
import zipfile
import shutil
import sys

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
DEST_DIR = os.path.join(os.getcwd(), "bin")
FFMPEG_DIR = os.path.join(DEST_DIR, "ffmpeg")

def download_ffmpeg():
    if os.path.exists(FFMPEG_DIR):
        print(f"FFmpeg directory already exists at {FFMPEG_DIR}")
        return

    os.makedirs(DEST_DIR, exist_ok=True)
    zip_path = os.path.join(DEST_DIR, "ffmpeg.zip")

    print(f"Downloading FFmpeg from {FFMPEG_URL}...")
    try:
        # Use a user agent to avoid potential 403s
        req = urllib.request.Request(
            FFMPEG_URL, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Download complete.")

        print("Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(DEST_DIR)
        
        # Renaissance of the folder
        extracted_folders = [f for f in os.listdir(DEST_DIR) if f.startswith("ffmpeg-") and os.path.isdir(os.path.join(DEST_DIR, f))]
        if extracted_folders:
            src = os.path.join(DEST_DIR, extracted_folders[0])
            os.rename(src, FFMPEG_DIR)
            print(f"Extracted to {FFMPEG_DIR}")
        else:
            print("Could not find extracted folder.")

        os.remove(zip_path)
        print("Cleanup done.")

    except Exception as e:
        print(f"Error downloading ffmpeg: {e}")
        # dummy creation for test if download fails (fallback)
        # os.makedirs(FFMPEG_DIR, exist_ok=True)

if __name__ == "__main__":
    download_ffmpeg()
