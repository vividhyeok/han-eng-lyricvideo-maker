import json
import os
import re
import traceback
from itertools import zip_longest
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 선택적 의존성
    load_dotenv = lambda: None

try:
    from pydub import AudioSegment  # 오디오 길이 측정을 위해 필요 (pip install pydub)
except ImportError:  # pragma: no cover - 선택적 의존성
    AudioSegment = None

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - 선택적 의존성
    AsyncOpenAI = None

# 환경변수(.env) 로드 및 OpenAI API 키 설정
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = None
if AsyncOpenAI and OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

TRANSLATION_CACHE_PATH = os.path.join("temp", "translation_cache.json")
_translation_cache: Optional[Dict[str, str]] = None

def _ensure_cache_loaded() -> None:
    global _translation_cache
    if _translation_cache is not None:
        return

    try:
        if os.path.exists(TRANSLATION_CACHE_PATH):
            with open(TRANSLATION_CACHE_PATH, "r", encoding="utf-8") as cache_file:
                _translation_cache = json.load(cache_file)
        else:
            _translation_cache = {}
    except Exception:
        _translation_cache = {}


def _save_cache() -> None:
    if _translation_cache is None:
        return

    os.makedirs(os.path.dirname(TRANSLATION_CACHE_PATH), exist_ok=True)
    with open(TRANSLATION_CACHE_PATH, "w", encoding="utf-8") as cache_file:
        json.dump(_translation_cache, cache_file, ensure_ascii=False, indent=2)


def _get_cached_translation(lyric: str) -> Optional[str]:
    _ensure_cache_loaded()
    assert _translation_cache is not None
    return _translation_cache.get(lyric)


def _update_cache(original: str, translated: str) -> None:
    _ensure_cache_loaded()
    assert _translation_cache is not None
    _translation_cache[original] = translated


async def translate_lyrics(lyrics: List[str]) -> List[str]:
    """가사를 문맥 기반으로 자연스럽게 영어 의역"""
    if not lyrics:
        return []

    # 1. Check cache and identify pending lines
    results: List[Optional[str]] = []
    pending_indices: List[int] = []
    pending_lyrics: List[str] = []

    for idx, lyric in enumerate(lyrics):
        stripped = lyric.strip()
        if not stripped:
            results.append("")
            continue

        if is_english(stripped):
            results.append(stripped)
            continue

        # For better context, we might want to re-translate even if cached,
        # but to save costs/time, we'll use cache if available.
        # If the user wants to force re-translation, they can clear the cache.
        cached = _get_cached_translation(stripped)
        if cached:
            results.append(cached)
            continue

        results.append(None)
        pending_indices.append(idx)
        pending_lyrics.append(stripped)

    # 2. Translate pending lines with full context
    if pending_lyrics and client:
        try:
            # We send the *full* original lyrics as context, but ask to translate only the pending ones?
            # Actually, to get the best context, we should probably send the whole song
            # and ask for the whole song back, or at least the relevant parts.
            # But that might be expensive if we only need a few lines.
            # However, the user asked for "better context".
            # Let's try to translate the *pending* lines, but provide the *surrounding* lines as context if possible.
            # Or simpler: Just send the list of pending lyrics.
            # Wait, if we just send pending lyrics [Line 1, Line 5, Line 10], we lose context.
            # The best way for "context" is to send the WHOLE block of lyrics that needs translation.
            # If the cache is sparse (some lines cached, some not), it's tricky.
            # Let's assume for "better translation" we should prioritize the batch translation.
            
            # Strategy: If there are pending lines, we will send the *entire* input list to the LLM
            # to ensure full context, but we only *use* (and pay attention to) the lines we need?
            # No, that's wasteful if 90% is cached.
            
            # Compromise: Send the pending lyrics list. 
            # BUT the user specifically asked for "context-aware".
            # If I just send isolated pending lines, I lose context.
            # Let's try to send the *entire* lyrics list to the API if we have *any* pending lines,
            # and just update the cache for all of them. 
            # This ensures consistency.
            
            # However, to avoid re-translating already English lines or empty lines,
            # we can filter those out or just include them and let the LLM handle it.
            
            # Let's go with: Send ALL lyrics to OpenAI to get the best flow.
            # We will ignore the cache for the purpose of generating the translation context,
            # but we can still respect the cache if we want. 
            # Given the user request "fix translation to be more natural", 
            # re-translating everything is probably safer to ensure flow.
            # Let's overwrite the results with the new full-context translation.
            
            translations = await _translate_with_openai(lyrics)
            
            # Update results and cache
            # We map back to the original indices
            if len(translations) == len(lyrics):
                results = translations
                for original, translated in zip(lyrics, translations):
                    if original.strip() and not is_english(original.strip()):
                        _update_cache(original.strip(), translated)
            else:
                # Fallback if counts don't match: try to map pending only?
                # If counts don't match, we might have an issue.
                # Let's just fill in what we can or fallback to original.
                print(f"[WARN] Translation count mismatch: Input {len(lyrics)} vs Output {len(translations)}")
                # Try to use what we have? Or just return original for mismatch.
                # Let's try to use the pending logic as a fallback if the full batch fails?
                # No, let's just return the translations we got, padded or truncated.
                results = translations[:len(lyrics)] + [lyrics[i] for i in range(len(translations), len(lyrics))]

        except Exception as exc:
            print(f"[DEBUG] Translation service failed: {exc}")
            # Fallback to original for None entries
            pass

    # Fill any remaining Nones with original
    final_output = []
    for i, res in enumerate(results):
        if res is None:
            final_output.append(lyrics[i])
        else:
            final_output.append(res)

    if pending_indices or (client and lyrics): # Save if we did anything
        _save_cache()

    return final_output


