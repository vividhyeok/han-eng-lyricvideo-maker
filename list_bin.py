
import os

target = r"C:\ProgramData\chocolatey\bin"
print(f"Listing {target}:")
try:
    if os.path.exists(target):
        found = False
        for item in os.listdir(target):
            if "ffmpeg" in item.lower():
                print(f" - {item}")
                found = True
        if not found:
            print("No ffmpeg related files found.")
    else:
        print("Path C:\\ProgramData\\chocolatey\\bin does not exist.")
except Exception as e:
    print(f"Error: {e}")
