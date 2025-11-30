import os
import pickle
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# YouTube API 스코프
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    """YouTube API 인증 및 서비스 객체 반환"""
    creds = None
    token_path = 'token.pickle'
    credentials_path = os.getenv('YOUTUBE_CLIENT_SECRET_PATH', 'client_secret.json')
    
    # 저장된 토큰이 있으면 로드
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # 유효한 인증 정보가 없으면 로그인
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"YouTube API credentials 파일을 찾을 수 없습니다: {credentials_path}\n"
                    "Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 생성하고 다운로드하세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 토큰 저장
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: Optional[list] = None,
    category_id: str = "10",  # 10 = Music
    privacy_status: str = "private"  # "public", "private", "unlisted"
) -> str:
    """
    YouTube에 동영상 업로드
    
    Args:
        video_path: 업로드할 동영상 파일 경로
        title: 동영상 제목
        description: 동영상 설명
        tags: 태그 리스트
        category_id: 카테고리 ID (10 = Music)
        privacy_status: 공개 설정 ("public", "private", "unlisted")
    
    Returns:
        업로드된 동영상의 YouTube ID
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"동영상 파일을 찾을 수 없습니다: {video_path}")
    
    youtube = get_authenticated_service()
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags or [],
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }
    
    # 동영상 파일 업로드
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    print(f"[DEBUG] YouTube 업로드 시작: {title}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"[DEBUG] 업로드 진행률: {progress}%")
    
    video_id = response['id']
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"[DEBUG] YouTube 업로드 완료: {video_url}")
    
    return video_id
