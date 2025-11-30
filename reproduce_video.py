import os
import json
from PIL import Image
from moviepy.audio.AudioClip import AudioArrayClip
import numpy as np
from app.media.video_maker import make_lyric_video

# Create dummy assets
os.makedirs("temp_test", exist_ok=True)

# 1. Dummy Audio (10 seconds silence)
# 44100 Hz, 2 channels, 10 seconds
duration = 10
sr = 44100
audio_data = np.zeros((duration * sr, 2))
audio_clip = AudioArrayClip(audio_data, fps=sr)
audio_path = "temp_test/dummy_audio.mp3"
audio_clip.write_audiofile(audio_path, fps=sr)

# 2. Dummy Album Art
img = Image.new('RGB', (500, 500), color = (73, 109, 137))
img_path = "temp_test/dummy_album.jpg"
img.save(img_path)

# 3. Dummy Lyrics JSON
lyrics_data = [
    {"start_time": 1.0, "original": "첫 번째 가사입니다", "english": "This is the first lyric"},
    {"start_time": 4.0, "original": "두 번째 가사입니다", "english": "This is the second lyric"},
    {"start_time": 7.0, "original": "마지막 가사입니다", "english": "This is the last lyric"}
]
json_path = "temp_test/dummy_lyrics.json"
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(lyrics_data, f, ensure_ascii=False)

# 4. Generate Video
output_path = "temp_test/output_video.mp4"
try:
    make_lyric_video(audio_path, img_path, json_path, output_path)
    print(f"Video generated successfully at {output_path}")
except Exception as e:
    print(f"Video generation failed: {e}")