async def _translate_with_openai(lyrics: List[str]) -> List[str]:
    """Translate lyrics using selected AI model"""
    if not lyrics:
        return []

    artist = os.getenv('CURRENT_ARTIST', 'Unknown Artist')
    title = os.getenv('CURRENT_TITLE', 'Unknown Song')

    # Get selected model from config
    from app.config.config_manager import get_config
    from app.lyrics.ai_models import create_model
    
    config = get_config()
    model_id = config.get_translation_model()
    
    print(f"[DEBUG] Using translation model: {model_id}")
    
    # Create model instance
    model = create_model(model_id)
    
    if not model or not model.is_available():
        print(f"[WARN] Model {model_id} not available, returning original lyrics")
        return lyrics
    
    try:
        translated = await model.translate(lyrics, artist, title)
        
        # Clean up translations
        from app.lyrics.openai_handler import clean_translation
        cleaned = [clean_translation(t) if isinstance(t, str) else str(t) for t in translated]
        return cleaned
        
    except Exception as e:
        print(f"[ERROR] Translation failed with {model_id}: {e}")
        return lyrics

def is_english(text: str) -> bool:
    """텍스트가 100% 영어로만 이루어져 있는지 확인 (숫자, 특수문자 포함)"""
    if not text or not text.strip():
        return True
    
    # 한글이 하나라도 있으면 False
    if re.search(r'[가-힣]', text):
        return False
    
    # 영어, 숫자, 공백, 일반 특수문자만 있으면 True
    return all(char.isascii() or char.isspace() for char in text)

def clean_translation(text: str) -> str:
    """번역된 텍스트 정리"""
    # 따옴표, 메타 텍스트, 특수문자 정리
    text = text.strip()
    # 번역 메타 텍스트 제거
    text = re.sub(r'translates to|in English:', '', text)
    # 불필요한 따옴표와 마침표 제거
    text = re.sub(r'^["\']+|["\']+$|\\"|\.+$', '', text)
    # 한글이 그대로 있는 경우 처리
    if re.search(r'[가-힣]', text):
        return "Translation error"
    return text.strip()

def convert_timestamp(timestamp: str) -> float:
    """LRC 타임스탬프를 초 단위로 변환"""
    try:
        minutes, seconds = timestamp.split(':')
        return float(minutes) * 60 + float(seconds)
    except:
        return 0

def format_time(seconds: float) -> str:
    """초 단위 시간을 LRC 타임스탬프 형식으로 변환"""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:05.2f}"

