# YouTube 자동 업로드 설정 가이드

## 1. Google Cloud Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. **API 및 서비스 > 라이브러리**로 이동
4. "YouTube Data API v3" 검색 후 **사용 설정**
5. **API 및 서비스 > 사용자 인증 정보**로 이동
6. **사용자 인증 정보 만들기 > OAuth 클라이언트 ID** 선택
7. 애플리케이션 유형: **데스크톱 앱** 선택
8. 생성 후 **JSON 다운로드** 클릭
9. 다운로드한 파일을 프로젝트 루트에 `client_secret.json`으로 저장

## 2. 필요한 패키지 설치

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## 3. 사용 예시

```python
from app.media.video_maker import make_lyric_video
from app.upload.youtube_uploader import upload_video

# 1. 동영상 생성
video_path = "data/output/output.mp4"
make_lyric_video(
    audio_path="path/to/audio.mp3",
    album_art_path="path/to/album_art.jpg",
    lyrics_json_path="data/temp/lyrics.json",
    output_path=video_path
)

# 2. YouTube 업로드
video_id = upload_video(
    video_path=video_path,
    title="아티스트 - 곡 제목 (Lyric Video)",
    description="Official Lyric Video",
    tags=["lyrics", "lyric video", "music"],
    privacy_status="public"  # "public", "private", "unlisted"
)

print(f"업로드 완료: https://www.youtube.com/watch?v={video_id}")
```

## 4. 환경 변수 설정 (선택사항)

`.env` 파일에 추가:
```
YOUTUBE_CLIENT_SECRET_PATH=client_secret.json
```

## 5. 첫 실행 시

- 첫 실행 시 브라우저가 열리며 Google 계정 로그인 요청
- 앱 권한 승인 후 `token.pickle` 파일이 자동 생성됨
- 이후 실행 시에는 자동으로 인증됨

## 6. 주의사항

- `client_secret.json`과 `token.pickle`은 절대 공개 저장소에 업로드하지 마세요
- `.gitignore`에 추가 권장:
  ```
  client_secret.json
  token.pickle
  ```
