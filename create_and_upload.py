"""
YouTube 자동 업로드 테스트 스크립트

사용 전 준비사항:
1. Google Cloud Console에서 OAuth 2.0 클라이언트 ID 생성
2. client_secret.json 파일을 프로젝트 루트에 저장
3. .env 파일에 CURRENT_ARTIST, CURRENT_TITLE 설정
"""

import os
import asyncio
from dotenv import load_dotenv

from app.config.paths import OUTPUT_DIR, TEMP_DIR, ensure_data_dirs
from app.lyrics.openai_handler import parse_lrc_and_translate
from app.media.video_maker import make_lyric_video
from app.upload.youtube_uploader import upload_video

# 환경 변수 로드
load_dotenv()

async def main():
    ensure_data_dirs()

    # 파일 경로 설정
    lrc_file = input("LRC 파일 경로를 입력하세요: ").strip()
    audio_file = input("오디오 파일 경로를 입력하세요: ").strip()
    album_art_file = input("앨범 아트 이미지 경로를 입력하세요: ").strip()
    
    # 파일 존재 확인
    if not os.path.exists(lrc_file):
        print(f"❌ LRC 파일을 찾을 수 없습니다: {lrc_file}")
        return
    if not os.path.exists(audio_file):
        print(f"❌ 오디오 파일을 찾을 수 없습니다: {audio_file}")
        return
    if not os.path.exists(album_art_file):
        print(f"❌ 앨범 아트 파일을 찾을 수 없습니다: {album_art_file}")
        return
    
    # 아티스트와 제목 가져오기
    artist = os.getenv('CURRENT_ARTIST', input("아티스트 이름: ").strip())
    title = os.getenv('CURRENT_TITLE', input("곡 제목: ").strip())
    
    print(f"\n🎵 처리 중: {artist} - {title}")
    
    # 1. LRC 파싱 및 번역
    print("\n📝 1단계: 가사 번역 중...")
    lyrics_json_path = os.path.join(TEMP_DIR, "lyrics.json")
    await parse_lrc_and_translate(lrc_file, lyrics_json_path)
    print("✅ 가사 번역 완료")
    
    # 2. 동영상 생성
    print("\n🎬 2단계: 리릭 비디오 생성 중...")
    output_video_path = os.path.join(OUTPUT_DIR, f"{artist} - {title} (Lyric Video).mp4")
    make_lyric_video(
        audio_path=audio_file,
        album_art_path=album_art_file,
        lyrics_json_path=lyrics_json_path,
        output_path=output_video_path
    )
    print(f"✅ 동영상 생성 완료: {output_video_path}")
    
    # 3. YouTube 업로드 여부 확인
    upload_choice = input("\n📤 YouTube에 업로드하시겠습니까? (y/n): ").strip().lower()
    
    if upload_choice == 'y':
        # client_secret.json 확인
        if not os.path.exists('client_secret.json'):
            print("\n❌ client_secret.json 파일이 없습니다.")
            print("Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 생성하고")
            print("다운로드한 JSON 파일을 'client_secret.json'으로 저장하세요.")
            print("\n자세한 내용은 YOUTUBE_UPLOAD_GUIDE.md를 참고하세요.")
            return
        
        # 업로드 설정
        video_title = f"{artist} - {title} (Lyric Video)"
        video_description = input(f"\n동영상 설명 (Enter로 기본값): ").strip() or f"{artist} - {title}\nOfficial Lyric Video"
        
        print("\n공개 설정을 선택하세요:")
        print("1. public (공개)")
        print("2. unlisted (링크가 있는 사람만)")
        print("3. private (비공개)")
        privacy_choice = input("선택 (1/2/3, 기본값=3): ").strip() or "3"
        
        privacy_map = {"1": "public", "2": "unlisted", "3": "private"}
        privacy_status = privacy_map.get(privacy_choice, "private")
        
        print(f"\n📤 YouTube 업로드 중...")
        print(f"   제목: {video_title}")
        print(f"   공개 설정: {privacy_status}")
        
        try:
            video_id = upload_video(
                video_path=output_video_path,
                title=video_title,
                description=video_description,
                tags=[artist, title, "lyrics", "lyric video", "music"],
                category_id="10",  # Music
                privacy_status=privacy_status
            )
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"\n✅ YouTube 업로드 완료!")
            print(f"🔗 URL: {video_url}")
            
        except FileNotFoundError as e:
            print(f"\n❌ 오류: {e}")
        except Exception as e:
            print(f"\n❌ 업로드 실패: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n✅ 완료! 동영상 파일: {output_video_path}")

if __name__ == "__main__":
    asyncio.run(main())
