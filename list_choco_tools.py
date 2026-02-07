
import os

target = r"C:\ProgramData\chocolatey\lib\ffmpeg\tools"
print(f"Listing {target}:")
try:
    if os.path.exists(target):
        for item in os.listdir(target):
            print(f" - {item}")
            sub = os.path.join(target, item)
            if os.path.isdir(sub):
                print(f"   Listing {sub}:")
                for subitem in os.listdir(sub):
                    print(f"    - {subitem}")
                    if subitem == "bin":
                        print(f"      (Contains bin, checking inside...)")
                        for b in os.listdir(os.path.join(sub, "bin")):
                            print(f"       ~ {b}")
    else:
        print("Path does not exist.")
except Exception as e:
    print(f"Error: {e}")
