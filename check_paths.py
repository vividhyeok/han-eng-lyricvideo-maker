
import sys
import os
import shutil

# Mock setup to allow importing app modules
sys.path.append(os.getcwd())

try:
    from app.config import paths
    print(f"FFMPEG_PATH: {paths.FFMPEG_PATH}")
    print(f"FFPROBE_PATH: {paths.FFPROBE_PATH}")
    print(f"FFMPEG_DIR: {paths.FFMPEG_DIR}")
    
    print(f"Exists(FFMPEG_PATH): {os.path.exists(paths.FFMPEG_PATH)}")
    print(f"Exists(FFMPEG_DIR): {os.path.exists(paths.FFMPEG_DIR)}")
    
    print("-" * 20)
    print("Trying shutil.which('ffmpeg')...")
    which_ffmpeg = shutil.which("ffmpeg")
    print(f"shutil.which('ffmpeg'): {which_ffmpeg}")
    
except ImportError:
    print("Could not import app.config.paths. Make sure you are in the project root.")
except Exception as e:
    print(f"Error: {e}")