def seconds_to_srt_timestamp(seconds):
    """
    초 단위의 시간을 SRT 형식의 "HH:MM:SS,mmm" 문자열로 변환합니다.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{sec:02d},{milliseconds:03d}"

async def parse_lrc_and_translate(lrc_filepath: str, json_filepath: str) -> str:
    try:
        # LRC 파일 존재 확인
        if not os.path.exists(lrc_filepath):
            raise FileNotFoundError(f"LRC 파일을 찾을 수 없습니다: {lrc_filepath}")

        with open(lrc_filepath, 'r', encoding='utf-8') as f:
            lrc_content = f.read()
            
        # 첫 가사 시간 찾기
        first_lyric_time = None
        for line in lrc_content.split('\n'):
            if line.startswith('[') and ']' in line:
                first_lyric_time = line[1:line.index(']')]
                if first_lyric_time:
                    break
        
        # 환경 변수에서 아티스트와 제목 가져오기
        artist = os.getenv('CURRENT_ARTIST', '아티스트')
        title = os.getenv('CURRENT_TITLE', '제목')
        
        # 아티스트-제목 형식의 가사 추가
        if first_lyric_time:
            intro_lyric = f"[{first_lyric_time}]{artist} - {title}\n"
            modified_lrc = intro_lyric + lrc_content
        else:
            modified_lrc = lrc_content
        
        # 가사 데이터 추출 및 번역
        lyrics_data: List[Dict[str, str]] = []
        pending_texts: List[str] = []

        for line in modified_lrc.split('\n'):
            if line.startswith('[') and ']' in line:
                try:
                    time_str = line[1:line.index(']')]
                    text = line[line.index(']') + 1:].strip()

                    if not text:
                        continue

                    seconds = convert_timestamp(time_str)
                    lyrics_data.append({
                        'start_time': seconds,
                        'original': text
                    })
                    pending_texts.append(text)
                except Exception as e:
                    print(f"라인 처리 중 오류: {e}")
                    continue

        translations = await translate_lyrics(pending_texts) if pending_texts else []

        for entry, translated_text in zip_longest(lyrics_data, translations, fillvalue=""):
            if entry is None:
                continue
            entry['english'] = translated_text if translated_text else entry['original']

        # 시간순 정렬
        lyrics_data.sort(key=lambda x: x['start_time'])

        # JSON 파일로 저장
        os.makedirs(os.path.dirname(json_filepath), exist_ok=True)
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(lyrics_data, f, ensure_ascii=False, indent=2)

        print(f"[DEBUG] JSON 파일 생성 완료: {json_filepath}")
        return json_filepath  # json_filepath 반환

    except Exception as e:
        print(f"[ERROR] LRC 파싱/번역 오류: {str(e)}")
        traceback.print_exc()
        raise

def save_lyrics_json(lyrics_data: List[Dict], output_path: str):
    """가사 데이터를 JSON 형식으로 저장"""
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(lyrics_data, f, ensure_ascii=False, indent=2)

async def generate_srt_from_lrc(lrc_filepath, srt_filepath, audio_filepath=None, default_duration=3.0):
    """
    LRC 파일을 SRT 형식으로 변환하고 번역하는 비동기 함수
    """
    # 오디오 파일 길이 측정 (옵션)
    total_duration = None
    if audio_filepath and os.path.exists(audio_filepath) and AudioSegment:
        try:
            audio = AudioSegment.from_file(audio_filepath)
            total_duration = len(audio) / 1000.0  # 초 단위
        except Exception as e:
            print("오디오 길이 측정 실패:", e)
    
    # LRC 파일 읽기
    with open(lrc_filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # LRC 라인 파싱
    subtitles = []
    time_pattern = re.compile(r"\[(\d{2}:\d{2}\.\d{2})\]\s*(.*)")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = time_pattern.match(line)
        if match:
            timestamp = match.group(1)
            lyric = match.group(2)
            subtitles.append((timestamp, lyric))
    
    srt_entries = []
    for i, (timestamp, lyric) in enumerate(subtitles):
        start_time = convert_timestamp(f"[{timestamp}]")
        # 종료시간 계산
        if i < len(subtitles) - 1:
            next_timestamp = subtitles[i+1][0]
            end_time = convert_timestamp(f"[{next_timestamp}]")
        else:
            if total_duration is not None:
                end_time = seconds_to_srt_timestamp(total_duration)
            else:
                parts = start_time.split(":")
                sec_parts = parts[2].split(",")
                total_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(sec_parts[0]) + int(sec_parts[1]) / 1000.0
                end_seconds = total_sec + default_duration
                end_time = seconds_to_srt_timestamp(end_seconds)
        
        # 영어 번역 수행 (비동기)
        translation = await translate_lyrics([lyric])
        translated_text = translation[0] if translation else "Translation failed"
        
        srt_entries.append({
            "index": i + 1,
            "start": start_time,
            "end": end_time,
            "original": lyric,
            "translated": translated_text
        })
    
    # SRT 파일 작성
    with open(srt_filepath, "w", encoding="utf-8") as f:
        for entry in srt_entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['original']}\n")
            f.write(f"{entry['translated']}\n\n")
    
    print(f"SRT 파일 생성 완료: {srt_filepath}")
    return srt_filepath
