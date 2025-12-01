import os
from typing import Dict, List, Optional, Sequence, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.fx import all as vfx
import numpy as np
import re
import json
import traceback

def draw_outlined_text(draw: ImageDraw.ImageDraw, pos: Tuple[float, float], text: str, font: ImageFont.ImageFont,
                       text_color=(255, 255, 255), outline_color=(0, 0, 0), outline_width=3) -> None:
    """테두리가 있는 텍스트 그리기"""
    x, y = pos
    x = int(round(x))
    y = int(round(y))
    # 테두리 그리기
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            draw.text((x + offset_x, y + offset_y), text, font=font, fill=outline_color)
    # 메인 텍스트 그리기
    draw.text((x, y), text, font=font, fill=text_color)

def resolve_font_path() -> Optional[str]:
    """가사 렌더링에 사용할 폰트를 탐색"""
    env_font = os.getenv("LYRIC_FONT_PATH")
    if env_font and os.path.exists(env_font):
        return env_font

    candidates: Sequence[str] = (
        os.path.join(os.getcwd(), "assets", "fonts", "NotoSansCJK-Regular.otf"),
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgunbd.ttf",
    )

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _load_font(font_path: Optional[str], size: int) -> ImageFont.ImageFont:
    fallback_candidates = (
        font_path,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    )

    for candidate in fallback_candidates:
        if not candidate:
            continue
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue

    return ImageFont.load_default()


def prepare_fonts() -> Tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
    font_path = resolve_font_path()
    return _load_font(font_path, 72), _load_font(font_path, 48)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    if hasattr(draw, "textlength"):
        return draw.textlength(text, font=font)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def _split_long_token(token: str, draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, max_width: float) -> List[str]:
    if not token:
        return [""]
    buffer = ""
    lines: List[str] = []
    for char in token:
        tentative = buffer + char
        if _text_width(draw, tentative, font) <= max_width or not buffer:
            buffer = tentative
        else:
            lines.append(buffer)
            buffer = char
    if buffer:
        lines.append(buffer)
    return lines


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: float) -> List[str]:
    if not text:
        return [""]

    words = text.split()
    lines: List[str] = []
    current_line = ""

    for word in words:
        tentative = word if not current_line else f"{current_line} {word}"
        if _text_width(draw, tentative, font) <= max_width:
            current_line = tentative
            continue

        if current_line:
            lines.append(current_line)

        if _text_width(draw, word, font) <= max_width:
            current_line = word
        else:
            split_tokens = _split_long_token(word, draw, font, max_width)
            if split_tokens:
                lines.extend(split_tokens[:-1])
                current_line = split_tokens[-1]
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    if not lines:
        return [text]
    return lines


def _draw_multiline_centered(draw: ImageDraw.ImageDraw, lines: List[str], font: ImageFont.ImageFont,
                             frame_width: int, center_y: float, spacing_ratio: float = 0.3) -> None:
    lines = [line for line in lines if line is not None]
    if not lines:
        return

    heights = [_text_height(draw, line, font) for line in lines]
    if not heights:
        return

    base_spacing = max(int(heights[0] * spacing_ratio), 10)
    total_height = sum(heights) + base_spacing * (len(lines) - 1)
    start_y = center_y - total_height / 2
    y_cursor = start_y

    for line, height in zip(lines, heights):
        width = _text_width(draw, line, font)
        x = (frame_width - width) / 2
        draw_outlined_text(draw, (x, y_cursor), line, font)
        y_cursor += height + base_spacing


def prepare_base_frame(background_img: Image.Image) -> Image.Image:
    frame = background_img.convert('RGBA')
    # Increased blur radius for minimalist look
    blurred = frame.filter(ImageFilter.GaussianBlur(radius=30))
    # Darker overlay for better contrast
    overlay = Image.new('RGBA', frame.size, (0, 0, 0, 160))
    return Image.alpha_composite(blurred, overlay)


def create_lyric_frame(base_frame: Image.Image, lyric: Dict[str, str], fonts: Tuple[ImageFont.ImageFont, ImageFont.ImageFont],
                       max_width_ratio: float = 0.86) -> Image.Image:
    """각 가사 프레임 생성"""
    frame = base_frame.copy()
    draw = ImageDraw.Draw(frame)

    korean_font, english_font = fonts
    max_text_width = frame.width * max_width_ratio

    original_text = lyric.get('original', '')
    translated_text = lyric.get('english', '')

    korean_lines = _wrap_text(draw, original_text, korean_font, max_text_width)
    english_lines = _wrap_text(draw, translated_text, english_font, max_text_width)

    _draw_multiline_centered(draw, korean_lines, korean_font, frame.width, frame.height * 0.45)
    _draw_multiline_centered(draw, english_lines, english_font, frame.width, frame.height * 0.72)

    return frame.convert('RGB')

