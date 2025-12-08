"""Premiere Pro용 XML 내보내기 유틸리티."""

from __future__ import annotations

import json
import os
import subprocess
from typing import List
from xml.etree.ElementTree import Element, ElementTree, SubElement

from app.config.paths import FFPROBE_PATH


def _get_audio_duration(audio_path: str) -> float:
    """FFprobe를 사용하여 오디오 파일의 길이를 초 단위로 반환합니다."""
    try:
        cmd = [
            FFPROBE_PATH,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"[ERROR] 오디오 길이 확인 실패: {e}")
        return 0.0


def _pathurl(path: str) -> str:
    """파일 경로를 Premiere가 이해할 수 있는 file:// URL로 변환."""
    abs_path = os.path.abspath(path)
    # Windows 경로에서도 동작하도록 슬래시 표준화
    return "file://" + abs_path.replace("\\", "/")


def _append_markers(
    clipitem: Element, lyrics: List[dict], fps: int, total_duration: float
) -> None:
    """가사 데이터를 Premiere 마커로 변환하여 clipitem에 추가."""

    if not lyrics:
        return

    # 종료 시간을 계산하기 위해 다음 시작 시간을 미리 확인
    for idx, lyric in enumerate(lyrics):
        start = float(lyric.get("start_time", 0.0))
        end = (
            float(lyrics[idx + 1].get("start_time", total_duration))
            if idx < len(lyrics) - 1
            else total_duration
        )

        start_frames = int(round(start * fps))
        end_frames = max(start_frames + 1, int(round(end * fps)))

        marker = SubElement(clipitem, "marker")
        SubElement(marker, "name").text = (lyric.get("original") or "").strip()
        combined_comment = "\n".join(
            filter(None, [lyric.get("original", ""), lyric.get("english", "")])
        )
        SubElement(marker, "comment").text = combined_comment.strip()
        SubElement(marker, "in").text = str(start_frames)
        SubElement(marker, "out").text = str(end_frames)


def _add_rate(parent: Element, fps: int) -> None:
    rate = SubElement(parent, "rate")
    SubElement(rate, "timebase").text = str(fps)
    SubElement(rate, "ntsc").text = "FALSE"


def export_premiere_xml(
    audio_path: str,
    album_art_path: str,
    lyrics_json_path: str,
    output_xml_path: str,
    fps: int = 30,
) -> str:
    """
    가사 JSON을 이용해 Premiere Pro에서 바로 불러올 수 있는 Final Cut Pro XML(xmeml)을 생성한다.

    Args:
        audio_path: 오디오 파일 경로.
        album_art_path: 앨범 아트 이미지 경로(참조용).
        lyrics_json_path: 번역된 가사 JSON 파일 경로.
        output_xml_path: 생성할 XML 파일 경로.
        fps: 시퀀스 프레임 레이트.

    Returns:
        생성된 XML 파일 경로.
    """

    if not os.path.exists(lyrics_json_path):
        raise FileNotFoundError(f"가사 JSON을 찾을 수 없습니다: {lyrics_json_path}")

    with open(lyrics_json_path, "r", encoding="utf-8") as f:
        lyrics: List[dict] = json.load(f)

    lyrics.sort(key=lambda item: float(item.get("start_time", 0.0)))

    total_duration = _get_audio_duration(audio_path)

    total_frames = int(round(total_duration * fps))
    sequence_name = os.path.splitext(os.path.basename(audio_path))[0]

    root = Element("xmeml", version="5")
    sequence = SubElement(root, "sequence", id="sequence-1")
    SubElement(sequence, "name").text = sequence_name
    _add_rate(sequence, fps)
    SubElement(sequence, "duration").text = str(total_frames)

    media = SubElement(sequence, "media")
    video = SubElement(media, "video")
    track = SubElement(video, "track")

    clipitem = SubElement(track, "clipitem", id="clipitem-1")
    SubElement(clipitem, "name").text = sequence_name
    _add_rate(clipitem, fps)
    SubElement(clipitem, "start").text = "0"
    SubElement(clipitem, "end").text = str(total_frames)
    SubElement(clipitem, "in").text = "0"
    SubElement(clipitem, "out").text = str(total_frames)

    file_el = SubElement(clipitem, "file", id="file-1")
    SubElement(file_el, "name").text = os.path.basename(audio_path)
    SubElement(file_el, "pathurl").text = _pathurl(audio_path)
    _add_rate(file_el, fps)
    SubElement(file_el, "duration").text = str(total_frames)

    # 부가 정보로 앨범 아트 위치를 logginginfo에 기록
    logginginfo = SubElement(file_el, "logginginfo")
    SubElement(logginginfo, "description").text = f"Album art: {_pathurl(album_art_path)}"

    _append_markers(clipitem, lyrics, fps, total_duration)

    os.makedirs(os.path.dirname(output_xml_path) or ".", exist_ok=True)
    ElementTree(root).write(output_xml_path, encoding="utf-8", xml_declaration=True)
    return output_xml_path

