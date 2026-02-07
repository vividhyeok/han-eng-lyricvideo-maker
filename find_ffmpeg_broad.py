
import os

root_dir = r"C:\ProgramData\chocolatey"
target = "ffmpeg.exe"

print(f"Searching for {target} in {root_dir}")
for root, dirs, files in os.walk(root_dir):
    if target in files:
        print(f"FOUND: {os.path.join(root, target)}")
    
    # Optional: print dirs to debug structure
    # if "ffmpeg" in root.lower():
    #     print(f"Traversing: {root}")
