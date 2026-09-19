```python
# -*- coding: utf-8 -*-
"""
video_handler.py

動画解析を担当するHandler。

目的
----
自作AIから動画解析要求を受け取り、

    動画
      ↓
    VideoHandler
      ↓
    VideoAnalysisService
      ↓
    ┌─────────────────────────┐
    │ 動画メタデータ           │
    │ フレーム                 │
    │ 音声                     │
    │ 字幕                     │
    │ タイムライン             │
    └─────────────────────────┘
      ↓
    AI Video Model
      ↓
    構造化された解析結果
      ↓
    KnowledgeManager等

という流れを作る。

設計方針
--------
1. 特定AIベンダーに依存しない
2. Gemini / OpenAI / Claude / Local AIを将来切り替え可能にする
3. 字幕付き動画を時間軸で扱えるようにする
4. 動画全体だけでなく区間解析にも対応する
5. 解析結果をJSONとして保存しやすくする
6. KnowledgeManagerへ渡せる構造にする
7. FFmpegが利用できればフレーム・音声抽出を行う
8. AIが利用できない場合でもデジタル動画解析だけは実行できる
9. エラーでChatOrchestrator全体を停止させない
10. 将来的なPlugin/Service分離を考慮する

必要な外部コマンド
------------------
FFmpeg / ffprobe

例:
    ffmpeg -version
    ffprobe -version

Python依存
----------
標準ライブラリ中心。

AI APIはプロバイダごとに別Serviceへ切り出すことを推奨。
このファイルでは「Provider Adapter」を受け取る構造にする。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
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
    Awaitable,
    Callable,
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
# Optional BaseHandler
# ============================================================

try:
    from api.services.handlers.base_handler import BaseHandler
except Exception:
    class BaseHandler:
        """
        既存BaseHandlerが存在しない環境でも単体テストできる
        フォールバックBaseHandler。
        """

        name = "base"

        def __init__(self, *args, **kwargs):
            pass


# ============================================================
# Logger
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


# ============================================================
# Constants
# ============================================================

HANDLER_NAME = "video"

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

SUPPORTED_SUBTITLE_EXTENSIONS = {
    ".srt",
    ".vtt",
    ".ass",
    ".ssa",
    ".txt",
}

DEFAULT_FRAME_INTERVAL = 5.0

DEFAULT_MAX_FRAMES = 120

DEFAULT_MAX_FILE_SIZE_MB = 2048

DEFAULT_WORK_DIR = ".ai_video"

DEFAULT_RESULT_DIR = ".ai_video/results"

DEFAULT_FRAME_DIR = ".ai_video/frames"

DEFAULT_AUDIO_DIR = ".ai_video/audio"

DEFAULT_SUBTITLE_DIR = ".ai_video/subtitles"


# ============================================================
# Exceptions
# ============================================================

class VideoHandlerError(Exception):
    """VideoHandler共通例外。"""


class VideoValidationError(VideoHandlerError):
    """動画ファイル検証エラー。"""


class VideoToolError(VideoHandlerError):
    """FFmpeg/ffprobe等のツールエラー。"""


class VideoAIError(VideoHandlerError):
    """動画AI解析エラー。"""


class SubtitleParseError(VideoHandlerError):
    """字幕解析エラー。"""


# ============================================================
# Data Models
# ============================================================

@dataclass
class SubtitleEntry:
    """
    字幕1件。

    start:
        秒

    end:
        秒

    text:
        字幕本文
    """

    start: float
    end: float
    text: str

    index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoMetadata:
    """
    動画メタデータ。
    """

    path: str

    filename: str

    extension: str

    mime_type: Optional[str] = None

    size_bytes: int = 0

    duration: float = 0.0

    width: int = 0

    height: int = 0

    fps: float = 0.0

    video_codec: Optional[str] = None

    audio_codec: Optional[str] = None

    has_video: bool = False

    has_audio: bool = False

    created_at: Optional[str] = None

    sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoFrame:
    """
    抽出されたフレーム。
    """

    timestamp: float

    path: str

    width: int = 0

    height: int = 0

    index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoSegment:
    """
    動画の解析区間。
    """

    start: float

    end: float

    index: int = 0

    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineEvent:
    """
    動画中のある時点における統合情報。

    visual:
        AIが認識した映像情報

    audio:
        音声情報

    subtitle:
        字幕情報

    ocr:
        画面上の文字

    ai_summary:
        AIによる統合的な説明
    """

    timestamp: float

    visual: Optional[str] = None

    audio: Optional[str] = None

    subtitle: Optional[str] = None

    ocr: Optional[str] = None

    ai_summary: Optional[str] = None

    confidence: Optional[float] = None

    frame_path: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoAnalysisRequest:
    """
    VideoHandlerへの解析要求。

    例:

        VideoAnalysisRequest(
            video_path="sample.mp4",
            instruction="この動画で説明されているC++コードを抽出して"
        )
    """

    video_path: str

    instruction: str = ""

    subtitle_path: Optional[str] = None

    start_time: Optional[float] = None

    end_time: Optional[float] = None

    frame_interval: float = DEFAULT_FRAME_INTERVAL

    max_frames: int = DEFAULT_MAX_FRAMES

    extract_audio: bool = True

    extract_frames: bool = True

    analyze_subtitles: bool = True

    use_ai: bool = True

    provider: Optional[str] = None

    save_result: bool = True

    result_path: Optional[str] = None

    language: Optional[str] = "ja"

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoAnalysisResult:
    """
    VideoHandlerの最終結果。

    KnowledgeManagerへ渡すことを想定。
    """

    success: bool

    video: Dict[str, Any]

    request: Dict[str, Any]

    frames: List[Dict[str, Any]] = field(default_factory=list)

    subtitles: List[Dict[str, Any]] = field(default_factory=list)

    timeline: List[Dict[str, Any]] = field(default_factory=list)

    analysis: Dict[str, Any] = field(default_factory=dict)

    knowledge: Dict[str, Any] = field(default_factory=dict)

    errors: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# AI Provider Protocol
# ============================================================

class VideoAIProvider(Protocol):
    """
    Video AI Providerの共通インターフェース。

    Gemini / OpenAI / Claude / Local AIなどを
    この形式に合わせる。

    必須:
        analyze_video()

    任意:
        analyze_frames()
        analyze_timeline()
    """

    async def analyze_video(
        self,
        video_path: str,
        prompt: str,
        metadata: Dict[str, Any],
        subtitles: Sequence[Dict[str, Any]],
        frames: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        ...


# ============================================================
# Utility Functions
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _format_timestamp(seconds: float) -> str:
    """
    秒をHH:MM:SS.mmmへ変換。
    """

    seconds = max(0.0, float(seconds))

    hours = int(seconds // 3600)

    minutes = int((seconds % 3600) // 60)

    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def _parse_timestamp(value: str) -> float:
    """
    以下を解析。

    00:01:20,500
    00:01:20.500
    01:20.500
    01:20
    80.5
    """

    value = value.strip()

    if not value:
        return 0.0

    if value.replace(".", "", 1).isdigit():
        return float(value)

    value = value.replace(",", ".")

    parts = value.split(":")

    try:
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])

            return hours * 3600 + minutes * 60 + seconds

        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])

            return minutes * 60 + seconds

    except ValueError:
        pass

    raise SubtitleParseError(
        f"タイムスタンプを解析できません: {value}"
    )


def _normalize_text(text: str) -> str:
    """
    字幕などの不要な空白を整理。
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    lines = []

    for line in text.split("\n"):
        line = line.strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def _file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    動画ファイルのSHA-256。
    """

    digest = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# ============================================================
# FFmpeg Manager
# ============================================================

class FFmpegManager:
    """
    FFmpeg / ffprobeを管理。

    VideoHandler本体からFFmpeg処理を分離することで、
    将来的に別Serviceへ移行しやすくする。
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
        return bool(self.ffmpeg_path and self.ffprobe_path)

    def require(self):
        if not self.available:
            raise VideoToolError(
                "FFmpeg / ffprobeが見つかりません。"
                "FFMPEG_PATH / FFPROBE_PATHを設定するか、"
                "PATHへFFmpegを追加してください。"
            )

    def probe(self, video_path: str) -> Dict[str, Any]:
        """
        ffprobeで動画情報を取得。
        """

        self.require()

        command = [
            self.ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )

        except subprocess.CalledProcessError as exc:
            raise VideoToolError(
                f"ffprobe実行失敗: {exc.stderr}"
            ) from exc

        try:
            return json.loads(completed.stdout)

        except json.JSONDecodeError as exc:
            raise VideoToolError(
                "ffprobeのJSONを解析できませんでした。"
            ) from exc

    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        interval: float = DEFAULT_FRAME_INTERVAL,
        max_frames: int = DEFAULT_MAX_FRAMES,
    ) -> List[VideoFrame]:
        """
        動画からフレームを抽出。

        interval秒ごとに抽出する。
        """

        self.require()

        os.makedirs(output_dir, exist_ok=True)

        duration = None

        if end_time is not None:
            duration = max(0.0, end_time - start_time)

        fps_expression = f"fps=1/{max(interval, 0.1)}"

        output_pattern = os.path.join(
            output_dir,
            "frame_%06d.jpg",
        )

        command = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            str(max(0.0, start_time)),
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
                fps_expression,
                "-frames:v",
                str(max_frames),
                "-q:v",
                "2",
                output_pattern,
            ]
        )

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        except OSError as exc:
            raise VideoToolError(
                f"FFmpeg起動失敗: {exc}"
            ) from exc

        if completed.returncode != 0:
            raise VideoToolError(
                "フレーム抽出に失敗しました: "
                + completed.stderr[-2000:]
            )

        files = sorted(
            Path(output_dir).glob("frame_*.jpg")
        )

        frames: List[VideoFrame] = []

        for index, frame_path in enumerate(files):
            timestamp = start_time + (
                index * max(interval, 0.1)
            )

            frames.append(
                VideoFrame(
                    timestamp=timestamp,
                    path=str(frame_path),
                    index=index,
                )
            )

        return frames

    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
    ) -> str:
        """
        動画から音声をWAVへ抽出。
        """

        self.require()

        os.makedirs(
            os.path.dirname(output_path) or ".",
            exist_ok=True,
        )

        command = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            str(max(0.0, start_time)),
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
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                output_path,
            ]
        )

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        except OSError as exc:
            raise VideoToolError(
                f"FFmpeg起動失敗: {exc}"
            ) from exc

        if completed.returncode != 0:
            raise VideoToolError(
                "音声抽出に失敗しました: "
                + completed.stderr[-2000:]
            )

        return output_path


# ============================================================
# Subtitle Parser
# ============================================================

class SubtitleParser:
    """
    SRT / VTT字幕を解析する。
    """

    TIME_PATTERN = re.compile(
        r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[,.]\d{3})"
        r"\s*-->\s*"
        r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[,.]\d{3})"
    )

    def parse(self, subtitle_path: str) -> List[SubtitleEntry]:
        path = Path(subtitle_path)

        if not path.exists():
            raise SubtitleParseError(
                f"字幕ファイルが存在しません: {subtitle_path}"
            )

        suffix = path.suffix.lower()

        if suffix == ".srt":
            return self.parse_srt(path)

        if suffix == ".vtt":
            return self.parse_vtt(path)

        if suffix in {".txt", ".ass", ".ssa"}:
            return self.parse_generic(path)

        raise SubtitleParseError(
            f"未対応の字幕形式です: {suffix}"
        )

    def parse_srt(self, path: Path) -> List[SubtitleEntry]:
        text = path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

        blocks = re.split(
            r"\n\s*\n",
            text.strip(),
        )

        entries: List[SubtitleEntry] = []

        for index, block in enumerate(blocks, start=1):
            lines = block.splitlines()

            if not lines:
                continue

            match = None

            for line in lines:
                match = self.TIME_PATTERN.search(line)

                if match:
                    break

            if not match:
                continue

            start = _parse_timestamp(
                match.group("start")
            )

            end = _parse_timestamp(
                match.group("end")
            )

            text_lines = []

            time_line_index = lines.index(
                match.group(0)
            ) if match.group(0) in lines else 1

            for line in lines[time_line_index + 1:]:
                line = line.strip()

                if line:
                    text_lines.append(line)

            subtitle_text = _normalize_text(
                "\n".join(text_lines)
            )

            if subtitle_text:
                entries.append(
                    SubtitleEntry(
                        start=start,
                        end=end,
                        text=subtitle_text,
                        index=index,
                    )
                )

        return entries

    def parse_vtt(self, path: Path) -> List[SubtitleEntry]:
        text = path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

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

        entries: List[SubtitleEntry] = []

        for index, block in enumerate(blocks, start=1):
            lines = block.splitlines()

            match = None
            time_line_index = -1

            for i, line in enumerate(lines):
                current = self.TIME_PATTERN.search(line)

                if current:
                    match = current
                    time_line_index = i
                    break

            if not match:
                continue

            start = _parse_timestamp(
                match.group("start")
            )

            end = _parse_timestamp(
                match.group("end")
            )

            subtitle_text = _normalize_text(
                "\n".join(
                    lines[time_line_index + 1:]
                )
            )

            if subtitle_text:
                entries.append(
                    SubtitleEntry(
                        start=start,
                        end=end,
                        text=subtitle_text,
                        index=index,
                    )
                )

        return entries

    def parse_generic(self, path: Path) -> List[SubtitleEntry]:
        """
        TXT/ASS/SSAの簡易処理。

        完全なASS/SSAパーサーではない。
        """

        text = path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

        entries: List[SubtitleEntry] = []

        lines = text.splitlines()

        for index, line in enumerate(lines, start=1):
            line = line.strip()

            if not line:
                continue

            match = self.TIME_PATTERN.search(line)

            if match:
                start = _parse_timestamp(
                    match.group("start")
                )

                end = _parse_timestamp(
                    match.group("end")
                )

                subtitle_text = line[
                    match.end():
                ].strip()

                subtitle_text = re.sub(
                    r"^[\-:>]+",
                    "",
                    subtitle_text,
                ).strip()

                if subtitle_text:
                    entries.append(
                        SubtitleEntry(
                            start=start,
                            end=end,
                            text=subtitle_text,
                            index=index,
                        )
                    )

            else:
                entries.append(
                    SubtitleEntry(
                        start=0.0,
                        end=0.0,
                        text=line,
                        index=index,
                    )
                )

        return entries


# ============================================================
# Timeline Merger
# ============================================================

class TimelineMerger:
    """
    フレーム・字幕などを時間軸で統合する。
    """

    def subtitles_at(
        self,
        timestamp: float,
        subtitles: Sequence[SubtitleEntry],
    ) -> List[SubtitleEntry]:

        result = []

        for subtitle in subtitles:
            if subtitle.start <= timestamp <= subtitle.end:
                result.append(subtitle)

        return result

    def nearest_subtitle(
        self,
        timestamp: float,
        subtitles: Sequence[SubtitleEntry],
        max_distance: float = 5.0,
    ) -> Optional[SubtitleEntry]:

        best = None
        best_distance = float("inf")

        for subtitle in subtitles:

            if subtitle.start <= timestamp <= subtitle.end:
                return subtitle

            distance = min(
                abs(timestamp - subtitle.start),
                abs(timestamp - subtitle.end),
            )

            if distance < best_distance:
                best = subtitle
                best_distance = distance

        if best_distance <= max_distance:
            return best

        return None

    def build(
        self,
        frames: Sequence[VideoFrame],
        subtitles: Sequence[SubtitleEntry],
    ) -> List[TimelineEvent]:

        events: List[TimelineEvent] = []

        for frame in frames:

            current = self.subtitles_at(
                frame.timestamp,
                subtitles,
            )

            subtitle_text = None

            if current:
                subtitle_text = "\n".join(
                    item.text
                    for item in current
                )

            else:
                nearest = self.nearest_subtitle(
                    frame.timestamp,
                    subtitles,
                )

                if nearest:
                    subtitle_text = nearest.text

            events.append(
                TimelineEvent(
                    timestamp=frame.timestamp,
                    subtitle=subtitle_text,
                    frame_path=frame.path,
                )
            )

        return events


# ============================================================
# Knowledge Converter
# ============================================================

class VideoKnowledgeConverter:
    """
    VideoAnalysisResultをKnowledgeManagerへ
    渡しやすい形式へ変換する。
    """

    def convert(
        self,
        result: VideoAnalysisResult,
    ) -> Dict[str, Any]:

        video = result.video

        analysis = result.analysis

        title = (
            analysis.get("title")
            or Path(
                video.get("filename", "video")
            ).stem
        )

        summary = (
            analysis.get("summary")
            or analysis.get("description")
            or ""
        )

        concepts = analysis.get(
            "concepts",
            [],
        )

        keywords = analysis.get(
            "keywords",
            [],
        )

        sections = analysis.get(
            "sections",
            [],
        )

        return {
            "type": "video_knowledge",
            "source_type": "video",
            "title": title,
            "summary": summary,
            "keywords": keywords,
            "concepts": concepts,
            "sections": sections,
            "source": {
                "filename": video.get("filename"),
                "path": video.get("path"),
                "duration": video.get("duration"),
                "sha256": video.get("sha256"),
            },
            "timeline": result.timeline,
            "metadata": {
                "generated_at": result.generated_at,
                "handler": HANDLER_NAME,
            },
        }


# ============================================================
# Video Handler
# ============================================================

class VideoHandler(BaseHandler):
    """
    自作AI用VideoHandler。

    ChatOrchestratorから呼び出されることを想定。

    基本使用:

        handler = VideoHandler()

        result = await handler.handle(
            {
                "video_path": "sample.mp4",
                "instruction": "この動画を要約してください"
            }
        )

    戻り値:
        Dict[str, Any]
    """

    name = HANDLER_NAME

    description = (
        "動画ファイルを解析し、映像・音声・字幕・"
        "タイムライン・AI解析結果を統合するHandler"
    )

    capabilities = [
        "video_metadata",
        "video_frame_extraction",
        "video_audio_extraction",
        "subtitle_parsing",
        "timeline_merging",
        "video_ai_analysis",
        "video_summary",
        "video_knowledge_extraction",
        "video_segment_analysis",
    ]

    def __init__(
        self,
        ffmpeg_manager: Optional[FFmpegManager] = None,
        ai_provider: Optional[VideoAIProvider] = None,
        work_dir: str = DEFAULT_WORK_DIR,
        result_dir: str = DEFAULT_RESULT_DIR,
        frame_dir: str = DEFAULT_FRAME_DIR,
        audio_dir: str = DEFAULT_AUDIO_DIR,
        subtitle_dir: str = DEFAULT_SUBTITLE_DIR,
        max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    ):
        try:
            super().__init__()
        except Exception:
            pass

        self.ffmpeg = (
            ffmpeg_manager
            or FFmpegManager()
        )

        self.ai_provider = ai_provider

        self.work_dir = Path(work_dir)

        self.result_dir = Path(result_dir)

        self.frame_dir = Path(frame_dir)

        self.audio_dir = Path(audio_dir)

        self.subtitle_dir = Path(subtitle_dir)

        self.max_file_size_mb = max_file_size_mb

        self.subtitle_parser = SubtitleParser()

        self.timeline_merger = TimelineMerger()

        self.knowledge_converter = (
            VideoKnowledgeConverter()
        )

        self.work_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.result_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.frame_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.audio_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.subtitle_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ========================================================
    # Public API
    # ========================================================

    async def handle(
        self,
        request: Union[
            VideoAnalysisRequest,
            Dict[str, Any],
        ],
    ) -> Dict[str, Any]:
        """
        ChatOrchestratorから呼び出すメインエントリ。

        DictでもVideoAnalysisRequestでも受け取れる。
        """

        if isinstance(request, dict):
            request = self._request_from_dict(request)

        try:
            result = await self.analyze(request)

            return result.to_dict()

        except Exception as exc:
            logger.exception(
                "VideoHandlerでエラーが発生しました"
            )

            return {
                "success": False,
                "error": str(exc),
                "handler": self.name,
            }

    async def analyze(
        self,
        request: VideoAnalysisRequest,
    ) -> VideoAnalysisResult:
        """
        動画解析本体。
        """

        errors: List[str] = []

        warnings: List[str] = []

        # ----------------------------------------------------
        # 1. Validation
        # ----------------------------------------------------

        video_path = self._validate_video(
            request.video_path
        )

        # ----------------------------------------------------
        # 2. Metadata
        # ----------------------------------------------------

        try:
            metadata = await asyncio.to_thread(
                self._get_video_metadata,
                video_path,
            )

        except Exception as exc:
            errors.append(
                f"動画メタデータ取得失敗: {exc}"
            )

            metadata = VideoMetadata(
                path=str(video_path),
                filename=video_path.name,
                extension=video_path.suffix.lower(),
                mime_type=mimetypes.guess_type(
                    str(video_path)
                )[0],
                size_bytes=video_path.stat().st_size,
            )

        # ----------------------------------------------------
        # 3. Subtitle
        # ----------------------------------------------------

        subtitles: List[SubtitleEntry] = []

        subtitle_path = (
            request.subtitle_path
        )

        if subtitle_path:
            try:
                subtitles = await asyncio.to_thread(
                    self.subtitle_parser.parse,
                    subtitle_path,
                )

            except Exception as exc:
                warnings.append(
                    f"字幕解析失敗: {exc}"
                )

        elif request.analyze_subtitles:
            detected = self._detect_subtitle_file(
                video_path
            )

            if detected:
                try:
                    subtitles = await asyncio.to_thread(
                        self.subtitle_parser.parse,
                        str(detected),
                    )

                except Exception as exc:
                    warnings.append(
                        f"自動検出字幕の解析失敗: {exc}"
                    )

        # ----------------------------------------------------
        # 4. Frame extraction
        # ----------------------------------------------------

        frames: List[VideoFrame] = []

        if request.extract_frames:

            frame_output_dir = (
                self.frame_dir
                / self._make_job_id(video_path)
            )

            try:
                frames = await asyncio.to_thread(
                    self.ffmpeg.extract_frames,
                    str(video_path),
                    str(frame_output_dir),
                    request.start_time or 0.0,
                    request.end_time,
                    request.frame_interval,
                    request.max_frames,
                )

            except Exception as exc:
                warnings.append(
                    f"フレーム抽出失敗: {exc}"
                )

        # ----------------------------------------------------
        # 5. Audio extraction
        # ----------------------------------------------------

        audio_path: Optional[str] = None

        if request.extract_audio:

            audio_output = (
                self.audio_dir
                / f"{self._make_job_id(video_path)}.wav"
            )

            try:
                audio_path = await asyncio.to_thread(
                    self.ffmpeg.extract_audio,
                    str(video_path),
                    str(audio_output),
                    request.start_time or 0.0,
                    request.end_time,
                )

            except Exception as exc:
                warnings.append(
                    f"音声抽出失敗: {exc}"
                )

        # ----------------------------------------------------
        # 6. Timeline
        # ----------------------------------------------------

        timeline = self.timeline_merger.build(
            frames,
            subtitles,
        )

        # ----------------------------------------------------
        # 7. AI analysis
        # ----------------------------------------------------

        analysis: Dict[str, Any] = {}

        if request.use_ai:

            if self.ai_provider is None:

                warnings.append(
                    "AI Providerが設定されていないため、"
                    "AI動画解析をスキップしました。"
                )

            else:

                try:
                    analysis = await self._analyze_with_ai(
                        request=request,
                        metadata=metadata,
                        subtitles=subtitles,
                        frames=frames,
                        timeline=timeline,
                        audio_path=audio_path,
                    )

                except Exception as exc:
                    errors.append(
                        f"AI動画解析失敗: {exc}"
                    )

        # ----------------------------------------------------
        # 8. Knowledge
        # ----------------------------------------------------

        temporary_result = VideoAnalysisResult(
            success=not errors,
            video=metadata.to_dict(),
            request=request.to_dict(),
            frames=[
                frame.to_dict()
                for frame in frames
            ],
            subtitles=[
                subtitle.to_dict()
                for subtitle in subtitles
            ],
            timeline=[
                event.to_dict()
                for event in timeline
            ],
            analysis=analysis,
            errors=errors,
            warnings=warnings,
        )

        knowledge = (
            self.knowledge_converter.convert(
                temporary_result
            )
        )

        temporary_result.knowledge = knowledge

        # ----------------------------------------------------
        # 9. Save
        # ----------------------------------------------------

        if request.save_result:

            try:
                result_path = (
                    Path(request.result_path)
                    if request.result_path
                    else self.result_dir
                    / (
                        self._make_job_id(video_path)
                        + ".json"
                    )
                )

                self._save_json(
                    result_path,
                    temporary_result.to_dict(),
                )

            except Exception as exc:
                warnings.append(
                    f"解析結果保存失敗: {exc}"
                )

        return temporary_result

    # ========================================================
    # Request
    # ========================================================

    def _request_from_dict(
        self,
        data: Dict[str, Any],
    ) -> VideoAnalysisRequest:

        video_path = (
            data.get("video_path")
            or data.get("path")
            or data.get("file")
            or data.get("input")
        )

        if not video_path:
            raise VideoValidationError(
                "video_pathが指定されていません。"
            )

        return VideoAnalysisRequest(
            video_path=str(video_path),
            instruction=str(
                data.get("instruction")
                or data.get("prompt")
                or ""
            ),
            subtitle_path=data.get(
                "subtitle_path"
            ),
            start_time=self._optional_float(
                data.get("start_time")
            ),
            end_time=self._optional_float(
                data.get("end_time")
            ),
            frame_interval=_safe_float(
                data.get(
                    "frame_interval",
                    DEFAULT_FRAME_INTERVAL,
                ),
                DEFAULT_FRAME_INTERVAL,
            ),
            max_frames=_safe_int(
                data.get(
                    "max_frames",
                    DEFAULT_MAX_FRAMES,
                ),
                DEFAULT_MAX_FRAMES,
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
            analyze_subtitles=bool(
                data.get(
                    "analyze_subtitles",
                    True,
                )
            ),
            use_ai=bool(
                data.get(
                    "use_ai",
                    True,
                )
            ),
            provider=data.get(
                "provider"
            ),
            save_result=bool(
                data.get(
                    "save_result",
                    True,
                )
            ),
            result_path=data.get(
                "result_path"
            ),
            language=data.get(
                "language",
                "ja",
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
        )

    @staticmethod
    def _optional_float(
        value: Any,
    ) -> Optional[float]:

        if value is None:
            return None

        try:
            return float(value)

        except (TypeError, ValueError):
            return None

    # ========================================================
    # Validation
    # ========================================================

    def _validate_video(
        self,
        video_path: str,
    ) -> Path:

        path = Path(video_path).expanduser().resolve()

        if not path.exists():
            raise VideoValidationError(
                f"動画ファイルが存在しません: {path}"
            )

        if not path.is_file():
            raise VideoValidationError(
                f"動画ファイルではありません: {path}"
            )

        if path.suffix.lower() not in (
            SUPPORTED_VIDEO_EXTENSIONS
        ):
            raise VideoValidationError(
                "未対応の動画形式です: "
                f"{path.suffix}"
            )

        size_mb = (
            path.stat().st_size
            / (1024 * 1024)
        )

        if size_mb > self.max_file_size_mb:
            raise VideoValidationError(
                f"動画サイズが上限を超えています。"
                f"{size_mb:.2f}MB > "
                f"{self.max_file_size_mb}MB"
            )

        return path

    # ========================================================
    # Metadata
    # ========================================================

    def _get_video_metadata(
        self,
        video_path: Path,
    ) -> VideoMetadata:

        probe = self.ffmpeg.probe(
            str(video_path)
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

            elif (
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

                    fps = (
                        float(numerator)
                        / float(denominator)
                    )

                except Exception:
                    fps = 0.0

        duration = _safe_float(
            format_info.get(
                "duration"
            )
        )

        mime_type = (
            mimetypes.guess_type(
                str(video_path)
            )[0]
        )

        return VideoMetadata(
            path=str(video_path),
            filename=video_path.name,
            extension=video_path.suffix.lower(),
            mime_type=mime_type,
            size_bytes=video_path.stat().st_size,
            duration=duration,
            width=_safe_int(
                video_stream.get("width")
                if video_stream
                else 0
            ),
            height=_safe_int(
                video_stream.get("height")
                if video_stream
                else 0
            ),
            fps=fps,
            video_codec=(
                video_stream.get("codec_name")
                if video_stream
                else None
            ),
            audio_codec=(
                audio_stream.get("codec_name")
                if audio_stream
                else None
            ),
            has_video=video_stream is not None,
            has_audio=audio_stream is not None,
            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
            sha256=awaitable_hash(
                video_path
            ),
        )

    # ========================================================
    # Subtitle
    # ========================================================

    def _detect_subtitle_file(
        self,
        video_path: Path,
    ) -> Optional[Path]:

        candidates = []

        for extension in (
            ".srt",
            ".vtt",
            ".ass",
            ".ssa",
            ".txt",
        ):

            candidate = (
                video_path.with_suffix(
                    extension
                )
            )

            if candidate.exists():
                candidates.append(candidate)

        if candidates:
            return candidates[0]

        return None

    # ========================================================
    # AI
    # ========================================================

    async def _analyze_with_ai(
        self,
        request: VideoAnalysisRequest,
        metadata: VideoMetadata,
        subtitles: Sequence[SubtitleEntry],
        frames: Sequence[VideoFrame],
        timeline: Sequence[TimelineEvent],
        audio_path: Optional[str],
    ) -> Dict[str, Any]:

        prompt = self._build_ai_prompt(
            request=request,
            metadata=metadata,
            subtitles=subtitles,
            timeline=timeline,
        )

        frame_payload = []

        for frame in frames:

            try:
                encoded = await asyncio.to_thread(
                    self._encode_image,
                    frame.path,
                )

                frame_payload.append(
                    {
                        "timestamp": frame.timestamp,
                        "path": frame.path,
                        "image_base64": encoded,
                    }
                )

            except Exception as exc:

                logger.warning(
                    "フレーム読み込み失敗: %s",
                    exc,
                )

        subtitle_payload = [
            subtitle.to_dict()
            for subtitle in subtitles
        ]

        result = await self.ai_provider.analyze_video(
            video_path=str(
                metadata.path
            ),
            prompt=prompt,
            metadata=metadata.to_dict(),
            subtitles=subtitle_payload,
            frames=frame_payload,
        )

        if not isinstance(result, dict):
            result = {
                "summary": str(result)
            }

        return result

    def _build_ai_prompt(
        self,
        request: VideoAnalysisRequest,
        metadata: VideoMetadata,
        subtitles: Sequence[SubtitleEntry],
        timeline: Sequence[TimelineEvent],
    ) -> str:

        subtitle_text = "\n".join(
            (
                f"[{_format_timestamp(item.start)}"
                f" - "
                f"{_format_timestamp(item.end)}] "
                f"{item.text}"
            )
            for item in subtitles[:500]
        )

        instruction = (
            request.instruction.strip()
            or "この動画の内容を詳しく解析してください。"
        )

        return f"""
あなたは動画解析AIです。

以下の動画について解析してください。

ユーザー要求:
{instruction}

動画情報:
- ファイル名: {metadata.filename}
- 長さ: {metadata.duration:.3f}秒
- 解像度: {metadata.width}x{metadata.height}
- FPS: {metadata.fps:.3f}
- 動画Codec: {metadata.video_codec}
- 音声Codec: {metadata.audio_codec}

重要:
映像だけでなく、音声、字幕、画面上の文字、
タイムスタンプを可能な範囲で関連付けてください。

特に以下を区別してください。

1. 実際に動画から確認できる事実
2. 字幕から確認できる情報
3. 音声から確認できる情報
4. 映像から推測した情報
5. AIによる推測

推測を事実として扱わないでください。

字幕:
--------------------
{subtitle_text}
--------------------

可能なら以下のJSON形式で返してください。

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
    "spoken_content": "",
    "subtitle_summary": "",
    "code": [],
    "questions": [],
    "answers": [],
    "confidence": 0.0,
    "uncertainties": []
}}

日本語で回答してください。
""".strip()

    # ========================================================
    # Image
    # ========================================================

    @staticmethod
    def _encode_image(
        path: str,
    ) -> str:

        with open(
            path,
            "rb",
        ) as f:

            data = f.read()

        return base64.b64encode(
            data
        ).decode("ascii")

    # ========================================================
    # Save
    # ========================================================

    @staticmethod
    def _save_json(
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

    # ========================================================
    # Job ID
    # ========================================================

    @staticmethod
    def _make_job_id(
        video_path: Path,
    ) -> str:

        stat = video_path.stat()

        raw = (
            f"{video_path.resolve()}"
            f":{stat.st_size}"
            f":{stat.st_mtime_ns}"
        )

        digest = hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

        return digest[:24]


# ============================================================
# Hash Helper
# ============================================================

def awaitable_hash(
    path: Path,
) -> Optional[str]:

    try:
        return _file_sha256(path)

    except Exception as exc:
        logger.warning(
            "SHA256生成失敗: %s",
            exc,
        )

        return None


# ============================================================
# Simple Local Provider
# ============================================================

class LocalDescriptionProvider:
    """
    テスト用Provider。

    実際のVision AIではない。

    VideoHandlerのパイプラインを確認するために使用する。
    """

    async def analyze_video(
        self,
        video_path: str,
        prompt: str,
        metadata: Dict[str, Any],
        subtitles: Sequence[Dict[str, Any]],
        frames: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:

        return {
            "title": Path(
                video_path
            ).stem,

            "summary": (
                "LocalDescriptionProviderによる"
                "テスト解析結果です。"
            ),

            "description": (
                f"フレーム数: {len(frames)}、"
                f"字幕数: {len(subtitles)}"
            ),

            "keywords": [],

            "concepts": [],

            "important_points": [],

            "sections": [],

            "timeline": [],

            "detected_objects": [],

            "detected_text": [],

            "spoken_content": "",

            "subtitle_summary": (
                "\n".join(
                    item.get("text", "")
                    for item in subtitles[:20]
                )
            ),

            "code": [],

            "questions": [],

            "answers": [],

            "confidence": 0.1,

            "uncertainties": [
                "これはテスト用Providerです。"
                "実際のVision AIによる解析ではありません。"
            ],
        }


# ============================================================
# Factory
# ============================================================

def create_video_handler(
    ai_provider: Optional[
        VideoAIProvider
    ] = None,
    **kwargs,
) -> VideoHandler:
    """
    VideoHandler生成用Factory。

    将来的に設定ファイルからProviderを
    自動選択する場合にも利用できる。
    """

    return VideoHandler(
        ai_provider=ai_provider,
        **kwargs,
    )


# ============================================================
# Intent Helper
# ============================================================

def looks_like_video_request(
    text: str,
) -> bool:
    """
    IntentRouter等から利用できる簡易判定。

    これは最終的なIntent判定ではない。

    KnowledgeManager / IntentRouter側で
    より高度な判定を行うことを推奨。
    """

    if not text:
        return False

    text = text.lower()

    keywords = [
        "動画",
        "ビデオ",
        "video",
        "mp4",
        "mov",
        "mkv",
        "webm",
        "字幕",
        "映像解析",
        "動画解析",
        "動画を解析",
        "動画を見て",
        "動画の内容",
        "動画を要約",
        "動画から",
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


# ============================================================
# Example
# ============================================================

async def example():
    """
    最小使用例。

    実際のAI Providerを接続する前のテスト用。
    """

    provider = LocalDescriptionProvider()

    handler = VideoHandler(
        ai_provider=provider,
    )

    result = await handler.handle(
        {
            "video_path": "sample.mp4",

            "instruction": (
                "この動画の内容を要約し、"
                "重要なポイントを抽出してください。"
            ),

            "frame_interval": 5.0,

            "max_frames": 60,

            "extract_audio": True,

            "extract_frames": True,

            "analyze_subtitles": True,

            "use_ai": True,
        }
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


# ============================================================
# CLI
# ============================================================

def main():

    import argparse

    parser = argparse.ArgumentParser(
        description="VideoHandler CLI"
    )

    parser.add_argument(
        "video",
        help="解析する動画ファイル",
    )

    parser.add_argument(
        "--subtitle",
        default=None,
        help="字幕ファイル",
    )

    parser.add_argument(
        "--instruction",
        default="動画の内容を要約してください。",
        help="AIへの解析指示",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_FRAME_INTERVAL,
        help="フレーム抽出間隔",
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

    args = parser.parse_args()

    provider = None

    if not args.no_ai:
        provider = LocalDescriptionProvider()

    handler = VideoHandler(
        ai_provider=provider,
    )

    request = VideoAnalysisRequest(
        video_path=args.video,
        subtitle_path=args.subtitle,
        instruction=args.instruction,
        frame_interval=args.interval,
        max_frames=args.max_frames,
        use_ai=not args.no_ai,
    )

    result = asyncio.run(
        handler.analyze(request)
    )

    print(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
```

