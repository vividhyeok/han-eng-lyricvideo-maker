
import sys
import os
sys.path.append(os.getcwd())

try:
    import app.config.paths as paths
    import shutil
    
    print("-" * 20)
    print(f"PATH: {os.environ['PATH']}")
    print("-" * 20)
    
    print(f"FFMPEG_PATH in config: {paths.FFMPEG_PATH}")
    print(f"FFMPEG_DIR in config: {paths.FFMPEG_DIR}")
    
    spotdl_path = shutil.which("spotdl")
    print(f"spotdl found at: {spotdl_path}")
    
    if paths.FFMPEG_PATH and os.path.exists(paths.FFMPEG_PATH) and spotdl_path:
        print("VERIFICATION SUCCESS: Both ffmpeg and spotdl are found.")
    else:
        print("VERIFICATION FAILED: Missing dependencies.")

except Exception as e:
    print(f"Error during verification: {e}")
