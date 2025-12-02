# youtube_handler.py

from typing import Optional, List, Dict, Any

import os
import yt_dlp
from youtubesearchpython import VideosSearch

from app.config.paths import TEMP_DIR, ensure_data_dirs

def parse_duration(duration_str: str) -> Optional[int]:
    """YouTube 동영상 길이 문자열(HH:MM:SS)을 초 단위로 변환"""
    if not duration_str:
        return None
    parts = duration_str.split(':')
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
    except (ValueError, IndexError):
        return None
    return None

def _search_with_videos_search(query: str, target_duration: Optional[int]) -> List[Dict[str, Any]]:
    """youtubesearchpython 기반 검색"""
    videosSearch = VideosSearch(query + " audio", limit=5)
    results = videosSearch.result().get("result", [])

    formatted_results = []
    for result in results:
        duration_in_sec = parse_duration(result.get('duration'))
        formatted_results.append({
            'title': result.get('title', ''),
            'link': result.get('link', ''),
            'thumbnail': result.get('thumbnails', [{}])[0].get('url', ''),
            'duration': result.get('duration', 'N/A'),
            'duration_sec': duration_in_sec
        })

    return _pick_by_duration(formatted_results, target_duration)


def _search_with_yt_dlp(query: str, target_duration: Optional[int]) -> List[Dict[str, Any]]:
    """yt-dlp 검색을 이용한 백업 경로 (youtubesearchpython 실패 시 사용)"""
    opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        # ytsearch는 내부적으로 YouTube Data API 없이도 검색 가능
        info = ydl.extract_info(f"ytsearch5:{query} audio", download=False)
        entries = info.get('entries', [])

    formatted_results = []
    for entry in entries:
        duration = entry.get('duration')
        formatted_results.append({
            'title': entry.get('title', ''),
            'link': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
            'thumbnail': entry.get('thumbnails', [{}])[0].get('url', ''),
            'duration': entry.get('duration_string') or (str(duration) if duration else 'N/A'),
            'duration_sec': duration
        })

    return _pick_by_duration(formatted_results, target_duration)


def _pick_by_duration(results: List[Dict[str, Any]], target_duration: Optional[int]) -> List[Dict[str, Any]]:
    """타겟 길이 기준으로 최적 결과 선택"""
    if not results:
        return []

    if target_duration is None:
        return results[:3]

    best_match = None
    min_diff = float('inf')

    for result in results:
        if result['duration_sec'] is not None:
            diff = abs(result['duration_sec'] - target_duration)
            if diff < min_diff:
                min_diff = diff
                best_match = result

    if best_match and min_diff <= 10:
        print(f"[DEBUG] 자동 선택된 YouTube 영상: {best_match['title']} (길이 차이: {min_diff}초)")
        return [best_match]

    print(f"[DEBUG] 자동 선택 실패. 가장 근접한 영상과의 길이 차이가 큼: {min_diff}초")
    return results[:3]


def youtube_search(query: str, target_duration: Optional[int] = None) -> List[Dict[str, Any]]:
    """YouTube 검색. 기본 라이브러리가 실패하면 yt-dlp로 재시도"""
    try:
        return _search_with_videos_search(query, target_duration)
    except TypeError as e:
        # youtubesearchpython이 proxies 키워드 문제로 실패하는 경우를 대비한 처리
        if "proxies" in str(e):
            print("[WARN] youtubesearchpython proxies 오류 발생, yt-dlp로 대체 검색 수행")
        else:
            print(f"[WARN] youtubesearchpython 검색 실패: {e}")
    except Exception as e:
        print(f"[WARN] youtubesearchpython 검색 실패: {e}")

    try:
        return _search_with_yt_dlp(query, target_duration)
    except Exception as e:
        print(f"YouTube 검색 실패: {e}")
        return []

def download_youtube_audio(url: str, output_filename: str) -> bool:
    """YouTube 동영상의 오디오를 MP3로 바로 다운로드"""
    try:
        # output_filename = os.path.splitext(output_filename)[0]  # 파일명에 점(.)이 포함된 경우 확장자로 오인하여 잘리는 문제 수정
        ensure_data_dirs()
        os.makedirs(TEMP_DIR, exist_ok=True)
        base_path = os.path.join(TEMP_DIR, output_filename)

        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '192K',
            'outtmpl': base_path + '.%(ext)s',  # 확장자 명시적 처리
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'noplaylist': True,
            'overwrites': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"[DEBUG] MP3 다운로드 시작: {output_filename}")
            ydl.download([url])
            
            output_path = base_path + '.mp3'
            if os.path.exists(output_path):
                print(f"[DEBUG] MP3 다운로드 완료: {output_path}")
                return True
                
        return False

    except Exception as e:
        print(f"[ERROR] MP3 다운로드 실패: {str(e)}")
        return False
