from genieapi import GenieAPI
from typing import List, Tuple, Optional
import requests
import traceback
import os
from bs4 import BeautifulSoup

def search_genie_songs(query: str, limit: int = 4) -> List[Tuple[str, str, str, str, int]]:
    """지니뮤직에서 노래 검색"""
    try:
        print(f"[DEBUG] 지니뮤직 검색 시작: 검색어 '{query}'")
        genie = GenieAPI()
        songs = genie.search_song(query, limit=limit)
        print(f"[DEBUG] GenieAPI 검색 결과: {len(songs)}개")
        
        results = []
        for idx, song in enumerate(songs):
            try:
                if isinstance(song, dict):
                    title = song.get('title', '').strip()
                    song_id = (song.get('id') or song.get('song_id') or '').strip()
                    artist = song.get('artist', '').strip()
                    album = song.get('album') or song.get('album_name') or ''
                    album = album.strip()
                    extra_info = f"{artist} - {album}" if album else artist
                else:
                    unpacked = list(song)
                    title, song_id = unpacked[0], unpacked[1]
                    extra_info = unpacked[2] if len(unpacked) > 2 else ''

                print(f"\n[DEBUG] {idx+1}번째 곡 처리 중:")
                print(f"  - 제목: {title}")
                print(f"  - ID: {song_id}")
                print(f"  - 추가정보: {extra_info}")
                
                album_art_url, duration = get_song_details(song_id)
                if not album_art_url and isinstance(song, dict):
                    album_art_url = song.get('thumbnail')
                album_art_url = album_art_url or ""
                print(f"  - 앨범아트 URL: {album_art_url}")
                
                results.append((title.strip(), str(song_id), extra_info.strip(), album_art_url, duration))
                print(f"[DEBUG] {idx+1}번째 곡 처리 완료")
                
            except Exception as e:
                print(f"[DEBUG] 곡 정보 처리 실패: {e}")
                traceback.print_exc()
                continue
        
        return results

    except Exception as e:
        print(f"[DEBUG] 지니뮤직 검색 실패: {e}")
        traceback.print_exc()
        return []

def get_genie_lyrics(song_id: str) -> Optional[str]:
    """지니뮤직에서 가사 가져오기"""
    try:
        genie = GenieAPI()
        lyrics = genie.get_lyrics(song_id)
        
        # GenieAPI가 파일 경로를 반환하는 경우 파일 내용을 읽어서 반환
        if lyrics and isinstance(lyrics, str) and (os.path.exists(lyrics) or os.path.exists(os.path.join(os.getcwd(), lyrics))):
            file_path = lyrics if os.path.exists(lyrics) else os.path.join(os.getcwd(), lyrics)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"[DEBUG] 가사 파일 읽기 성공: {file_path}")
                    return content
                except Exception as read_err:
                    print(f"[WARN] 가사 파일 읽기 실패: {read_err}")
                    # 읽기 실패 시 경로 반환 (기존 동작 유지) 또는 None
        
        print(f"[DEBUG] 가사 가져오기 성공: {song_id}")
        return lyrics
    except Exception as e:
        print(f"[DEBUG] 가사 가져오기 실패: {e}")
        return None

def parse_genie_extra_info(extra_info: str) -> Tuple[str, str]:
    """추가 정보에서 아티스트와 앨범 분리"""
    if not extra_info:
        return "", ""
    parts = extra_info.split(' - ', 1)
    artist = parts[0].strip()
    album = parts[1].strip() if len(parts) > 1 else ""
    return artist, album

def get_song_details(song_id: str) -> Tuple[Optional[str], Optional[int]]:
    """지니뮤직에서 앨범 아트 URL과 재생 시간 가져오기"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        song_url = f"https://www.genie.co.kr/detail/songInfo?xgnm={song_id}"
        print(f"[DEBUG] 곡 정보 URL: {song_url}")
        response = requests.get(song_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 앨범 아트
        album_art_url = None
        album_img = soup.select_one('div.photo-zone span.cover > img')
        if album_img and 'src' in album_img.attrs:
            img_url = album_img['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            album_art_url = img_url.replace('/dims/resize/Q_80,0', '')
            print(f"[DEBUG] 앨범 아트 URL 찾음: {album_art_url}")
        else:
            print("[DEBUG] 앨범 아트를 찾을 수 없습니다.")

        # 재생 시간
        duration = None
        info_elements = soup.select('ul.info-data li')
        for item in info_elements:
            title_span = item.select_one('span.title')
            if title_span and '재생시간' in title_span.text:
                value_span = item.select_one('span.value')
                if value_span:
                    time_str = value_span.text.strip()
                    try:
                        minutes, seconds = map(int, time_str.split(':'))
                        duration = minutes * 60 + seconds
                        print(f"[DEBUG] 재생 시간 찾음: {time_str} ({duration}초)")
                    except ValueError:
                        print(f"[DEBUG] 재생 시간 형식 오류: {time_str}")
                break
        else:
            print("[DEBUG] 재생 시간을 찾을 수 없습니다.")
            
        return album_art_url, duration
            
    except Exception as e:
        print(f"[DEBUG] 앨범 아트 및 재생 시간 가져오기 실패: {e}")
        traceback.print_exc()
        
    return None, None

def get_album_arts_url(song_id: str) -> List[str]:
    """지니뮤직에서 여러 앨범 아트 URL 가져오기"""
    urls = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # 곡 정보 페이지
        url = f"https://www.genie.co.kr/detail/songInfo?xgnm={song_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        album_img = soup.select_one('a.cover > img')
        if album_img and 'src' in album_img.attrs:
            img_url = album_img['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            urls.append(img_url.replace('/cover/size80/', '/cover/ori/'))
            
        # 아티스트 페이지에서 추가 앨범 아트 검색
        artist_link = soup.select_one('a.artist-info')
        if artist_link and 'href' in artist_link.attrs:
            artist_url = f"https://www.genie.co.kr{artist_link['href']}"
            artist_response = requests.get(artist_url, headers=headers)
            artist_soup = BeautifulSoup(artist_response.text, 'html.parser')
            album_imgs = artist_soup.select('div.album-list img')[:2]  # 추가로 2개만
            
            for img in album_imgs:
                if 'src' in img.attrs:
                    img_url = img['src']
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    urls.append(img_url.replace('/cover/size80/', '/cover/ori/'))
            
    except Exception as e:
        print(f"앨범 아트 URL 가져오기 실패: {e}")
        
    return urls

def get_song_album_id_and_art_url(song_id: str) -> Optional[Tuple[str, str]]:
    """지니뮤직에서 앨범 아트 URL과 앨범 ID 가져오기"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = f"https://www.genie.co.kr/detail/songInfo?xgnm={song_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        album_img = soup.select_one('a.cover > img')
        
        if album_img and 'src' in album_img.attrs:
            img_url = album_img['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            album_id = img_url.split('/')[-1].split('.')[0]
            return img_url.replace('/cover/size140/', '/cover/ori/'), album_id
            
    except Exception as e:
        print(f"앨범 정보 가져오기 실패: {e}")
        traceback.print_exc()
        
    return None
