# 🎬 Lyric Video Maker

**노래 검색 → 가사 번역 → 앨범 아트 다운로드 → 리릭 비디오 생성까지 한 번에!**
PyQt6 기반의 GUI로 누구나 빠르게 고퀄리티 리릭 비디오를 제작할 수 있는 파이썬 애플리케이션입니다.

---

# ✨ 주요 기능

### 🔍 1. 노래 검색

* **Genie API**로 노래 정보(제목/아티스트/앨범/가사)를 자동 수집
* **YouTube 검색**을 통한 오디오 소스 선택
* 선택 즉시 메타데이터 입력란 자동 채움

### 🖼️ 2. 앨범 아트 자동 수집

* MusicBrainz + Bugs 음악 페이지 스크래핑
* URL 수동 입력도 가능하며 미리보기 즉시 표시

### 🌍 3. 자연스러운 가사 번역(LRC 기반)

* LRC 파일 파싱
* 문맥 보정 후 OpenAI API로 영어 번역 생성
* 캐시를 활용하여 반복 번역 최소화

### 🎞️ 4. 리릭 비디오 생성 / 편집용 XML 출력

* FFmpeg + PIL로 **앨범 아트 + 타임라인 + 번역 가사** 합성
* **MP4 비디오** 또는 **Final Cut Pro XML(Premiere 호환)** 출력
* YouTube 자동 업로드 옵션 지원(OAuth)

### 🖥️ 5. 직관적인 PyQt6 GUI

* 실시간 진행률 표시
* 검색 결과 미리보기
* 출력 옵션 및 설정 메뉴 제공

---

# 🚀 설치 및 초기 설정

## 1. 저장소 클론

```bash
git clone https://github.com/yourusername/LyricVideoMaker.git
cd LyricVideoMaker
```

## 2. 가상환경 생성(권장)

```bash
python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

## 3. 패키지 설치

```bash
pip install -r requirements.txt
```

## 4. 환경 변수 설정

프로젝트 루트에 `.env` 생성 후 아래 내용 입력:

```env
OPENAI_API_KEY=your_api_key_here
```

(YouTube 업로드 사용 시 OAuth 파일은 `client_secret.json`으로 루트에 배치)

---

# 🖱️ 사용 방법

## 1. 앱 실행

```bash
python main.py
```

PyQt6 GUI가 실행되며, 필요한 폴더(`data/…`)가 자동 생성됩니다.

---

## 2. 노래 검색 → 선택

1. 검색창에 `"아티스트 곡명"` 입력
2. **Genie 결과**에서 원하는 항목 선택

   * 제목 / 아티스트 / LRC 링크 / 앨범 아트 URL 자동 입력
3. **YouTube 검색 결과**에서 실제 음원 선택

   * 오디오 다운로드용 URL 자동 등록
4. 앨범 아트는 자동 미리보기 제공

---

## 3. 출력 옵션 설정

* 출력 형식 선택

  * **MP4 비디오**
  * **Premiere/FCP용 XML(xmeml)**
* 번역 모델 선택 (OpenAI)
* YouTube 자동 업로드 여부 설정

---

## 4. 리릭 비디오 생성

### 버튼: **Generate Video**

아래 작업이 순서대로 실행됩니다:

1. YouTube 오디오(MP3) 다운로드
2. 앨범 아트 이미지 다운로드
3. LRC 파일 파싱
4. OpenAI 기반 문맥 번역
5. FFmpeg/PIL로 영상 합성
6. 결과물 저장 (`data/output`)

모든 과정은 진행률 바 + 로그로 즉시 확인할 수 있습니다.

---

# 🔧 실사용 운영 가이드

## 💡 1. 최초 준비 체크

* `.env`에 API 키 등록
* `(선택)` YouTube 업로드용 OAuth 설정
* 실행 전 `pip install -r requirements.txt`
* 최초 `python main.py` 실행 시 데이터 폴더 자동 생성됨

---

## 📌 2. 한 세션 작업 흐름

1. 앱 실행
2. 노래 검색
3. Genie에서 메타데이터 자동 채우기
4. YouTube에서 음원 선택
5. 필요하면 앨범 아트 URL 교체
6. 번역/출력 옵션 조정
7. **Generate Video** 클릭
8. 결과물 확인(`data/output`)

---

## 🧹 3. 작업 후 정리

* 결과물은 **전부 `data/output`**에 모입니다
* `data/temp`는 자동 정리되며 문제 발생 시 삭제해도 안전
* 번역 캐시 초기화:

  * `data/cache/translation_cache.json` 삭제
* 오류 발생 시 GUI 로그 + `[DEBUG]`, `[ERROR]` 콘솔 메시지 참고

---

# 🧱 디렉토리 및 코드 구조

```
LyricVideoMaker/
│ main.py                 # GUI 실행 엔트리
│ .env
│ requirements.txt
│
├─ app/
│  ├─ pipeline/
│  │   └─ process_manager.py      # 전체 작업 파이프라인
│  ├─ lyrics/
│  │   └─ openai_handler.py       # 번역 + LRC 처리
│  ├─ media/
│  │   └─ video_maker.py          # FFmpeg 기반 비디오 생성
│  ├─ export/
│  │   └─ premiere_exporter.py    # XML(xmeml) 출력
│  ├─ sources/
│  │   ├─ genie_handler.py
│  │   ├─ youtube_handler.py
│  │   └─ album_art_finder.py
│  └─ ui/
│      ├─ main_window.py
│      └─ components.py
│
├─ data/
│  ├─ temp/       # 중간 파일
│  ├─ lyrics/     # LRC 파일
│  ├─ output/     # 최종 MP4, XML
│  ├─ cache/      # 번역 캐시
│  └─ config/     # 설정 파일
```

---

# 🛠️ 문제 해결

* 항상 콘솔 로그의 `[DEBUG]` / `[ERROR]` 확인
* API 키/환경 변수 확인
* YouTube 다운로드 오류 시 네트워크 또는 URL 재확인
* GUI가 멈출 경우 재시작 후 `data/temp` 비우고 다시 시도

---

# 📄 라이선스

본 프로젝트는 **MIT License**를 따릅니다.
자세한 내용은 [LICENSE](LICENSE) 파일을 확인하세요.