def parse_srt_file(srt_path: str):
    """SRT 파일 파싱"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    segments = content.strip().split('\n\n')
    lyrics_data = []
    
    for segment in segments:
        lines = segment.split('\n')
        if len(lines) >= 3:
            times = lines[1].split(' --> ')
            start_time = times[0].replace(',', '.')
            end_time = times[1].replace(',', '.')
            text = '\n'.join(lines[2:])  # 한글 가사와 영어 가사 모두 포함
            lyrics_data.append({
                'start': start_time,
                'end': end_time,
                'text': text
            })
    
    return lyrics_data

def make_lyric_video(audio_path: str, album_art_path: str, lyrics_json_path: str, output_path: str):
    """리릭 비디오 생성"""
    try:
        print("[DEBUG] 리릭 비디오 생성 시작")

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        os.makedirs('temp', exist_ok=True)

        audio = None
        background_clip = None
        final_clip = None
        clips: List[ImageClip] = []

        try:
            # 오디오 로드
            audio = AudioFileClip(audio_path)
            duration = audio.duration

            # 앨범아트 로드 및 크기 조정
            with Image.open(album_art_path) as album_image:
                background_img = album_image.convert('RGB')
                background_img = background_img.resize((1920, 1080), Image.Resampling.LANCZOS)
            lyric_base_frame = prepare_base_frame(background_img)
            fonts = prepare_fonts()

            # 가사 JSON 로드 및 정렬
            with open(lyrics_json_path, 'r', encoding='utf-8') as f:
                lyrics_data = json.load(f)

            if not lyrics_data:
                raise ValueError("가사 데이터가 비어 있습니다.")

            lyrics_data.sort(key=lambda item: float(item.get('start_time', 0.0)))

            # 각 가사에 대한 클립 생성
            for index, lyric in enumerate(lyrics_data):
                frame = create_lyric_frame(lyric_base_frame, lyric, fonts)
                frame_array = np.array(frame, dtype=np.uint8)

                start_time = float(lyric.get('start_time', 0.0))
                if index < len(lyrics_data) - 1:
                    next_start = float(lyrics_data[index + 1].get('start_time', duration))
                else:
                    next_start = duration

                next_start = max(next_start, start_time + 0.1)
                clip_duration = max(0.1, next_start - start_time)

                # Manual fade-in effect (0.5s) using set_opacity
                clip = ImageClip(frame_array).set_duration(clip_duration).set_start(start_time)
                clip = clip.fx(vfx.fadein, 0.5)
                clips.append(clip)

            # 배경 클립 생성
            background_clip = ImageClip(np.array(background_img, dtype=np.uint8)).set_duration(duration)

            # 모든 클립 합성
            final_clip = CompositeVideoClip([background_clip] + clips, size=(1920, 1080)).set_audio(audio)

            temp_audiofile = os.path.join('temp', 'lyric-video-temp-audio.m4a')
            threads = max(1, (os.cpu_count() or 4) // 2)

            # 비디오 파일 생성
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                audio_bitrate='192k',
                bitrate='6000k',
                preset='fast',
                threads=threads,
                ffmpeg_params=['-crf', '18', '-pix_fmt', 'yuv420p'],
                temp_audiofile=temp_audiofile,
                remove_temp=True,
            )

            print(f"[DEBUG] 리릭 비디오 생성 완료: {output_path}")

        finally:
            for clip in clips:
                clip.close()
            if background_clip is not None:
                background_clip.close()
            if final_clip is not None:
                final_clip.close()
            if audio is not None:
                audio.close()

    except Exception as e:
        print(f"[ERROR] 비디오 생성 실패: {str(e)}")
        traceback.print_exc()
        raise e

def convert_timestamp_to_seconds(timestamp: str) -> float:
    """SRT 타임스탬프를 초 단위로 변환"""
    hours, minutes, seconds = timestamp.replace(',', '.').split(':')
    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

def convert_milliseconds_to_seconds(milliseconds: float) -> float:
    """밀리초를 초 단위로 변환"""
    return milliseconds / 1000

def parse_lyrics_json(json_path: str) -> List[dict]:
    """JSON 가사 파일 파싱"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)