このコードのポイントは、**あえてGeminiのAPIコードを `VideoHandler.py` に直接書いていない**ことです。

あなたの自作AIの場合、これはかなり重要です。

```text
ChatOrchestrator
       ↓
  VideoHandler
       ↓
VideoAIProvider
       ├── GeminiProvider
       ├── OpenAIProvider
       ├── ClaudeProvider
       └── LocalVisionProvider
```

にできます。

つまり、将来Geminiから別のAIに変更しても、`VideoHandler.py` の大部分は変更せずに済みます。

### 今回の `VideoHandler.py` が既に持っている役割

```text
動画
 ↓
[1] ファイル検証
 ↓
[2] ffprobe
 ↓
[3] 動画情報取得
 ↓
[4] 字幕検出
 ↓
[5] SRT/VTT解析
 ↓
[6] フレーム抽出
 ↓
[7] 音声抽出
 ↓
[8] タイムライン統合
 ↓
[9] AI Provider
 ↓
[10] AI解析
 ↓
[11] Knowledge形式へ変換
 ↓
[12] JSON保存
```

なので、次に作るべきものは **`VideoAnalysisService.py`** です。

今の `VideoHandler.py` は「受付・調整役」にして、実際の動画処理をService側へ移すと、あなたがこれまで作ってきた

```text
Handler
 ↓
Service
 ↓
KnowledgeManager
```

という設計にさらに綺麗に合わせられます。

また、今回のコードには **SRT/VTT字幕の時間情報とフレームの時間情報を統合する `TimelineMerger`** を入れてあります。ここが、さっき話していた「字幕付き動画をAIに解析させる」ための土台になります。

次は **`VideoAnalysisService.py` → `GeminiVideoProvider.py` → `OpenAIVideoProvider.py`** の順に作ると、実際のAI動画解析まで接続できます。
