
import os
import sys

def find_file(name, search_paths):
    print(f"Searching for {name}...")
    for path in search_paths:
        if not os.path.exists(path):
            continue
        print(f" Checking {path}")
        for root, dirs, files in os.walk(path):
            if name in files:
                full_path = os.path.join(root, name)
                print(f" FOUND: {full_path}")
                return full_path
    print(f" NOT FOUND: {name}")
    return None

common_paths = [
    r"C:\ProgramData\chocolatey",
    r"C:\Users\user\AppData\Roaming\Python",
    r"C:\Tools",
    os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Programs"),
             ]

ffmpeg = find_file("ffmpeg.exe", common_paths)
spotdl = find_file("spotdl.exe", common_paths)
