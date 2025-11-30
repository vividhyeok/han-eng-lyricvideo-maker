"""
spotDL handler for high-quality audio downloads
Uses Spotify metadata to find the best matching audio from YouTube
"""

import os
from typing import Optional
from spotdl import Spotdl
from spotdl.types.song import Song

def download_audio_with_spotdl(artist: str, title: str, output_dir: str = "temp") -> Optional[str]:
    """
    spotDL을 사용하여 고품질 오디오 다운로드
    
    Args:
        artist: 아티스트 이름
        title: 곡 제목
        output_dir: 출력 디렉토리
    
    Returns:
        다운로드된 파일 경로 또는 None
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # spotDL 초기화
        spotdl = Spotdl(
            client_id="your_client_id",  # Spotify API credentials (optional for search)
            client_secret="your_client_secret",
            output_format="mp3",
            bitrate="320k",  # 최고 품질
            threads=4
        )
        
        # 검색 쿼리 생성
        query = f"{artist} - {title}"
        print(f"[DEBUG] spotDL 검색: {query}")
        
        # Spotify에서 곡 검색
        songs = spotdl.search([query])
        
        if not songs:
            print(f"[DEBUG] spotDL 검색 결과 없음: {query}")
            return None
        
        song = songs[0]
        print(f"[DEBUG] 찾은 곡: {song.name} by {song.artist}")
        
        # 다운로드
        output_file = os.path.join(output_dir, f"{artist} - {title}.mp3")
        spotdl.download(song, output_file=output_file)
        
        if os.path.exists(output_file):
            print(f"[DEBUG] spotDL 다운로드 완료: {output_file}")
            return output_file
        
        return None
        
    except Exception as e:
        print(f"[ERROR] spotDL 다운로드 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def download_audio_simple(artist: str, title: str, output_dir: str = "temp") -> Optional[str]:
    """
    간단한 spotDL 다운로드 (Spotify API credentials 불필요)
    
    Args:
        artist: 아티스트 이름
        title: 곡 제목
        output_dir: 출력 디렉토리
    
    Returns:
        다운로드된 파일 경로 또는 None
    """
    try:
        import subprocess
        os.makedirs(output_dir, exist_ok=True)
        
        query = f"{artist} - {title}"
        output_template = os.path.join(output_dir, "{artist} - {title}.{output-ext}")
        
        print(f"[DEBUG] spotDL CLI 다운로드: {query}")
        
        # spotDL CLI 사용
        cmd = [
            "spotdl",
            "download",
            query,
            "--output", output_template,
            "--format", "mp3",
            "--bitrate", "320k"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            expected_file = os.path.join(output_dir, f"{artist} - {title}.mp3")
            if os.path.exists(expected_file):
                print(f"[DEBUG] spotDL 다운로드 완료: {expected_file}")
                return expected_file
        else:
            print(f"[ERROR] spotDL CLI 오류: {result.stderr}")
        
        return None
        
    except Exception as e:
        print(f"[ERROR] spotDL 다운로드 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
