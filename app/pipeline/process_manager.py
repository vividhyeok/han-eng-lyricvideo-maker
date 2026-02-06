import os
import traceback
import asyncio
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from app.config.paths import (
    LYRICS_DIR,
    OUTPUT_DIR,
    TEMP_DIR,
    ensure_data_dirs,
    LEGACY_LYRICS_DIR,
)
from app.export.premiere_exporter import export_premiere_xml
from app.lyrics.openai_handler import parse_lrc_and_translate
from app.media.video_maker import make_lyric_video, get_audio_duration
from app.sources.album_art_finder import download_album_art
from app.sources.youtube_handler import download_youtube_audio

OutputMode = Literal["video", "premiere_xml"]


@dataclass
class ProcessConfig:
    title: str
    artist: str
    album_art_url: str
    youtube_url: str
    output_mode: OutputMode = "video"
    target_dir: str = TEMP_DIR
    output_dir: str = OUTPUT_DIR
    lrc_path: Optional[str] = None
    prefer_youtube: bool = False
    track_no: Optional[int] = None
    sub_folder: Optional[str] = None

class ProcessManager:
    def __init__(self, update_progress: Callable[[str, int], None]):
        self.update_progress = update_progress

    async def process_async(self, config: ProcessConfig):
        temp_files_to_cleanup = []

        try:
            print("[DEBUG] 작업 프로세스 시작")
            
            ensure_data_dirs()
            os.makedirs(LYRICS_DIR, exist_ok=True)
            print(f"[DEBUG] 디렉토리 확인: {TEMP_DIR}")
            print(f"[DEBUG] 디렉토리 확인: {OUTPUT_DIR}")
            print(f"[DEBUG] 디렉토리 확인: {LYRICS_DIR}")
                
            # 파일명 생성
            base_filename = f"{config.artist} - {config.title}"
            if config.track_no is not None:
                base_filename = f"{config.track_no:02d} {base_filename}"
            
            filename = self._sanitize_filename(base_filename)
            
            # 출력 디렉토리 설정 (서브 폴더 지원)
            current_output_dir = config.output_dir
            if config.sub_folder:
                current_output_dir = os.path.join(config.output_dir, self._sanitize_filename(config.sub_folder))
                os.makedirs(current_output_dir, exist_ok=True)

            audio_path = os.path.join(TEMP_DIR, f"{filename}.mp3")
            image_path = os.path.join(TEMP_DIR, f"{filename}.jpg")
            json_path = os.path.join(TEMP_DIR, f"{filename}_lyrics.json")
            output_path = os.path.join(current_output_dir, f"{filename}.mp4")
            premiere_xml_path = os.path.join(current_output_dir, f"{filename}.xml")
            
            print("[DEBUG] 파일 경로 설정 완료:")
            print(f"- 오디오: {audio_path}")
            print(f"- 이미지: {image_path}")
            print(f"- 가사: {json_path}")
            print(f"- 출력: {output_path}")
            
            # 오디오 다운로드 (spotDL 우선, 실패 시 YouTube 폴백)
            self.update_progress("고품질 오디오 다운로드 중...", 20)
            
            audio_downloaded = False
            
            # Check if audio already exists (e.g. from manual sync)
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                print(f"[DEBUG] 기존 오디오 파일 사용: {audio_path}")
                audio_downloaded = True
            else:
                # Try spotDL unless prefer_youtube is True
                spotdl_success = False
                if not config.prefer_youtube:
                    print(f"[DEBUG] spotDL 다운로드 시도: {config.artist} - {config.title}")
                    from app.sources.spotdl_handler import download_audio_simple
                    spotdl_result = download_audio_simple(config.artist, config.title, TEMP_DIR)
                    
                    if spotdl_result and os.path.exists(spotdl_result):
                        print(f"[DEBUG] spotDL 다운로드 성공: {spotdl_result}")
                        # spotDL이 생성한 파일을 원하는 경로로 이동/복사
                        if spotdl_result != audio_path:
                            import shutil
                            shutil.move(spotdl_result, audio_path)
                        spotdl_success = True
                        audio_downloaded = True
                
                if not spotdl_success:
                    print("[WARN] spotDL 다운로드 건너뜀/실패, YouTube 다운로드로 폴백")
                    self.update_progress("YouTube 오디오 다운로드 중...", 25)
                    print(f"[DEBUG] YouTube 다운로드 시작: {config.youtube_url}")
                    if download_youtube_audio(config.youtube_url, filename):
                        audio_downloaded = True
                        print(f"[DEBUG] YouTube 다운로드 완료")
            
            if audio_downloaded:
                temp_files_to_cleanup.append(audio_path)
            else:
                raise Exception("오디오 다운로드 실패 (spotDL 및 YouTube 모두 실패)")
            print(f"[DEBUG] 오디오 다운로드 완료: {audio_path}")
            
            # 앨범 아트 다운로드
            self.update_progress("앨범 아트 다운로드 중...", 40)
            print(f"[DEBUG] 앨범 아트 다운로드 시작: {config.album_art_url}")
            if not download_album_art(config.album_art_url, image_path):
                raise Exception("앨범 아트 다운로드 실패")
            print("[DEBUG] 앨범 아트 다운로드 완료")
            temp_files_to_cleanup.append(image_path)
            
            # LRC 파일 찾기
            self.update_progress("가사 파일 처리 중...", 60)
            lrc_path = None
            if config.lrc_path:
                if os.path.exists(config.lrc_path):
                    lrc_path = config.lrc_path
                    print(f"[DEBUG] 지정된 LRC 파일 사용: {lrc_path}")
                else:
                    print(f"[WARN] 지정된 LRC 파일을 찾을 수 없습니다: {config.lrc_path}")

            if lrc_path is None:
                search_dirs = [LYRICS_DIR]
                if os.path.isdir(LEGACY_LYRICS_DIR) and LEGACY_LYRICS_DIR not in search_dirs:
                    search_dirs.append(LEGACY_LYRICS_DIR)

                lrc_files = []
                for lyrics_dir in search_dirs:
                    try:
                        lrc_files.extend(
                            [
                                os.path.join(lyrics_dir, f)
                                for f in os.listdir(lyrics_dir)
                                if f.endswith(".lrc")
                            ]
                        )
                    except FileNotFoundError:
                        continue
                if not lrc_files:
                    raise Exception("가사 파일을 찾을 수 없습니다")
                lrc_files.sort(key=lambda path: os.path.getmtime(path), reverse=True)
                lrc_path = lrc_files[0]
                print(f"[DEBUG] 최신 LRC 파일 사용: {lrc_path}")
            
            # 가사 번역
            try:
                self.update_progress("가사 번역 중...", 80)
                print("[DEBUG] 가사 번역 시작")
                os.environ['CURRENT_ARTIST'] = config.artist
                os.environ['CURRENT_TITLE'] = config.title
                
                # 오디오 길이 확인 (가사 배분을 위해)
                duration = get_audio_duration(audio_path)
                
                lyrics_json_path = await parse_lrc_and_translate(lrc_path, json_path, duration=duration)
                temp_files_to_cleanup.append(lyrics_json_path)
                print(f"[DEBUG] 가사 번역 완료: {lyrics_json_path}")
            finally:
                os.environ.pop('CURRENT_ARTIST', None)
                os.environ.pop('CURRENT_TITLE', None)
            
            try:
                for file_path in [audio_path, image_path, lyrics_json_path]:
                    if not os.path.exists(file_path):
                        raise Exception(f"필요한 파일이 없습니다: {file_path}")

                if config.output_mode == "premiere_xml":
                    self.update_progress("Premiere XML 내보내는 중...", 90)
                    print("[DEBUG] Premiere XML 전용 모드 시작")
                    xml_result = export_premiere_xml(
                        audio_path=audio_path,
                        album_art_path=image_path,
                        lyrics_json_path=lyrics_json_path,
                        output_xml_path=premiere_xml_path,
                    )
                    print(f"[DEBUG] Premiere XML 생성 완료: {xml_result}")
                    self._cleanup_temp_files(temp_files_to_cleanup)
                    return xml_result

                self.update_progress("리릭 비디오 생성 중...", 90)
                print("[DEBUG] 비디오 생성 시작")

                make_lyric_video(
                    audio_path=audio_path,
                    album_art_path=image_path,
                    lyrics_json_path=lyrics_json_path,
                    output_path=output_path
                )
                print(f"[DEBUG] 비디오 생성 완료: {output_path}")

                try:
                    self.update_progress("Premiere XML 내보내는 중...", 95)
                    xml_result = export_premiere_xml(
                        audio_path=audio_path,
                        album_art_path=image_path,
                        lyrics_json_path=lyrics_json_path,
                        output_xml_path=premiere_xml_path,
                    )
                    print(f"[DEBUG] Premiere XML 생성 완료: {xml_result}")
                except Exception as xml_error:
                    print(f"[WARN] Premiere XML 생성 실패: {xml_error}")

                self._cleanup_temp_files(temp_files_to_cleanup)
                return output_path

            except Exception as e:
                print(f"[ERROR] 비디오/XML 생성 중 오류 발생: {str(e)}")
                traceback.print_exc()
                raise
                
        except Exception as e:
            print(f"[ERROR] 처리 중 오류 발생: {str(e)}")
            traceback.print_exc()
            raise

    def process(self, config: ProcessConfig):
        """동기 래퍼 메서드"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.process_async(config))

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        import re
        return re.sub(r'[\\/*?:"<>|]', "_", filename)

    @staticmethod
    def _cleanup_temp_files(paths):
        for path in paths:
            if not path:
                continue
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"[DEBUG] 임시 파일 삭제: {path}")
                except OSError as cleanup_error:
                    print(f"[WARN] 임시 파일 삭제 실패 ({path}): {cleanup_error}")

    def validate_config(self, config: ProcessConfig) -> Optional[str]:
        if not all([config.title, config.artist, config.album_art_url, config.youtube_url]):
            return "제목, 아티스트, 앨범 아트 URL, YouTube URL을 모두 입력해주세요."
        if config.output_mode not in ("video", "premiere_xml"):
            return "출력 형식이 올바르지 않습니다."
        return None
