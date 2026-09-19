```python
# -*- coding: utf-8 -*-
"""
VideoAnalysisService.py

動画解析の中核Service。

責務
----
VideoHandlerから渡された動画解析要求を受け取り、

    動画
      ↓
    メタデータ取得
      ↓
    音声抽出
      ↓
    フレーム抽出
      ↓
    字幕解析
      ↓
    OCR
      ↓
    音声文字起こし
      ↓
    タイムライン統合
      ↓
    AI Vision / Video Model
      ↓
    統合解析
      ↓
    Knowledge用データ生成

を行う。

設計思想
--------
VideoHandler:
    「動画解析という仕事を受け付ける」

VideoAnalysisService:
    「実際に動画を解析する」

Provider:
    「具体的なAI/音声認識/OCRを実行する」

この分離によって、

    Gemini
    OpenAI
    Claude
    Whisper
    Tesseract
    EasyOCR
    PaddleOCR
    Local Vision Model

などを後から交換できる。

重要
----
このServiceは特定AI SDKに直接依存しない。

AI APIの実装はProvider Adapter側に置く。
"""


from __future__ import annotations


# ============================================================
# Standard Library
# ============================================================

import asyncio
import base64
import hashlib
import json
import logging
import math
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import time

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
)


# ============================================================
# Logger
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
    )


# ============================================================
# Constants
# ============================================================

SERVICE_NAME = "video_analysis"

DEFAULT_WORK_DIR = ".ai_video"

DEFAULT_FRAME_INTERVAL = 5.0

DEFAULT_MAX_FRAMES = 120

DEFAULT_MAX_SUBTITLES = 1000

DEFAULT_MAX_TIMELINE_EVENTS = 1000

DEFAULT_AUDIO_SAMPLE_RATE = 16000

DEFAULT_AUDIO_CHANNELS = 1

DEFAULT_SCENE_INTERVAL = 30.0

SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    ".wmv",
    ".mpeg",
    ".mpg",
    ".3gp",
}


# ============================================================
# Exceptions
# ============================================================

class VideoAnalysisServiceError(Exception):
    """VideoAnalysisService共通例外。"""


class VideoInputError(VideoAnalysisServiceError):
    """動画入力エラー。"""


class VideoMetadataError(VideoAnalysisServiceError):
    """動画メタデータ取得エラー。"""


class VideoExtractionError(VideoAnalysisServiceError):
    """映像・音声抽出エラー。"""


class VideoProviderError(VideoAnalysisServiceError):
    """AI/OCR/音声認識Providerエラー。"""


class VideoTimelineError(VideoAnalysisServiceError):
    """タイムライン構築エラー。"""


# ============================================================
# Data Models
# ============================================================

@dataclass
class VideoInput:
    """
    VideoAnalysisServiceへの入力。

    video_path:
        動画ファイル

    subtitle_path:
        外部字幕ファイル。
        Noneなら動画と同名の字幕を自動探索する。

    start_time:
        解析開始秒

    end_time:
        解析終了秒
    """

    video_path: str

    subtitle_path: Optional[str] = None

    start_time: Optional[float] = None

    end_time: Optional[float] = None

    language: str = "ja"

    instruction: str = ""

    provider: Optional[str] = None

    extract_audio: bool = True

    extract_frames: bool = True

    use_ocr: bool = False

    use_transcription: bool = False

    use_ai: bool = True

    frame_interval: float = DEFAULT_FRAME_INTERVAL

    max_frames: int = DEFAULT_MAX_FRAMES

    max_subtitles: int = DEFAULT_MAX_SUBTITLES

    max_timeline_events: int = (
        DEFAULT_MAX_TIMELINE_EVENTS
    )

    save_intermediate: bool = False

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoMetadata:
    """
    動画の基本情報。
    """

    path: str

    filename: str

    extension: str

    size_bytes: int = 0

    duration: float = 0.0

    width: int = 0

    height: int = 0

    fps: float = 0.0

    video_codec: Optional[str] = None

    audio_codec: Optional[str] = None

    has_video: bool = False

    has_audio: bool = False

    mime_type: Optional[str] = None

    sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FrameInfo:
    """
    動画から抽出したフレーム。
    """

    index: int

    timestamp: float

    path: str

    width: int = 0

    height: int = 0

    image_base64: Optional[str] = None

    ocr_text: Optional[str] = None

    visual_description: Optional[str] = None

    confidence: Optional[float] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubtitleEntry:
    """
    字幕1件。
    """

    index: int

    start: float

    end: float

    text: str

    source: str = "external"

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptSegment:
    """
    音声文字起こし結果。
    """

    index: int

    start: float

    end: float

    text: str

    language: Optional[str] = None

    confidence: Optional[float] = None

    speaker: Optional[str] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OCRResult:
    """
    OCR結果。
    """

    timestamp: float

    text: str

    confidence: Optional[float] = None

    frame_path: Optional[str] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineEvent:
    """
    動画の時間軸上の統合イベント。

    ここがVideoAnalysisServiceの重要部分。

    例:

        00:01:20
        visual:
            Visual StudioでC++コードを編集

        subtitle:
            「ファイルを開きます」

        transcript:
            「ここではファイルを開きます」

        ocr:
            std::ifstream file(...)

    """

    timestamp: float

    end_timestamp: Optional[float] = None

    frame_indices: List[int] = field(
        default_factory=list
    )

    visual: List[str] = field(
        default_factory=list
    )

    subtitles: List[str] = field(
        default_factory=list
    )

    transcript: List[str] = field(
        default_factory=list
    )

    ocr: List[str] = field(
        default_factory=list
    )

    ai_summary: Optional[str] = None

    confidence: Optional[float] = None

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Scene:
    """
    動画のシーン。

    AIに動画全体を一度に渡すのではなく、
    シーン単位で解析するための構造。
    """

    index: int

    start: float

    end: float

    frame_indices: List[int] = field(
        default_factory=list
    )

    subtitle_text: str = ""

    transcript_text: str = ""

    ocr_text: str = ""

    visual_summary: str = ""

    ai_summary: str = ""

    keywords: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoAnalysisResult:
    """
    VideoAnalysisServiceの最終結果。
    """

    success: bool

    video: Dict[str, Any]

    input: Dict[str, Any]

    frames: List[Dict[str, Any]] = field(
        default_factory=list
    )

    subtitles: List[Dict[str, Any]] = field(
        default_factory=list
    )

    transcript: List[Dict[str, Any]] = field(
        default_factory=list
    )

    ocr: List[Dict[str, Any]] = field(
        default_factory=list
    )

    scenes: List[Dict[str, Any]] = field(
        default_factory=list
    )

    timeline: List[Dict[str, Any]] = field(
        default_factory=list
    )

    analysis: Dict[str, Any] = field(
        default_factory=dict
    )

    knowledge: Dict[str, Any] = field(
        default_factory=dict
    )

    statistics: Dict[str, Any] = field(
        default_factory=dict
    )

    warnings: List[str] = field(
        default_factory=list
    )

    errors: List[str] = field(
        default_factory=list
    )

    processing_time_seconds: float = 0.0

    generated_at: str = field(
        default_factory=lambda:
            datetime.now(
                timezone.utc
            ).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# Provider Protocols
# ============================================================

class VideoProvider(Protocol):
    """
    動画AI Provider。

    Gemini / OpenAI / Claude / Local Vision Model等を
    このインターフェースに合わせる。
    """

    async def analyze(
        self,
        *,
        video_path: str,
        prompt: str,
        metadata: Dict[str, Any],
        frames: Sequence[Dict[str, Any]],
        subtitles: Sequence[Dict[str, Any]],
        transcript: Sequence[Dict[str, Any]],
        timeline: Sequence[Dict[str, Any]],
        scenes: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        ...


class TranscriptionProvider(Protocol):
    """
    Whisper等の音声文字起こしProvider。
    """

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Sequence[Dict[str, Any]]:
        ...


class OCRProvider(Protocol):
    """
    OCR Provider。

    Tesseract / EasyOCR / PaddleOCR等。
    """

    async def recognize(
        self,
        image_path: str,
    ) -> Dict[str, Any]:
        ...


# ============================================================
# FFmpeg Utility
# ============================================================

class FFmpegService:
    """
    FFmpeg / ffprobeをServiceとしてまとめる。

    VideoAnalysisServiceから外部コマンドの詳細を隠す。
    """

    def __init__(
        self,
        ffmpeg_path: Optional[str] = None,
        ffprobe_path: Optional[str] = None,
    ):
        self.ffmpeg_path = (
            ffmpeg_path
            or os.getenv("FFMPEG_PATH")
            or shutil.which("ffmpeg")
        )

        self.ffprobe_path = (
            ffprobe_path
            or os.getenv("FFPROBE_PATH")
            or shutil.which("ffprobe")
        )

    @property
    def available(self) -> bool:
        return bool(
            self.ffmpeg_path
            and self.ffprobe_path
        )

    def require(self):
        if not self.available:
            raise VideoExtractionError(
                "FFmpeg / ffprobeが見つかりません。"
            )

    async def probe(
        self,
        path: str,
    ) -> Dict[str, Any]:

        self.require()

        command = [
            self.ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path,
        ]

        try:

            completed = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        except Exception as exc:

            raise VideoMetadataError(
                f"ffprobe実行失敗: {exc}"
            ) from exc

        if completed.returncode != 0:

            raise VideoMetadataError(
                completed.stderr[-3000:]
            )

        try:

            return json.loads(
                completed.stdout
            )

        except json.JSONDecodeError as exc:

            raise VideoMetadataError(
                "ffprobe結果のJSON解析に失敗しました。"
            ) from exc

    async def extract_frames(
        self,
        *,
        video_path: str,
        output_dir: str,
        start_time: float,
        end_time: Optional[float],
        interval: float,
        max_frames: int,
    ) -> List[str]:

        self.require()

        output = Path(output_dir)

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        duration = None

        if end_time is not None:
            duration = max(
                0.0,
                end_time - start_time,
            )

        command = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            str(start_time),
            "-i",
            video_path,
        ]

        if duration is not None:
            command.extend(
                [
                    "-t",
                    str(duration),
                ]
            )

        command.extend(
            [
                "-vf",
                f"fps=1/{max(interval, 0.1)}",
                "-frames:v",
                str(max_frames),
                "-q:v",
                "2",
                str(
                    output / "frame_%06d.jpg"
                ),
            ]
        )

        completed = await asyncio.to_thread(
            subprocess.run,
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if completed.returncode != 0:

            raise VideoExtractionError(
                "フレーム抽出失敗: "
                + completed.stderr[-3000:]
            )

        return [
            str(path)
            for path in sorted(
                output.glob("frame_*.jpg")
            )
        ]

    async def extract_audio(
        self,
        *,
        video_path: str,
        output_path: str,
        start_time: float,
        end_time: Optional[float],
    ) -> str:

        self.require()

        output = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            str(start_time),
            "-i",
            video_path,
        ]

        if end_time is not None:

            duration = max(
                0.0,
                end_time - start_time,
            )

            command.extend(
                [
                    "-t",
                    str(duration),
                ]
            )

        command.extend(
            [
                "-vn",
                "-ac",
                str(DEFAULT_AUDIO_CHANNELS),
                "-ar",
                str(DEFAULT_AUDIO_SAMPLE_RATE),
                "-c:a",
                "pcm_s16le",
                str(output),
            ]
        )

        completed = await asyncio.to_thread(
            subprocess.run,
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if completed.returncode != 0:

            raise VideoExtractionError(
                "音声抽出失敗: "
                + completed.stderr[-3000:]
            )

        return str(output)


# ============================================================
# Subtitle Service
# ============================================================

class SubtitleService:
    """
    外部字幕を解析する。

    対応:
        SRT
        VTT

    ASS/SSAは簡易対応。
    """

    TIME_PATTERN = re.compile(
        r"(?P<start>"
        r"\d{1,2}:"
        r"\d{2}:"
        r"\d{2}[,.]\d{3}"
        r"|"
        r"\d{1,2}:"
        r"\d{2}[,.]\d{3}"
        r")"
        r"\s*-->\s*"
        r"(?P<end>"
        r"\d{1,2}:"
        r"\d{2}:"
        r"\d{2}[,.]\d{3}"
        r"|"
        r"\d{1,2}:"
        r"\d{2}[,.]\d{3}"
        r")"
    )

    def discover(
        self,
        video_path: str,
    ) -> Optional[str]:

        path = Path(video_path)

        for extension in (
            ".srt",
            ".vtt",
            ".ass",
            ".ssa",
        ):

            candidate = path.with_suffix(
                extension
            )

            if candidate.exists():
                return str(candidate)

        return None

    def parse(
        self,
        subtitle_path: str,
        max_entries: int = DEFAULT_MAX_SUBTITLES,
    ) -> List[SubtitleEntry]:

        path = Path(subtitle_path)

        if not path.exists():
            raise VideoInputError(
                f"字幕ファイルがありません: {path}"
            )

        suffix = path.suffix.lower()

        text = path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

        if suffix == ".srt":
            entries = self._parse_srt(text)

        elif suffix == ".vtt":
            entries = self._parse_vtt(text)

        else:
            entries = self._parse_generic(text)

        return entries[:max_entries]

    def _parse_srt(
        self,
        text: str,
    ) -> List[SubtitleEntry]:

        blocks = re.split(
            r"\n\s*\n",
            text.strip(),
        )

        result = []

        for index, block in enumerate(
            blocks,
            start=1,
        ):

            lines = block.splitlines()

            match = None

            time_line_index = None

            for i, line in enumerate(lines):

                candidate = (
                    self.TIME_PATTERN.search(
                        line
                    )
                )

                if candidate:

                    match = candidate

                    time_line_index = i

                    break

            if not match:
                continue

            start = self._parse_time(
                match.group("start")
            )

            end = self._parse_time(
                match.group("end")
            )

            text_lines = lines[
                time_line_index + 1:
            ]

            subtitle = self._clean_text(
                "\n".join(text_lines)
            )

            if not subtitle:
                continue

            result.append(
                SubtitleEntry(
                    index=index,
                    start=start,
                    end=end,
                    text=subtitle,
                    source="srt",
                )
            )

        return result

    def _parse_vtt(
        self,
        text: str,
    ) -> List[SubtitleEntry]:

        text = re.sub(
            r"^WEBVTT.*?\n",
            "",
            text,
            flags=re.IGNORECASE,
        )

        blocks = re.split(
            r"\n\s*\n",
            text.strip(),
        )

        result = []

        for index, block in enumerate(
            blocks,
            start=1,
        ):

            lines = block.splitlines()

            match = None

            time_line_index = None

            for i, line in enumerate(lines):

                candidate = (
                    self.TIME_PATTERN.search(
                        line
                    )
                )

                if candidate:

                    match = candidate

                    time_line_index = i

                    break

            if not match:
                continue

            start = self._parse_time(
                match.group("start")
            )

            end = self._parse_time(
                match.group("end")
            )

            subtitle = self._clean_text(
                "\n".join(
                    lines[
                        time_line_index + 1:
                    ]
                )
            )

            if subtitle:

                result.append(
                    SubtitleEntry(
                        index=index,
                        start=start,
                        end=end,
                        text=subtitle,
                        source="vtt",
                    )
                )

        return result

    def _parse_generic(
        self,
        text: str,
    ) -> List[SubtitleEntry]:

        result = []

        for index, line in enumerate(
            text.splitlines(),
            start=1,
        ):

            line = line.strip()

            if not line:
                continue

            match = self.TIME_PATTERN.search(
                line
            )

            if not match:

                result.append(
                    SubtitleEntry(
                        index=index,
                        start=0.0,
                        end=0.0,
                        text=self._clean_text(
                            line
                        ),
                        source="text",
                    )
                )

                continue

            start = self._parse_time(
                match.group("start")
            )

            end = self._parse_time(
                match.group("end")
            )

            subtitle = self._clean_text(
                line[match.end():]
            )

            if subtitle:

                result.append(
                    SubtitleEntry(
                        index=index,
                        start=start,
                        end=end,
                        text=subtitle,
                        source="generic",
                    )
                )

        return result

    @staticmethod
    def _parse_time(
        value: str,
    ) -> float:

        value = value.replace(
            ",",
            ".",
        )

        parts = value.split(":")

        if len(parts) == 3:

            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])

            return (
                h * 3600
                + m * 60
                + s
            )

        if len(parts) == 2:

            m = float(parts[0])
            s = float(parts[1])

            return (
                m * 60
                + s
            )

        return float(value)

    @staticmethod
    def _clean_text(
        text: str,
    ) -> str:

        text = re.sub(
            r"<[^>]+>",
            "",
            text,
        )

        text = text.replace(
            "\r",
            "",
        )

        lines = []

        for line in text.split("\n"):

            line = line.strip()

            if line:
                lines.append(line)

        return "\n".join(lines)


# ============================================================
# Timeline Service
# ============================================================

class VideoTimelineService:
    """
    映像・字幕・音声・OCRを時間軸に統合する。

    VideoAnalysisServiceの中心的なServiceの1つ。
    """

    def subtitle_at(
        self,
        timestamp: float,
        subtitles: Sequence[SubtitleEntry],
    ) -> List[SubtitleEntry]:

        return [
            subtitle
            for subtitle in subtitles
            if (
                subtitle.start
                <= timestamp
                <= subtitle.end
            )
        ]

    def transcript_at(
        self,
        timestamp: float,
        transcript: Sequence[TranscriptSegment],
    ) -> List[TranscriptSegment]:

        return [
            item
            for item in transcript
            if (
                item.start
                <= timestamp
                <= item.end
            )
        ]

    def ocr_near(
        self,
        timestamp: float,
        ocr_results: Sequence[OCRResult],
        tolerance: float = 3.0,
    ) -> List[OCRResult]:

        return [
            item
            for item in ocr_results
            if abs(
                item.timestamp
                - timestamp
            ) <= tolerance
        ]

    def build(
        self,
        frames: Sequence[FrameInfo],
        subtitles: Sequence[SubtitleEntry],
        transcript: Sequence[TranscriptSegment],
        ocr_results: Sequence[OCRResult],
        max_events: int = DEFAULT_MAX_TIMELINE_EVENTS,
    ) -> List[TimelineEvent]:

        events = []

        for frame in frames:

            timestamp = frame.timestamp

            subtitle_items = (
                self.subtitle_at(
                    timestamp,
                    subtitles,
                )
            )

            transcript_items = (
                self.transcript_at(
                    timestamp,
                    transcript,
                )
            )

            ocr_items = (
                self.ocr_near(
                    timestamp,
                    ocr_results,
                )
            )

            visual = []

            if frame.visual_description:
                visual.append(
                    frame.visual_description
                )

            events.append(
                TimelineEvent(
                    timestamp=timestamp,
                    frame_indices=[
                        frame.index
                    ],
                    visual=visual,
                    subtitles=[
                        item.text
                        for item
                        in subtitle_items
                    ],
                    transcript=[
                        item.text
                        for item
                        in transcript_items
                    ],
                    ocr=[
                        item.text
                        for item
                        in ocr_items
                    ],
                    confidence=frame.confidence,
                    metadata={
                        "frame_path": frame.path,
                    },
                )
            )

            if len(events) >= max_events:
                break

        return events


# ============================================================
# Scene Service
# ============================================================

class SceneService:
    """
    動画を一定区間に分割する。

    将来的にはAIによる本格的なScene Detectionへ
    置き換えられる。
    """

    def build(
        self,
        duration: float,
        interval: float = DEFAULT_SCENE_INTERVAL,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
    ) -> List[Scene]:

        actual_end = (
            end_time
            if end_time is not None
            else duration
        )

        actual_end = min(
            actual_end,
            duration,
        )

        if actual_end <= start_time:
            return []

        scenes = []

        index = 0

        current = start_time

        while current < actual_end:

            scene_end = min(
                current + interval,
                actual_end,
            )

            scenes.append(
                Scene(
                    index=index,
                    start=current,
                    end=scene_end,
                )
            )

            current = scene_end

            index += 1

        return scenes

    def attach_timeline(
        self,
        scenes: List[Scene],
        frames: Sequence[FrameInfo],
        subtitles: Sequence[SubtitleEntry],
        transcript: Sequence[TranscriptSegment],
        ocr: Sequence[OCRResult],
    ) -> List[Scene]:

        for scene in scenes:

            for frame in frames:

                if (
                    scene.start
                    <= frame.timestamp
                    < scene.end
                ):

                    scene.frame_indices.append(
                        frame.index
                    )

                    if frame.visual_description:
                        scene.visual_summary += (
                            " "
                            + frame.visual_description
                        )

            subtitle_text = []

            for item in subtitles:

                if self._overlap(
                    scene.start,
                    scene.end,
                    item.start,
                    item.end,
                ):

                    subtitle_text.append(
                        item.text
                    )

            scene.subtitle_text = (
                "\n".join(
                    dict.fromkeys(
                        subtitle_text
                    )
                )
            )

            transcript_text = []

            for item in transcript:

                if self._overlap(
                    scene.start,
                    scene.end,
                    item.start,
                    item.end,
                ):

                    transcript_text.append(
                        item.text
                    )

            scene.transcript_text = (
                "\n".join(
                    transcript_text
                )
            )

            ocr_text = []

            for item in ocr:

                if (
                    scene.start
                    <= item.timestamp
                    < scene.end
                ):

                    ocr_text.append(
                        item.text
                    )

            scene.ocr_text = (
                "\n".join(
                    dict.fromkeys(
                        ocr_text
                    )
                )
            )

        return scenes

    @staticmethod
    def _overlap(
        a_start: float,
        a_end: float,
        b_start: float,
        b_end: float,
    ) -> bool:

        return (
            a_start < b_end
            and b_start < a_end
        )


# ============================================================
# Prompt Builder
# ============================================================

class VideoPromptBuilder:
    """
    Video AI用Prompt生成。

    Prompt生成もServiceとして分離。
    """

    def build(
        self,
        *,
        instruction: str,
        metadata: VideoMetadata,
        subtitles: Sequence[SubtitleEntry],
        transcript: Sequence[TranscriptSegment],
        scenes: Sequence[Scene],
        timeline: Sequence[TimelineEvent],
        language: str = "ja",
    ) -> str:

        subtitle_text = self._format_subtitles(
            subtitles
        )

        transcript_text = (
            self._format_transcript(
                transcript
            )
        )

        scene_text = self._format_scenes(
            scenes
        )

        timeline_text = (
            self._format_timeline(
                timeline
            )
        )

        return f"""
あなたは高度な動画解析AIです。

動画を単純に要約するのではなく、
映像・音声・字幕・OCR・時間情報を
関連付けて解析してください。

==================================================
ユーザー要求
==================================================

{instruction or "動画の内容を詳しく解析してください。"}

==================================================
動画情報
==================================================

ファイル名:
{metadata.filename}

長さ:
{metadata.duration:.3f} 秒

解像度:
{metadata.width} x {metadata.height}

FPS:
{metadata.fps:.3f}

動画Codec:
{metadata.video_codec}

音声Codec:
{metadata.audio_codec}

==================================================
字幕
==================================================

{subtitle_text}

==================================================
音声文字起こし
==================================================

{transcript_text}

==================================================
シーン
==================================================

{scene_text}

==================================================
タイムライン
==================================================

{timeline_text}

==================================================
解析ルール
==================================================

1.
映像から確認できる事実と、
AIによる推測を区別してください。

2.
字幕と音声が一致している場合、
その情報を統合してください。

3.
字幕と映像が矛盾する場合、
矛盾を報告してください。

4.
画面上にコードがある場合、
可能な範囲でコードを抽出してください。

5.
画面上の文字がある場合、
重要なものを抽出してください。

6.
動画内の重要な時間をタイムスタンプ付きで示してください。

7.
動画の内容をKnowledgeとして再利用できる形にしてください。

8.
不明な情報を勝手に補完しないでください。

9.
確信度が低い情報には、
uncertaintiesへ記録してください。

==================================================
出力形式
==================================================

JSON形式:

{{
    "title": "",
    "summary": "",
    "description": "",

    "keywords": [],

    "concepts": [],

    "important_points": [],

    "sections": [],

    "timeline": [],

    "detected_objects": [],

    "detected_text": [],

    "code": [],

    "spoken_content": "",

    "subtitle_summary": "",

    "questions": [],

    "answers": [],

    "knowledge": [],

    "confidence": 0.0,

    "uncertainties": []
}}

使用言語:
{language}
""".strip()

    @staticmethod
    def _format_subtitles(
        subtitles: Sequence[SubtitleEntry],
    ) -> str:

        if not subtitles:
            return "(字幕なし)"

        lines = []

        for item in subtitles[:500]:

            lines.append(
                f"[{item.start:.3f}s - "
                f"{item.end:.3f}s] "
                f"{item.text}"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_transcript(
        transcript: Sequence[TranscriptSegment],
    ) -> str:

        if not transcript:
            return "(文字起こしなし)"

        lines = []

        for item in transcript[:500]:

            lines.append(
                f"[{item.start:.3f}s - "
                f"{item.end:.3f}s] "
                f"{item.text}"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_scenes(
        scenes: Sequence[Scene],
    ) -> str:

        if not scenes:
            return "(シーンなし)"

        lines = []

        for scene in scenes[:200]:

            lines.append(
                f"Scene {scene.index}: "
                f"{scene.start:.3f}s - "
                f"{scene.end:.3f}s\n"
                f"字幕: "
                f"{scene.subtitle_text[:1000]}\n"
                f"音声: "
                f"{scene.transcript_text[:1000]}\n"
                f"OCR: "
                f"{scene.ocr_text[:1000]}"
            )

        return "\n\n".join(lines)

    @staticmethod
    def _format_timeline(
        timeline: Sequence[TimelineEvent],
    ) -> str:

        if not timeline:
            return "(タイムラインなし)"

        lines = []

        for event in timeline[:500]:

            lines.append(
                f"[{event.timestamp:.3f}s]\n"
                f"映像: "
                f"{' / '.join(event.visual)}\n"
                f"字幕: "
                f"{' / '.join(event.subtitles)}\n"
                f"音声: "
                f"{' / '.join(event.transcript)}\n"
                f"OCR: "
                f"{' / '.join(event.ocr)}"
            )

        return "\n\n".join(lines)


# ============================================================
# Knowledge Builder
# ============================================================

class VideoKnowledgeBuilder:
    """
    動画解析結果をKnowledgeManager向けデータへ変換する。
    """

    def build(
        self,
        *,
        metadata: VideoMetadata,
        analysis: Dict[str, Any],
        scenes: Sequence[Scene],
        timeline: Sequence[TimelineEvent],
    ) -> Dict[str, Any]:

        return {
            "type": "video_knowledge",

            "source_type": "video",

            "title": (
                analysis.get(
                    "title"
                )
                or Path(
                    metadata.filename
                ).stem
            ),

            "summary": analysis.get(
                "summary",
                "",
            ),

            "description": analysis.get(
                "description",
                "",
            ),

            "keywords": analysis.get(
                "keywords",
                [],
            ),

            "concepts": analysis.get(
                "concepts",
                [],
            ),

            "important_points": analysis.get(
                "important_points",
                [],
            ),

            "sections": analysis.get(
                "sections",
                [],
            ),

            "source": {
                "path": metadata.path,
                "filename": metadata.filename,
                "duration": metadata.duration,
                "sha256": metadata.sha256,
            },

            "timeline": [
                event.to_dict()
                for event in timeline
            ],

            "scenes": [
                scene.to_dict()
                for scene in scenes
            ],

            "metadata": {
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),

                "service": SERVICE_NAME,
            },
        }


# ============================================================
# Main Service
# ============================================================

class VideoAnalysisService:
    """
    動画解析の中核。

    使用例:

        service = VideoAnalysisService(
            video_provider=gemini_provider
        )

        result = await service.analyze(
            VideoInput(
                video_path="sample.mp4",
                instruction=(
                    "この動画から"
                    "C++コードを抽出してください"
                )
            )
        )
    """

    def __init__(
        self,
        *,
        ffmpeg_service: Optional[
            FFmpegService
        ] = None,

        subtitle_service: Optional[
            SubtitleService
        ] = None,

        timeline_service: Optional[
            VideoTimelineService
        ] = None,

        scene_service: Optional[
            SceneService
        ] = None,

        prompt_builder: Optional[
            VideoPromptBuilder
        ] = None,

        knowledge_builder: Optional[
            VideoKnowledgeBuilder
        ] = None,

        video_provider: Optional[
            VideoProvider
        ] = None,

        transcription_provider: Optional[
            TranscriptionProvider
        ] = None,

        ocr_provider: Optional[
            OCRProvider
        ] = None,

        work_dir: str = DEFAULT_WORK_DIR,
    ):

        self.ffmpeg = (
            ffmpeg_service
            or FFmpegService()
        )

        self.subtitle_service = (
            subtitle_service
            or SubtitleService()
        )

        self.timeline_service = (
            timeline_service
            or VideoTimelineService()
        )

        self.scene_service = (
            scene_service
            or SceneService()
        )

        self.prompt_builder = (
            prompt_builder
            or VideoPromptBuilder()
        )

        self.knowledge_builder = (
            knowledge_builder
            or VideoKnowledgeBuilder()
        )

        self.video_provider = video_provider

        self.transcription_provider = (
            transcription_provider
        )

        self.ocr_provider = ocr_provider

        self.work_dir = Path(
            work_dir
        )

        self.work_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ========================================================
    # Public API
    # ========================================================

    async def analyze(
        self,
        video_input: Union[
            VideoInput,
            Dict[str, Any],
        ],
    ) -> VideoAnalysisResult:

        started_at = time.perf_counter()

        if isinstance(
            video_input,
            dict,
        ):

            video_input = self._from_dict(
                video_input
            )

        warnings: List[str] = []

        errors: List[str] = []

        # ----------------------------------------------------
        # 1. Validate
        # ----------------------------------------------------

        video_path = self._validate_input(
            video_input
        )

        # ----------------------------------------------------
        # 2. Job directory
        # ----------------------------------------------------

        job_id = self._create_job_id(
            video_path
        )

        job_dir = (
            self.work_dir
            / job_id
        )

        job_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        frame_dir = (
            job_dir
            / "frames"
        )

        audio_dir = (
            job_dir
            / "audio"
        )

        frame_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        audio_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ----------------------------------------------------
        # 3. Metadata
        # ----------------------------------------------------

        try:

            metadata = (
                await self._get_metadata(
                    video_path
                )
            )

        except Exception as exc:

            logger.exception(
                "動画メタデータ取得失敗"
            )

            errors.append(
                f"metadata: {exc}"
            )

            return self._failure_result(
                video_input,
                video_path,
                errors,
                warnings,
                started_at,
            )

        # ----------------------------------------------------
        # 4. Resolve time range
        # ----------------------------------------------------

        start_time, end_time = (
            self._resolve_time_range(
                video_input,
                metadata,
            )
        )

        # ----------------------------------------------------
        # 5. Subtitle
        # ----------------------------------------------------

        subtitles: List[
            SubtitleEntry
        ] = []

        subtitle_path = (
            video_input.subtitle_path
        )

        if not subtitle_path:

            subtitle_path = (
                self.subtitle_service.discover(
                    str(video_path)
                )
            )

        if subtitle_path:

            try:

                subtitles = (
                    await asyncio.to_thread(
                        self.subtitle_service.parse,
                        subtitle_path,
                        video_input.max_subtitles,
                    )
                )

                subtitles = (
                    self._clip_subtitles(
                        subtitles,
                        start_time,
                        end_time,
                    )
                )

            except Exception as exc:

                warnings.append(
                    f"subtitle: {exc}"
                )

        # ----------------------------------------------------
        # 6. Frames
        # ----------------------------------------------------

        frames: List[
            FrameInfo
        ] = []

        if video_input.extract_frames:

            try:

                frame_paths = (
                    await self.ffmpeg.extract_frames(
                        video_path=str(
                            video_path
                        ),
                        output_dir=str(
                            frame_dir
                        ),
                        start_time=start_time,
                        end_time=end_time,
                        interval=video_input.frame_interval,
                        max_frames=video_input.max_frames,
                    )
                )

                frames = (
                    self._build_frame_info(
                        frame_paths,
                        start_time,
                        video_input.frame_interval,
                    )
                )

            except Exception as exc:

                warnings.append(
                    f"frames: {exc}"
                )

        # ----------------------------------------------------
        # 7. OCR
        # ----------------------------------------------------

        ocr_results: List[
            OCRResult
        ] = []

        if (
            video_input.use_ocr
            and self.ocr_provider
        ):

            try:

                ocr_results = (
                    await self._run_ocr(
                        frames
                    )
                )

            except Exception as exc:

                warnings.append(
                    f"ocr: {exc}"
                )

        # ----------------------------------------------------
        # 8. Audio
        # ----------------------------------------------------

        audio_path: Optional[str] = None

        if video_input.extract_audio:

            try:

                audio_path = (
                    await self.ffmpeg.extract_audio(
                        video_path=str(
                            video_path
                        ),
                        output_path=str(
                            audio_dir
                            / "audio.wav"
                        ),
                        start_time=start_time,
                        end_time=end_time,
                    )
                )

            except Exception as exc:

                warnings.append(
                    f"audio: {exc}"
                )

        # ----------------------------------------------------
        # 9. Transcription
        # ----------------------------------------------------

        transcript: List[
            TranscriptSegment
        ] = []

        if (
            video_input.use_transcription
            and self.transcription_provider
            and audio_path
        ):

            try:

                transcript = (
                    await self._run_transcription(
                        audio_path,
                        video_input.language,
                    )
                )

            except Exception as exc:

                warnings.append(
                    f"transcription: {exc}"
                )

        # ----------------------------------------------------
        # 10. AI frame description
        # ----------------------------------------------------

        if (
            video_input.use_ai
            and self.video_provider
            and frames
        ):

            try:

                frames = (
                    await self._describe_frames(
                        frames
                    )
                )

            except Exception as exc:

                warnings.append(
                    f"frame_ai: {exc}"
                )

        # ----------------------------------------------------
        # 11. Timeline
        # ----------------------------------------------------

        timeline: List[
            TimelineEvent
        ] = []

        try:

            timeline = (
                self.timeline_service.build(
                    frames,
                    subtitles,
                    transcript,
                    ocr_results,
                    video_input.max_timeline_events,
                )
            )

        except Exception as exc:

            warnings.append(
                f"timeline: {exc}"
            )

        # ----------------------------------------------------
        # 12. Scene
        # ----------------------------------------------------

        scenes: List[
            Scene
        ] = []

        try:

            scenes = (
                self.scene_service.build(
                    duration=metadata.duration,
                    interval=DEFAULT_SCENE_INTERVAL,
                    start_time=start_time,
                    end_time=end_time,
                )
            )

            scenes = (
                self.scene_service.attach_timeline(
                    scenes,
                    frames,
                    subtitles,
                    transcript,
                    ocr_results,
                )
            )

        except Exception as exc:

            warnings.append(
                f"scenes: {exc}"
            )

        # ----------------------------------------------------
        # 13. AI video analysis
        # ----------------------------------------------------

        analysis: Dict[str, Any] = {}

        if (
            video_input.use_ai
            and self.video_provider
        ):

            try:

                prompt = (
                    self.prompt_builder.build(
                        instruction=(
                            video_input.instruction
                        ),
                        metadata=metadata,
                        subtitles=subtitles,
                        transcript=transcript,
                        scenes=scenes,
                        timeline=timeline,
                        language=(
                            video_input.language
                        ),
                    )
                )

                analysis = (
                    await self.video_provider.analyze(
                        video_path=str(
                            video_path
                        ),
                        prompt=prompt,
                        metadata=metadata.to_dict(),
                        frames=[
                            frame.to_dict()
                            for frame in frames
                        ],
                        subtitles=[
                            item.to_dict()
                            for item in subtitles
                        ],
                        transcript=[
                            item.to_dict()
                            for item in transcript
                        ],
                        timeline=[
                            item.to_dict()
                            for item in timeline
                        ],
                        scenes=[
                            item.to_dict()
                            for item in scenes
                        ],
                    )
                )

                if not isinstance(
                    analysis,
                    dict,
                ):

                    analysis = {
                        "summary": str(
                            analysis
                        )
                    }

            except Exception as exc:

                logger.exception(
                    "AI動画解析失敗"
                )

                warnings.append(
                    f"video_ai: {exc}"
                )

        elif video_input.use_ai:

            warnings.append(
                "VideoProviderが未設定のため、"
                "AI動画解析を実行していません。"
            )

        # ----------------------------------------------------
        # 14. Attach AI scene information
        # ----------------------------------------------------

        scenes = (
            self._attach_ai_analysis_to_scenes(
                scenes,
                analysis,
            )
        )

        # ----------------------------------------------------
        # 15. Build Knowledge
        # ----------------------------------------------------

        knowledge = (
            self.knowledge_builder.build(
                metadata=metadata,
                analysis=analysis,
                scenes=scenes,
                timeline=timeline,
            )
        )

        # ----------------------------------------------------
        # 16. Statistics
        # ----------------------------------------------------

        processing_time = (
            time.perf_counter()
            - started_at
        )

        statistics = {
            "duration_seconds": (
                metadata.duration
            ),

            "analysis_start": start_time,

            "analysis_end": end_time,

            "frames": len(frames),

            "subtitles": len(subtitles),

            "transcript_segments": len(
                transcript
            ),

            "ocr_results": len(
                ocr_results
            ),

            "scenes": len(scenes),

            "timeline_events": len(
                timeline
            ),

            "processing_time_seconds": (
                processing_time
            ),
        }

        # ----------------------------------------------------
        # 17. Result
        # ----------------------------------------------------

        result = VideoAnalysisResult(
            success=(
                len(errors) == 0
            ),
            video=metadata.to_dict(),
            input=video_input.to_dict(),
            frames=[
                frame.to_dict()
                for frame in frames
            ],
            subtitles=[
                item.to_dict()
                for item in subtitles
            ],
            transcript=[
                item.to_dict()
                for item in transcript
            ],
            ocr=[
                item.to_dict()
                for item in ocr_results
            ],
            scenes=[
                scene.to_dict()
                for scene in scenes
            ],
            timeline=[
                event.to_dict()
                for event in timeline
            ],
            analysis=analysis,
            knowledge=knowledge,
            statistics=statistics,
            warnings=warnings,
            errors=errors,
            processing_time_seconds=(
                processing_time
            ),
        )

        # ----------------------------------------------------
        # 18. Save intermediate
        # ----------------------------------------------------

        if video_input.save_intermediate:

            try:

                await self._save_intermediate(
                    job_dir,
                    result,
                )

            except Exception as exc:

                result.warnings.append(
                    f"intermediate_save: {exc}"
                )

        return result

    # ========================================================
    # Input
    # ========================================================

    def _from_dict(
        self,
        data: Dict[str, Any],
    ) -> VideoInput:

        path = (
            data.get("video_path")
            or data.get("path")
            or data.get("file")
            or data.get("input")
        )

        if not path:

            raise VideoInputError(
                "video_pathが指定されていません。"
            )

        return VideoInput(
            video_path=str(path),

            subtitle_path=data.get(
                "subtitle_path"
            ),

            start_time=self._optional_float(
                data.get("start_time")
            ),

            end_time=self._optional_float(
                data.get("end_time")
            ),

            language=data.get(
                "language",
                "ja",
            ),

            instruction=data.get(
                "instruction",
                data.get(
                    "prompt",
                    "",
                ),
            ),

            provider=data.get(
                "provider"
            ),

            extract_audio=bool(
                data.get(
                    "extract_audio",
                    True,
                )
            ),

            extract_frames=bool(
                data.get(
                    "extract_frames",
                    True,
                )
            ),

            use_ocr=bool(
                data.get(
                    "use_ocr",
                    False,
                )
            ),

            use_transcription=bool(
                data.get(
                    "use_transcription",
                    False,
                )
            ),

            use_ai=bool(
                data.get(
                    "use_ai",
                    True,
                )
            ),

            frame_interval=float(
                data.get(
                    "frame_interval",
                    DEFAULT_FRAME_INTERVAL,
                )
            ),

            max_frames=int(
                data.get(
                    "max_frames",
                    DEFAULT_MAX_FRAMES,
                )
            ),

            max_subtitles=int(
                data.get(
                    "max_subtitles",
                    DEFAULT_MAX_SUBTITLES,
                )
            ),

            max_timeline_events=int(
                data.get(
                    "max_timeline_events",
                    DEFAULT_MAX_TIMELINE_EVENTS,
                )
            ),

            save_intermediate=bool(
                data.get(
                    "save_intermediate",
                    False,
                )
            ),

            metadata=data.get(
                "metadata",
                {},
            ),
        )

    # ========================================================
    # Validation
    # ========================================================

    def _validate_input(
        self,
        video_input: VideoInput,
    ) -> Path:

        path = (
            Path(
                video_input.video_path
            )
            .expanduser()
            .resolve()
        )

        if not path.exists():

            raise VideoInputError(
                f"動画が存在しません: {path}"
            )

        if not path.is_file():

            raise VideoInputError(
                f"動画ファイルではありません: {path}"
            )

        if (
            path.suffix.lower()
            not in SUPPORTED_VIDEO_EXTENSIONS
        ):

            raise VideoInputError(
                "未対応の動画形式です: "
                f"{path.suffix}"
            )

        if (
            video_input.start_time is not None
            and video_input.start_time < 0
        ):

            raise VideoInputError(
                "start_timeは0以上で指定してください。"
            )

        if (
            video_input.end_time is not None
            and video_input.end_time < 0
        ):

            raise VideoInputError(
                "end_timeは0以上で指定してください。"
            )

        if (
            video_input.start_time is not None
            and video_input.end_time is not None
            and video_input.start_time
            >= video_input.end_time
        ):

            raise VideoInputError(
                "start_timeはend_timeより前にしてください。"
            )

        if video_input.frame_interval <= 0:

            raise VideoInputError(
                "frame_intervalは0より大きくしてください。"
            )

        if video_input.max_frames <= 0:

            raise VideoInputError(
                "max_framesは1以上にしてください。"
            )

        return path

    # ========================================================
    # Metadata
    # ========================================================

    async def _get_metadata(
        self,
        path: Path,
    ) -> VideoMetadata:

        probe = await self.ffmpeg.probe(
            str(path)
        )

        streams = probe.get(
            "streams",
            [],
        )

        format_info = probe.get(
            "format",
            {},
        )

        video_stream = None
        audio_stream = None

        for stream in streams:

            codec_type = stream.get(
                "codec_type"
            )

            if (
                codec_type == "video"
                and video_stream is None
            ):

                video_stream = stream

            if (
                codec_type == "audio"
                and audio_stream is None
            ):

                audio_stream = stream

        fps = 0.0

        if video_stream:

            rate = (
                video_stream.get(
                    "avg_frame_rate"
                )
                or video_stream.get(
                    "r_frame_rate"
                )
            )

            if rate and rate != "0/0":

                try:

                    numerator, denominator = (
                        rate.split("/")
                    )

                    denominator = float(
                        denominator
                    )

                    if denominator != 0:

                        fps = (
                            float(numerator)
                            / denominator
                        )

                except Exception:
                    pass

        duration = self._safe_float(
            format_info.get(
                "duration"
            )
        )

        return VideoMetadata(
            path=str(path),

            filename=path.name,

            extension=path.suffix.lower(),

            size_bytes=path.stat().st_size,

            duration=duration,

            width=self._safe_int(
                video_stream.get(
                    "width"
                )
                if video_stream
                else 0
            ),

            height=self._safe_int(
                video_stream.get(
                    "height"
                )
                if video_stream
                else 0
            ),

            fps=fps,

            video_codec=(
                video_stream.get(
                    "codec_name"
                )
                if video_stream
                else None
            ),

            audio_codec=(
                audio_stream.get(
                    "codec_name"
                )
                if audio_stream
                else None
            ),

            has_video=(
                video_stream is not None
            ),

            has_audio=(
                audio_stream is not None
            ),

            mime_type=(
                mimetypes.guess_type(
                    str(path)
                )[0]
            ),

            sha256=await asyncio.to_thread(
                self._sha256,
                path,
            ),
        )

    # ========================================================
    # Time Range
    # ========================================================

    def _resolve_time_range(
        self,
        video_input: VideoInput,
        metadata: VideoMetadata,
    ) -> Tuple[float, float]:

        start = (
            video_input.start_time
            if video_input.start_time is not None
            else 0.0
        )

        end = (
            video_input.end_time
            if video_input.end_time is not None
            else metadata.duration
        )

        start = max(
            0.0,
            start,
        )

        end = min(
            metadata.duration,
            end,
        )

        if end < start:
            end = start

        return start, end

    # ========================================================
    # Frames
    # ========================================================

    def _build_frame_info(
        self,
        paths: Sequence[str],
        start_time: float,
        interval: float,
    ) -> List[FrameInfo]:

        frames = []

        for index, path in enumerate(paths):

            timestamp = (
                start_time
                + index * interval
            )

            frames.append(
                FrameInfo(
                    index=index,
                    timestamp=timestamp,
                    path=path,
                )
            )

        return frames

    # ========================================================
    # OCR
    # ========================================================

    async def _run_ocr(
        self,
        frames: Sequence[FrameInfo],
    ) -> List[OCRResult]:

        if not self.ocr_provider:
            return []

        results = []

        semaphore = asyncio.Semaphore(4)

        async def process(
            frame: FrameInfo,
        ):

            async with semaphore:

                try:

                    result = (
                        await self.ocr_provider.recognize(
                            frame.path
                        )
                    )

                    if not isinstance(
                        result,
                        dict,
                    ):

                        result = {
                            "text": str(
                                result
                            )
                        }

                    text = str(
                        result.get(
                            "text",
                            "",
                        )
                    ).strip()

                    if not text:
                        return

                    results.append(
                        OCRResult(
                            timestamp=(
                                frame.timestamp
                            ),
                            text=text,
                            confidence=(
                                result.get(
                                    "confidence"
                                )
                            ),
                            frame_path=(
                                frame.path
                            ),
                            metadata=result,
                        )
                    )

                    frame.ocr_text = text

                except Exception as exc:

                    logger.warning(
                        "OCR失敗 frame=%s: %s",
                        frame.index,
                        exc,
                    )

        await asyncio.gather(
            *(
                process(frame)
                for frame in frames
            )
        )

        results.sort(
            key=lambda x: x.timestamp
        )

        return results

    # ========================================================
    # Transcription
    # ========================================================

    async def _run_transcription(
        self,
        audio_path: str,
        language: str,
    ) -> List[TranscriptSegment]:

        if not self.transcription_provider:
            return []

        raw = (
            await self.transcription_provider.transcribe(
                audio_path,
                language,
            )
        )

        result = []

        for index, item in enumerate(
            raw,
            start=1,
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            start = self._safe_float(
                item.get(
                    "start",
                    0,
                )
            )

            end = self._safe_float(
                item.get(
                    "end",
                    start,
                )
            )

            text = str(
                item.get(
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            result.append(
                TranscriptSegment(
                    index=index,
                    start=start,
                    end=end,
                    text=text,
                    language=item.get(
                        "language",
                        language,
                    ),
                    confidence=item.get(
                        "confidence"
                    ),
                    speaker=item.get(
                        "speaker"
                    ),
                    metadata=item,
                )
            )

        return result

    # ========================================================
    # Frame AI
    # ========================================================

    async def _describe_frames(
        self,
        frames: List[FrameInfo],
    ) -> List[FrameInfo]:

        """
        フレーム単体のAI解析。

        実際のProviderが対応している場合に利用する。

        VideoProviderにframe description機能が無い場合は
        何も変更しない。
        """

        method = getattr(
            self.video_provider,
            "describe_frame",
            None,
        )

        if not callable(method):
            return frames

        semaphore = asyncio.Semaphore(3)

        async def process(
            frame: FrameInfo,
        ):

            async with semaphore:

                try:

                    result = await method(
                        image_path=frame.path,
                        timestamp=frame.timestamp,
                    )

                    if isinstance(
                        result,
                        dict,
                    ):

                        frame.visual_description = (
                            result.get(
                                "description"
                            )
                        )

                        frame.confidence = (
                            result.get(
                                "confidence"
                            )
                        )

                except Exception as exc:

                    logger.warning(
                        "フレームAI解析失敗 "
                        "frame=%s: %s",
                        frame.index,
                        exc,
                    )

        await asyncio.gather(
            *(
                process(frame)
                for frame in frames
            )
        )

        return frames

    # ========================================================
    # Scene AI
    # ========================================================

    def _attach_ai_analysis_to_scenes(
        self,
        scenes: List[Scene],
        analysis: Dict[str, Any],
    ) -> List[Scene]:

        ai_sections = analysis.get(
            "sections",
            [],
        )

        if not isinstance(
            ai_sections,
            list,
        ):
            return scenes

        for section in ai_sections:

            if not isinstance(
                section,
                dict,
            ):
                continue

            start = self._safe_float(
                section.get(
                    "start",
                    section.get(
                        "start_time",
                        -1,
                    ),
                ),
                -1,
            )

            end = self._safe_float(
                section.get(
                    "end",
                    section.get(
                        "end_time",
                        -1,
                    ),
                ),
                -1,
            )

            summary = str(
                section.get(
                    "summary",
                    "",
                )
            )

            keywords = section.get(
                "keywords",
                [],
            )

            for scene in scenes:

                if (
                    start < scene.end
                    and end > scene.start
                ):

                    if summary:

                        scene.ai_summary = (
                            summary
                        )

                    if isinstance(
                        keywords,
                        list,
                    ):

                        scene.keywords.extend(
                            str(item)
                            for item in keywords
                        )

                    scene.keywords = list(
                        dict.fromkeys(
                            scene.keywords
                        )
                    )

        return scenes

    # ========================================================
    # Intermediate Save
    # ========================================================

    async def _save_intermediate(
        self,
        job_dir: Path,
        result: VideoAnalysisResult,
    ):

        path = (
            job_dir
            / "analysis_result.json"
        )

        await asyncio.to_thread(
            self._write_json,
            path,
            result.to_dict(),
        )

    # ========================================================
    # Failure
    # ========================================================

    def _failure_result(
        self,
        video_input: VideoInput,
        video_path: Path,
        errors: List[str],
        warnings: List[str],
        started_at: float,
    ) -> VideoAnalysisResult:

        return VideoAnalysisResult(
            success=False,

            video={
                "path": str(video_path),
                "filename": video_path.name,
            },

            input=video_input.to_dict(),

            errors=errors,

            warnings=warnings,

            processing_time_seconds=(
                time.perf_counter()
                - started_at
            ),
        )

    # ========================================================
    # Helpers
    # ========================================================

    @staticmethod
    def _clip_subtitles(
        subtitles: Sequence[SubtitleEntry],
        start_time: float,
        end_time: float,
    ) -> List[SubtitleEntry]:

        result = []

        for item in subtitles:

            if (
                item.end < start_time
                or item.start > end_time
            ):
                continue

            result.append(
                item
            )

        return result

    @staticmethod
    def _create_job_id(
        path: Path,
    ) -> str:

        stat = path.stat()

        raw = (
            str(path.resolve())
            + ":"
            + str(stat.st_size)
            + ":"
            + str(stat.st_mtime_ns)
        )

        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]

    @staticmethod
    def _sha256(
        path: Path,
    ) -> str:

        digest = hashlib.sha256()

        with path.open(
            "rb"
        ) as f:

            while True:

                chunk = f.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

        return digest.hexdigest()

    @staticmethod
    def _write_json(
        path: Path,
        data: Dict[str, Any],
    ):

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

    @staticmethod
    def _optional_float(
        value: Any,
    ) -> Optional[float]:

        if value is None:
            return None

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def _safe_int(
        value: Any,
        default: int = 0,
    ) -> int:

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return default


# ============================================================
# Simple Test Providers
# ============================================================

class DummyVideoProvider:
    """
    動作確認用の簡易VideoProvider。

    実際のAIではない。
    """

    async def analyze(
        self,
        *,
        video_path: str,
        prompt: str,
        metadata: Dict[str, Any],
        frames: Sequence[Dict[str, Any]],
        subtitles: Sequence[Dict[str, Any]],
        transcript: Sequence[Dict[str, Any]],
        timeline: Sequence[Dict[str, Any]],
        scenes: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:

        return {
            "title": Path(
                video_path
            ).stem,

            "summary": (
                "DummyVideoProviderによる"
                "テスト解析です。"
            ),

            "description": (
                f"フレーム={len(frames)}, "
                f"字幕={len(subtitles)}, "
                f"音声区間={len(transcript)}, "
                f"シーン={len(scenes)}"
            ),

            "keywords": [],

            "concepts": [],

            "important_points": [],

            "sections": [],

            "timeline": [],

            "detected_objects": [],

            "detected_text": [],

            "code": [],

            "spoken_content": "",

            "subtitle_summary": "\n".join(
                item.get(
                    "text",
                    "",
                )
                for item in subtitles[:20]
            ),

            "questions": [],

            "answers": [],

            "knowledge": [],

            "confidence": 0.1,

            "uncertainties": [
                "Dummy Providerです。"
            ],
        }


class DummyTranscriptionProvider:
    """
    音声文字起こしテスト用。
    """

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Sequence[Dict[str, Any]]:

        return [
            {
                "start": 0.0,
                "end": 3.0,
                "text": (
                    "これはテスト用の"
                    "文字起こしです。"
                ),
                "language": language,
                "confidence": 0.1,
            }
        ]


class DummyOCRProvider:
    """
    OCRテスト用。
    """

    async def recognize(
        self,
        image_path: str,
    ) -> Dict[str, Any]:

        return {
            "text": "",
            "confidence": 0.0,
        }


# ============================================================
# Factory
# ============================================================

def create_video_analysis_service(
    *,
    video_provider: Optional[
        VideoProvider
    ] = None,

    transcription_provider: Optional[
        TranscriptionProvider
    ] = None,

    ocr_provider: Optional[
        OCRProvider
    ] = None,

    work_dir: str = DEFAULT_WORK_DIR,
) -> VideoAnalysisService:

    return VideoAnalysisService(
        video_provider=video_provider,
        transcription_provider=(
            transcription_provider
        ),
        ocr_provider=ocr_provider,
        work_dir=work_dir,
    )


# ============================================================
# Convenience Function
# ============================================================

async def analyze_video(
    video_path: str,
    *,
    instruction: str = "",
    subtitle_path: Optional[str] = None,
    video_provider: Optional[
        VideoProvider
    ] = None,
    transcription_provider: Optional[
        TranscriptionProvider
    ] = None,
    ocr_provider: Optional[
        OCRProvider
    ] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    language: str = "ja",
) -> Dict[str, Any]:

    service = create_video_analysis_service(
        video_provider=video_provider,
        transcription_provider=(
            transcription_provider
        ),
        ocr_provider=ocr_provider,
    )

    result = await service.analyze(
        VideoInput(
            video_path=video_path,

            subtitle_path=subtitle_path,

            instruction=instruction,

            start_time=start_time,

            end_time=end_time,

            language=language,

            use_ai=(
                video_provider is not None
            ),

            use_transcription=(
                transcription_provider is not None
            ),

            use_ocr=(
                ocr_provider is not None
            ),
        )
    )

    return result.to_dict()


# ============================================================
# CLI
# ============================================================

async def _cli_async():

    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "VideoAnalysisService"
        )
    )

    parser.add_argument(
        "video",
        help="動画ファイル",
    )

    parser.add_argument(
        "--subtitle",
        default=None,
        help="SRT/VTT字幕",
    )

    parser.add_argument(
        "--instruction",
        default=(
            "動画の内容を要約してください。"
        ),
        help="解析指示",
    )

    parser.add_argument(
        "--start",
        type=float,
        default=None,
        help="解析開始秒",
    )

    parser.add_argument(
        "--end",
        type=float,
        default=None,
        help="解析終了秒",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_FRAME_INTERVAL,
        help="フレーム間隔",
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=DEFAULT_MAX_FRAMES,
        help="最大フレーム数",
    )

    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="AI解析を無効化",
    )

    parser.add_argument(
        "--save-intermediate",
        action="store_true",
        help="中間結果を保存",
    )

    args = parser.parse_args()

    provider = None

    if not args.no_ai:
        provider = DummyVideoProvider()

    service = VideoAnalysisService(
        video_provider=provider,
    )

    result = await service.analyze(
        VideoInput(
            video_path=args.video,

            subtitle_path=args.subtitle,

            instruction=args.instruction,

            start_time=args.start,

            end_time=args.end,

            frame_interval=args.interval,

            max_frames=args.max_frames,

            use_ai=(
                not args.no_ai
            ),

            save_intermediate=(
                args.save_intermediate
            ),
        )
    )

    print(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )


def main():

    asyncio.run(
        _cli_async()
    )


if __name__ == "__main__":
    main()
```
