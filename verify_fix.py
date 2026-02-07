
import sys
import os
import shutil

sys.path.append(os.getcwd())

try:
    from app.config import paths
    print(f"FFMPEG_PATH: {paths.FFMPEG_PATH}")
    print(f"FFMPEG_DIR: {paths.FFMPEG_DIR}")
    print(f"Exists: {os.path.exists(paths.FFMPEG_PATH)}")
    
    # Also verify spotdl finding logic in paths.py indirectly by checking PATH
    print(f"PATH has python scripts? {'Python314' in os.environ['PATH']}")
    print(f"shutil.which('spotdl'): {shutil.which('spotdl')}")

except Exception as e:
    print(f"Error: {e}")
