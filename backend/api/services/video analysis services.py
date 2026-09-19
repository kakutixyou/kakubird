# -*- coding: utf-8 -*-
"""
VideoAnalysisService.py

自作AI用 動画解析サービス。

============================================================
役割
============================================================

動画ファイルを受け取り、

    Video
      ↓
    Metadata
      ↓
    Subtitle
      ↓
    Audio
      ↓
    Transcript
      ↓
    Frames
      ↓
    OCR
      ↓
    Scene Detection
      ↓
    Timeline
      ↓
    VideoProvider
      ↓
    Structured JSON

という解析パイプラインを構築する。

============================================================
設計方針
============================================================

1. 動画そのものを一度にメモリへ読み込まない
2. ffprobe / ffmpeg を利用して動画情報を取得
3. 埋め込み字幕と外部字幕の両方に対応
4. 音声文字起こしはオプション
5. OCRはオプション
6. OpenCVによるフレーム抽出
7. 軽量なシーン検出
8. 字幕・音声・OCR・シーンを時系列へ統合
9. VideoProviderへ解析データを渡す
10. LocalLLM / VisionLLM / HybridLLMへ将来拡張可能

============================================================
想定Provider Interface
============================================================

async def analyze(
    *,
    video_path,
    prompt,
    metadata,
    frames,
    subtitles,
    transcript,
    timeline,
    scenes,
) -> Dict[str, Any]

============================================================
依存関係
============================================================

必須:
    Python 3.10+
    ffmpeg
    ffprobe

推奨:
    opencv-python

任意:
    faster-whisper
    openai-whisper
    pytesseract
    pysubs2

============================================================
注意
============================================================

このService自体はLLMを直接実装しない。

LLM処理はVideoProviderへ委譲する。

そのため、

    LocalVideoProvider
    VisionVideoProvider
    HybridVideoProvider

などへ差し替え可能。
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
import uuid

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
)


logger = logging.getLogger(__name__)


# ============================================================
# Protocol
# ============================================================


class VideoProvider(Protocol):
    """
    VideoAnalysisServiceが利用するProviderのインターフェース。

    LocalLLM / VisionLLM / Gemini / Claude / OpenAIなどを
    将来的に接続できるようにする。
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


# ============================================================
# Data Classes
# ============================================================


@dataclass
class VideoAnalysisConfig:
    """
    動画解析設定。
    """

    # --------------------------------------------------------
    # Frame
    # --------------------------------------------------------

    frame_interval: float = 5.0

    max_frames: int = 120

    frame_width: int = 1280

    frame_quality: int = 85

    save_frames: bool = True

    # --------------------------------------------------------
    # Scene
    # --------------------------------------------------------

    enable_scene_detection: bool = True

    scene_threshold: float = 0.35

    max_scenes: int = 200

    # --------------------------------------------------------
    # Subtitle
    # --------------------------------------------------------

    enable_embedded_subtitles: bool = True

    enable_external_subtitles: bool = True

    subtitle_path: Optional[str] = None

    max_subtitles: int = 1000

    # --------------------------------------------------------
    # Audio
    # --------------------------------------------------------

    enable_transcription: bool = False

    transcription_model: str = "small"

    transcription_language: Optional[str] = None

    audio_sample_rate: int = 16000

    # --------------------------------------------------------
    # OCR
    # --------------------------------------------------------

    enable_ocr: bool = False

    ocr_interval: float = 10.0

    ocr_language: str = "jpn+eng"

    # --------------------------------------------------------
    # Timeline
    # --------------------------------------------------------

    timeline_window: float = 2.0

    # --------------------------------------------------------
    # Runtime
    # --------------------------------------------------------

    command_timeout: int = 120

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    output_dir: Optional[str] = None

    keep_temp_files: bool = False


@dataclass
class SubtitleEntry:
    """
    字幕1件。
    """

    start: float

    end: float

    text: str

    language: Optional[str] = None

    source: str = "unknown"

    index: int = 0


@dataclass
class TranscriptEntry:
    """
    音声文字起こし1件。
    """

    start: float

    end: float

    text: str

    confidence: Optional[float] = None

    language: Optional[str] = None

    source: str = "whisper"


@dataclass
class FrameInfo:
    """
    抽出フレーム。
    """

    timestamp: float

    frame_index: int

    path: Optional[str] = None

    width: Optional[int] = None

    height: Optional[int] = None

    ocr_text: str = ""


@dataclass
class SceneInfo:
    """
    シーン。
    """

    start: float

    end: float

    duration: float

    start_frame: Optional[int] = None

    end_frame: Optional[int] = None

    confidence: float = 0.0


# ============================================================
# Main Service
# ============================================================


class VideoAnalysisService:
    """
    自作AI用の動画解析サービス。

    主な入口:

        await service.analyze_video(...)

    """

    def __init__(
        self,
        provider: Optional[VideoProvider] = None,
        *,
        config: Optional[VideoAnalysisConfig] = None,
        transcription_provider: Optional[Any] = None,
        ocr_provider: Optional[Callable[..., str]] = None,
    ):
        self.provider = provider

        self.config = (
            config
            if config is not None
            else VideoAnalysisConfig()
        )

        self.transcription_provider = (
            transcription_provider
        )

        self.ocr_provider = ocr_provider

    # ========================================================
    # Public API
    # ========================================================

    async def analyze_video(
        self,
        video_path: str,
        *,
        prompt: str = "この動画の内容を詳しく解析してください。",
        subtitle_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        動画解析のメイン入口。

        Returns:
            Dict[str, Any]
        """

        video_path = self._validate_video_path(
            video_path
        )

        logger.info(
            "VideoAnalysisService: 動画解析開始: %s",
            video_path,
        )

        work_dir = self._create_work_directory()

        try:

            # ------------------------------------------------
            # 1. Metadata
            # ------------------------------------------------

            metadata = await asyncio.to_thread(
                self._probe_video,
                video_path,
            )

            metadata["filename"] = Path(
                video_path
            ).name

            metadata["analysis_id"] = str(
                uuid.uuid4()
            )

            # ------------------------------------------------
            # 2. Subtitle
            # ------------------------------------------------

            subtitles = await asyncio.to_thread(
                self._extract_subtitles,
                video_path,
                subtitle_path
                or self.config.subtitle_path,
            )

            # ------------------------------------------------
            # 3. Audio / Transcript
            # ------------------------------------------------

            transcript: List[
                Dict[str, Any]
            ] = []

            if self.config.enable_transcription:

                transcript = await asyncio.to_thread(
                    self._transcribe_video,
                    video_path,
                    work_dir,
                )

            # ------------------------------------------------
            # 4. Frames
            # ------------------------------------------------

            frames = await asyncio.to_thread(
                self._extract_frames,
                video_path,
                work_dir,
                metadata,
            )

            # ------------------------------------------------
            # 5. OCR
            # ------------------------------------------------

            if self.config.enable_ocr:

                frames = await asyncio.to_thread(
                    self._run_ocr,
                    frames,
                )

            # ------------------------------------------------
            # 6. Scene detection
            # ------------------------------------------------

            scenes: List[
                Dict[str, Any]
            ] = []

            if self.config.enable_scene_detection:

                scenes = await asyncio.to_thread(
                    self._detect_scenes,
                    video_path,
                    metadata,
                )

            # ------------------------------------------------
            # 7. Timeline
            # ------------------------------------------------

            timeline = self._build_timeline(
                frames=frames,
                subtitles=subtitles,
                transcript=transcript,
                scenes=scenes,
            )

            # ------------------------------------------------
            # 8. Provider
            # ------------------------------------------------

            provider_result: Dict[str, Any] = {}

            if self.provider is not None:

                provider_result = await self.provider.analyze(
                    video_path=video_path,
                    prompt=prompt,
                    metadata=metadata,
                    frames=frames,
                    subtitles=subtitles,
                    transcript=transcript,
                    timeline=timeline,
                    scenes=scenes,
                )

            # ------------------------------------------------
            # 9. Final result
            # ------------------------------------------------

            result = {
                "success": True,

                "analysis_id": metadata[
                    "analysis_id"
                ],

                "metadata": metadata,

                "subtitles": subtitles,

                "transcript": transcript,

                "frames": frames,

                "scenes": scenes,

                "timeline": timeline,

                "llm_analysis": provider_result,

                "errors": [],

            }

            logger.info(
                "VideoAnalysisService: 動画解析完了: %s",
                video_path,
            )

            return result

        except Exception as exc:

            logger.exception(
                "VideoAnalysisService: 動画解析失敗: %s",
                exc,
            )

            return {
                "success": False,

                "analysis_id": None,

                "metadata": {},

                "subtitles": [],

                "transcript": [],

                "frames": [],

                "scenes": [],

                "timeline": [],

                "llm_analysis": {},

                "errors": [
                    str(exc)
                ],
            }

        finally:

            if not self.config.keep_temp_files:

                self._cleanup_directory(
                    work_dir
                )

    # ========================================================
    # Validation
    # ========================================================

    def _validate_video_path(
        self,
        video_path: str,
    ) -> str:
        """
        動画パスを検証する。
        """

        if not video_path:

            raise ValueError(
                "video_pathが指定されていません。"
            )

        path = Path(video_path)

        if not path.exists():

            raise FileNotFoundError(
                f"動画ファイルが存在しません: {video_path}"
            )

        if not path.is_file():

            raise ValueError(
                f"動画パスがファイルではありません: {video_path}"
            )

        return str(
            path.resolve()
        )

    # ========================================================
    # Work Directory
    # ========================================================

    def _create_work_directory(self) -> str:
        """
        動画解析用一時ディレクトリを作る。
        """

        if self.config.output_dir:

            base = Path(
                self.config.output_dir
            )

            base.mkdir(
                parents=True,
                exist_ok=True,
            )

            work_dir = (
                base
                / f"video_analysis_{uuid.uuid4().hex}"
            )

            work_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            return str(work_dir)

        return tempfile.mkdtemp(
            prefix="video_analysis_"
        )

    def _cleanup_directory(
        self,
        directory: str,
    ) -> None:

        try:

            shutil.rmtree(
                directory,
                ignore_errors=True,
            )

        except Exception as exc:

            logger.warning(
                "一時ディレクトリ削除失敗: %s",
                exc,
            )

    # ========================================================
    # FFmpeg
    # ========================================================

    def _check_ffmpeg(self) -> None:
        """
        ffmpeg / ffprobe の存在確認。
        """

        if shutil.which("ffmpeg") is None:

            raise RuntimeError(
                "ffmpegが見つかりません。"
                "PATHへffmpegを追加してください。"
            )

        if shutil.which("ffprobe") is None:

            raise RuntimeError(
                "ffprobeが見つかりません。"
                "PATHへffprobeを追加してください。"
            )

    def _run_command(
        self,
        command: List[str],
        *,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """
        外部コマンド実行。
        """

        logger.debug(
            "Command: %s",
            " ".join(command),
        )

        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=(
                timeout
                or self.config.command_timeout
            ),
            check=False,
        )

    # ========================================================
    # Metadata
    # ========================================================

    def _probe_video(
        self,
        video_path: str,
    ) -> Dict[str, Any]:
        """
        ffprobeで動画メタデータを取得する。
        """

        self._check_ffmpeg()

        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            video_path,
        ]

        result = self._run_command(
            command
        )

        if result.returncode != 0:

            raise RuntimeError(
                f"ffprobe失敗: {result.stderr}"
            )

        try:

            data = json.loads(
                result.stdout
            )

        except json.JSONDecodeError as exc:

            raise RuntimeError(
                f"ffprobe JSON解析失敗: {exc}"
            )

        streams = data.get(
            "streams",
            [],
        )

        format_info = data.get(
            "format",
            {},
        )

        video_stream = next(
            (
                s
                for s in streams
                if s.get("codec_type")
                == "video"
            ),
            None,
        )

        audio_stream = next(
            (
                s
                for s in streams
                if s.get("codec_type")
                == "audio"
            ),
            None,
        )

        subtitle_streams = [
            s
            for s in streams
            if s.get("codec_type")
            == "subtitle"
        ]

        fps = self._parse_fraction(
            (
                video_stream or {}
            ).get(
                "r_frame_rate",
                "0/1",
            )
        )

        duration = self._safe_float(
            (
                format_info
                or {}
            ).get(
                "duration",
                0,
            )
        )

        width = (
            video_stream or {}
        ).get(
            "width"
        )

        height = (
            video_stream or {}
        ).get(
            "height"
        )

        frame_count = (
            (
                video_stream or {}
            ).get(
                "nb_frames"
            )
        )

        if frame_count:

            try:
                frame_count = int(
                    frame_count
                )
            except ValueError:
                frame_count = None

        if frame_count is None and fps > 0:

            frame_count = int(
                duration * fps
            )

        return {
            "duration": duration,

            "fps": fps,

            "frame_count": frame_count,

            "width": width,

            "height": height,

            "resolution": (
                f"{width}x{height}"
                if width and height
                else None
            ),

            "video_codec": (
                video_stream or {}
            ).get(
                "codec_name"
            ),

            "audio_codec": (
                audio_stream or {}
            ).get(
                "codec_name"
            ),

            "format": format_info.get(
                "format_name"
            ),

            "size": self._safe_int(
                format_info.get(
                    "size"
                )
            ),

            "has_video": (
                video_stream
                is not None
            ),

            "has_audio": (
                audio_stream
                is not None
            ),

            "subtitle_streams": len(
                subtitle_streams
            ),

            "streams": [
                {
                    "index": s.get(
                        "index"
                    ),
                    "codec_type": s.get(
                        "codec_type"
                    ),
                    "codec_name": s.get(
                        "codec_name"
                    ),
                    "language": (
                        s.get(
                            "tags",
                            {}
                        )
                        .get(
                            "language"
                        )
                    ),
                    "title": (
                        s.get(
                            "tags",
                            {}
                        )
                        .get(
                            "title"
                        )
                    ),
                }
                for s in streams
            ],
        }

    # ========================================================
    # Subtitle
    # ========================================================

    def _extract_subtitles(
        self,
        video_path: str,
        external_subtitle_path: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        埋め込み字幕 + 外部字幕を取得。
        """

        subtitles: List[
            SubtitleEntry
        ] = []

        # ----------------------------------------------------
        # External
        # ----------------------------------------------------

        if (
            external_subtitle_path
            and os.path.exists(
                external_subtitle_path
            )
        ):

            try:

                subtitles.extend(
                    self._parse_subtitle_file(
                        external_subtitle_path,
                        source="external",
                    )
                )

            except Exception as exc:

                logger.warning(
                    "外部字幕解析失敗: %s",
                    exc,
                )

        # ----------------------------------------------------
        # Embedded
        # ----------------------------------------------------

        if self.config.enable_embedded_subtitles:

            try:

                subtitles.extend(
                    self._extract_embedded_subtitles(
                        video_path
                    )
                )

            except Exception as exc:

                logger.warning(
                    "埋め込み字幕抽出失敗: %s",
                    exc,
                )

        # ----------------------------------------------------
        # Sort
        # ----------------------------------------------------

        subtitles.sort(
            key=lambda x: (
                x.start,
                x.end,
            )
        )

        subtitles = subtitles[
            : self.config.max_subtitles
        ]

        return [
            asdict(item)
            for item in subtitles
        ]

    def _extract_embedded_subtitles(
        self,
        video_path: str,
    ) -> List[SubtitleEntry]:
        """
        ffprobeで字幕ストリームを調べ、
        ffmpegでSRTとして抽出する。
        """

        self._check_ffmpeg()

        probe_command = [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            video_path,
        ]

        probe = self._run_command(
            probe_command
        )

        if probe.returncode != 0:

            return []

        data = json.loads(
            probe.stdout
        )

        streams = [
            s
            for s in data.get(
                "streams",
                [],
            )
            if s.get(
                "codec_type"
            ) == "subtitle"
        ]

        results: List[
            SubtitleEntry
        ] = []

        for stream in streams:

            stream_index = stream.get(
                "index"
            )

            language = (
                stream.get(
                    "tags",
                    {}
                )
                .get(
                    "language"
                )
            )

            command = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-map",
                f"0:{stream_index}",
                "-f",
                "srt",
                "-",
            ]

            result = self._run_command(
                command
            )

            if result.returncode != 0:

                logger.warning(
                    "字幕ストリーム%d抽出失敗: %s",
                    stream_index,
                    result.stderr,
                )

                continue

            parsed = self._parse_srt_text(
                result.stdout,
                language=language,
                source="embedded",
            )

            results.extend(
                parsed
            )

        return results

    # ========================================================
    # Subtitle Parsing
    # ========================================================

    def _parse_subtitle_file(
        self,
        path: str,
        *,
        source: str,
    ) -> List[SubtitleEntry]:
        """
        SRT / VTT / ASS / SSAを簡易解析。
        """

        suffix = (
            Path(path)
            .suffix
            .lower()
        )

        with open(
            path,
            "r",
            encoding="utf-8-sig",
            errors="replace",
        ) as f:

            text = f.read()

        if suffix == ".srt":

            return self._parse_srt_text(
                text,
                source=source,
            )

        if suffix == ".vtt":

            return self._parse_vtt_text(
                text,
                source=source,
            )

        if suffix in {
            ".ass",
            ".ssa",
        }:

            return self._parse_ass_text(
                text,
                source=source,
            )

        logger.warning(
            "未対応字幕形式: %s",
            suffix,
        )

        return []

    def _parse_srt_text(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        source: str = "srt",
    ) -> List[SubtitleEntry]:

        entries: List[
            SubtitleEntry
        ] = []

        blocks = re.split(
            r"\n\s*\n",
            text.strip(),
        )

        index = 0

        for block in blocks:

            lines = [
                line.strip()
                for line in block.splitlines()
                if line.strip()
            ]

            if len(lines) < 2:
                continue

            timestamp_line = next(
                (
                    line
                    for line in lines
                    if "-->" in line
                ),
                None,
            )

            if not timestamp_line:
                continue

            start_end = timestamp_line.split(
                "-->",
                1,
            )

            if len(start_end) != 2:
                continue

            start = self._parse_timestamp(
                start_end[0].strip()
            )

            end = self._parse_timestamp(
                start_end[1].strip()
            )

            if start is None or end is None:
                continue

            timestamp_index = lines.index(
                timestamp_line
            )

            content = lines[
                timestamp_index + 1:
            ]

            subtitle_text = self._clean_subtitle_text(
                " ".join(content)
            )

            if not subtitle_text:
                continue

            index += 1

            entries.append(
                SubtitleEntry(
                    start=start,
                    end=end,
                    text=subtitle_text,
                    language=language,
                    source=source,
                    index=index,
                )
            )

        return entries

    def _parse_vtt_text(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        source: str = "vtt",
    ) -> List[SubtitleEntry]:

        # VTTは基本的にSRTと似ている
        text = re.sub(
            r"^WEBVTT.*?\n",
            "",
            text,
            flags=re.DOTALL,
        )

        return self._parse_srt_text(
            text,
            language=language,
            source=source,
        )

    def _parse_ass_text(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        source: str = "ass",
    ) -> List[SubtitleEntry]:

        entries: List[
            SubtitleEntry
        ] = []

        in_events = False

        index = 0

        for line in text.splitlines():

            line = line.strip()

            if line.lower() == "[events]":

                in_events = True
                continue

            if (
                line.startswith("[")
                and line.endswith("]")
            ):

                in_events = False
                continue

            if not in_events:
                continue

            if not line.startswith(
                "Dialogue:",
            ):
                continue

            payload = line[
                len("Dialogue:"):
            ].strip()

            parts = payload.split(
                ",",
                9,
            )

            if len(parts) < 10:
                continue

            start = self._parse_ass_timestamp(
                parts[1]
            )

            end = self._parse_ass_timestamp(
                parts[2]
            )

            if start is None or end is None:
                continue

            subtitle_text = parts[9]

            subtitle_text = re.sub(
                r"\{.*?\}",
                "",
                subtitle_text,
            )

            subtitle_text = (
                subtitle_text
                .replace(
                    r"\N",
                    " ",
                )
                .replace(
                    r"\n",
                    " ",
                )
            )

            subtitle_text = self._clean_subtitle_text(
                subtitle_text
            )

            if not subtitle_text:
                continue

            index += 1

            entries.append(
                SubtitleEntry(
                    start=start,
                    end=end,
                    text=subtitle_text,
                    language=language,
                    source=source,
                    index=index,
                )
            )

        return entries

    def _clean_subtitle_text(
        self,
        text: str,
    ) -> str:

        text = re.sub(
            r"<[^>]+>",
            "",
            text,
        )

        text = re.sub(
            r"\{.*?\}",
            "",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ========================================================
    # Frame Extraction
    # ========================================================

    def _extract_frames(
        self,
        video_path: str,
        work_dir: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        OpenCVを利用して一定間隔でフレームを抽出する。
        """

        try:

            import cv2

        except ImportError:

            logger.warning(
                "opencv-pythonがインストールされていません。"
            )

            return []

        if not metadata.get(
            "has_video",
            False,
        ):

            return []

        frames_dir = Path(
            work_dir
        ) / "frames"

        frames_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        capture = cv2.VideoCapture(
            video_path
        )

        if not capture.isOpened():

            logger.warning(
                "VideoCaptureを開けません: %s",
                video_path,
            )

            return []

        fps = float(
            metadata.get(
                "fps",
                0,
            )
            or 0
        )

        frame_count = int(
            metadata.get(
                "frame_count",
                0,
            )
            or 0
        )

        duration = float(
            metadata.get(
                "duration",
                0,
            )
            or 0
        )

        interval = max(
            0.1,
            self.config.frame_interval,
        )

        max_frames = max(
            1,
            self.config.max_frames,
        )

        frames: List[
            Dict[str, Any]
        ] = []

        timestamp = 0.0

        index = 0

        try:

            while (
                timestamp <= duration
                and len(frames) < max_frames
            ):

                capture.set(
                    cv2.CAP_PROP_POS_MSEC,
                    timestamp * 1000,
                )

                success, frame = (
                    capture.read()
                )

                if not success:

                    break

                actual_frame_index = int(
                    capture.get(
                        cv2.CAP_PROP_POS_FRAMES
                    )
                    or 0
                )

                height, width = (
                    frame.shape[:2]
                )

                output_path = None

                if self.config.save_frames:

                    filename = (
                        f"frame_{index:06d}.jpg"
                    )

                    output_path = (
                        frames_dir
                        / filename
                    )

                    target_width = (
                        self.config.frame_width
                    )

                    if (
                        target_width > 0
                        and width > target_width
                    ):

                        scale = (
                            target_width
                            / width
                        )

                        new_width = target_width

                        new_height = int(
                            height * scale
                        )

                        frame = cv2.resize(
                            frame,
                            (
                                new_width,
                                new_height,
                            ),
                            interpolation=cv2.INTER_AREA,
                        )

                    cv2.imwrite(
                        str(output_path),
                        frame,
                        [
                            cv2.IMWRITE_JPEG_QUALITY,
                            self.config.frame_quality,
                        ],
                    )

                frames.append(
                    asdict(
                        FrameInfo(
                            timestamp=timestamp,
                            frame_index=(
                                actual_frame_index
                            ),
                            path=(
                                str(output_path)
                                if output_path
                                else None
                            ),
                            width=width,
                            height=height,
                        )
                    )
                )

                index += 1

                timestamp += interval

                # frame_countが使える場合の安全策
                if (
                    frame_count > 0
                    and actual_frame_index
                    >= frame_count
                ):

                    break

        finally:

            capture.release()

        return frames

    # ========================================================
    # OCR
    # ========================================================

    def _run_ocr(
        self,
        frames: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        フレームへOCRを実行する。

        ocr_providerが指定されていればそれを使用。

        指定されていなければpytesseractを試す。
        """

        if not frames:
            return frames

        if self.ocr_provider is not None:

            for frame in frames:

                try:

                    text = self.ocr_provider(
                        frame.get(
                            "path"
                        )
                    )

                    frame["ocr_text"] = (
                        text or ""
                    )

                except Exception as exc:

                    logger.warning(
                        "OCR provider失敗: %s",
                        exc,
                    )

            return frames

        try:

            import pytesseract

        except ImportError:

            logger.warning(
                "pytesseractがインストールされていません。"
            )

            return frames

        last_ocr_time = -math.inf

        for frame in frames:

            timestamp = float(
                frame.get(
                    "timestamp",
                    0,
                )
            )

            if (
                timestamp - last_ocr_time
                < self.config.ocr_interval
            ):
                continue

            image_path = frame.get(
                "path"
            )

            if not image_path:
                continue

            try:

                text = pytesseract.image_to_string(
                    image_path,
                    lang=self.config.ocr_language,
                )

                frame["ocr_text"] = (
                    text.strip()
                )

                last_ocr_time = timestamp

            except Exception as exc:

                logger.warning(
                    "OCR失敗 timestamp=%s: %s",
                    timestamp,
                    exc,
                )

        return frames

    # ========================================================
    # Audio / Transcription
    # ========================================================

    def _transcribe_video(
        self,
        video_path: str,
        work_dir: str,
    ) -> List[Dict[str, Any]]:
        """
        動画から音声を抽出して文字起こし。

        優先:
            1. 外部transcription_provider
            2. faster-whisper
            3. whisper

        """

        if self.transcription_provider is not None:

            try:

                result = (
                    self.transcription_provider
                    .transcribe(
                        video_path
                    )
                )

                return self._normalize_transcript(
                    result
                )

            except Exception as exc:

                logger.exception(
                    "外部TranscriptionProvider失敗: %s",
                    exc,
                )

        audio_path = self._extract_audio(
            video_path,
            work_dir,
        )

        if not audio_path:

            return []

        # ----------------------------------------------------
        # faster-whisper
        # ----------------------------------------------------

        try:

            from faster_whisper import (
                WhisperModel,
            )

            logger.info(
                "faster-whisperで文字起こし開始"
            )

            model = WhisperModel(
                self.config.transcription_model
            )

            segments, info = (
                model.transcribe(
                    audio_path,
                    language=(
                        self.config
                        .transcription_language
                    ),
                )
            )

            result = []

            for segment in segments:

                result.append(
                    asdict(
                        TranscriptEntry(
                            start=float(
                                segment.start
                            ),
                            end=float(
                                segment.end
                            ),
                            text=(
                                segment.text
                                or ""
                            ).strip(),
                            confidence=None,
                            language=getattr(
                                info,
                                "language",
                                None,
                            ),
                            source="faster-whisper",
                        )
                    )
                )

            return result

        except ImportError:
            pass

        except Exception as exc:

            logger.warning(
                "faster-whisper失敗: %s",
                exc,
            )

        # ----------------------------------------------------
        # openai-whisper
        # ----------------------------------------------------

        try:

            import whisper

            logger.info(
                "openai-whisperで文字起こし開始"
            )

            model = whisper.load_model(
                self.config.transcription_model
            )

            result = model.transcribe(
                audio_path,
                language=(
                    self.config
                    .transcription_language
                ),
            )

            segments = result.get(
                "segments",
                [],
            )

            return [
                asdict(
                    TranscriptEntry(
                        start=float(
                            segment.get(
                                "start",
                                0,
                            )
                        ),
                        end=float(
                            segment.get(
                                "end",
                                0,
                            )
                        ),
                        text=(
                            segment.get(
                                "text",
                                "",
                            )
                            .strip()
                        ),
                        confidence=None,
                        language=result.get(
                            "language"
                        ),
                        source="whisper",
                    )
                )
                for segment in segments
            ]

        except ImportError:

            logger.warning(
                "Whisperがインストールされていません。"
            )

        except Exception as exc:

            logger.warning(
                "Whisper文字起こし失敗: %s",
                exc,
            )

        return []

    def _extract_audio(
        self,
        video_path: str,
        work_dir: str,
    ) -> Optional[str]:
        """
        ffmpegで音声をWAV化する。
        """

        self._check_ffmpeg()

        output = (
            Path(work_dir)
            / "audio.wav"
        )

        command = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(
                self.config.audio_sample_rate
            ),
            "-c:a",
            "pcm_s16le",
            str(output),
        ]

        result = self._run_command(
            command,
            timeout=max(
                self.config.command_timeout,
                300,
            ),
        )

        if result.returncode != 0:

            logger.warning(
                "音声抽出失敗: %s",
                result.stderr,
            )

            return None

        return str(output)

    def _normalize_transcript(
        self,
        result: Any,
    ) -> List[Dict[str, Any]]:
        """
        外部文字起こしProviderの形式を統一。
        """

        if result is None:
            return []

        if isinstance(
            result,
            dict,
        ):

            segments = result.get(
                "segments",
                [],
            )

        elif isinstance(
            result,
            list,
        ):

            segments = result

        else:

            return []

        normalized = []

        for segment in segments:

            if not isinstance(
                segment,
                dict,
            ):
                continue

            normalized.append(
                asdict(
                    TranscriptEntry(
                        start=self._safe_float(
                            segment.get(
                                "start",
                                0,
                            )
                        ),
                        end=self._safe_float(
                            segment.get(
                                "end",
                                0,
                            )
                        ),
                        text=str(
                            segment.get(
                                "text",
                                "",
                            )
                        ).strip(),
                        confidence=(
                            segment.get(
                                "confidence"
                            )
                        ),
                        language=(
                            segment.get(
                                "language"
                            )
                        ),
                        source=str(
                            segment.get(
                                "source",
                                "external",
                            )
                        ),
                    )
                )
            )

        return normalized

    # ========================================================
    # Scene Detection
    # ========================================================

    def _detect_scenes(
        self,
        video_path: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        OpenCVによる簡易シーン検出。

        フレーム間のヒストグラム差分を利用する。

        専用Scene Detectionライブラリほど高度ではないが、
        追加依存を抑えられる。
        """

        try:

            import cv2

        except ImportError:

            logger.warning(
                "opencv-pythonがないためScene Detectionをスキップ"
            )

            return []

        capture = cv2.VideoCapture(
            video_path
        )

        if not capture.isOpened():

            return []

        fps = float(
            metadata.get(
                "fps",
                0,
            )
            or 0
        )

        duration = float(
            metadata.get(
                "duration",
                0,
            )
            or 0
        )

        sample_interval = max(
            0.5,
            self.config.frame_interval,
        )

        scenes: List[
            SceneInfo
        ] = []

        previous_hist = None

        scene_start = 0.0

        current_timestamp = 0.0

        frame_index = 0

        try:

            while (
                current_timestamp
                <= duration
            ):

                capture.set(
                    cv2.CAP_PROP_POS_MSEC,
                    current_timestamp * 1000,
                )

                success, frame = (
                    capture.read()
                )

                if not success:
                    break

                gray = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2GRAY,
                )

                hist = cv2.calcHist(
                    [gray],
                    [0],
                    None,
                    [64],
                    [0, 256],
                )

                cv2.normalize(
                    hist,
                    hist,
                )

                if previous_hist is not None:

                    difference = cv2.compareHist(
                        previous_hist,
                        hist,
                        cv2.HISTCMP_BHATTACHARYYA,
                    )

                    if (
                        difference
                        >= self.config.scene_threshold
                    ):

                        scene_end = (
                            current_timestamp
                        )

                        scenes.append(
                            SceneInfo(
                                start=scene_start,
                                end=scene_end,
                                duration=(
                                    scene_end
                                    - scene_start
                                ),
                                confidence=min(
                                    1.0,
                                    float(
                                        difference
                                    ),
                                ),
                            )
                        )

                        scene_start = (
                            current_timestamp
                        )

                        if (
                            len(scenes)
                            >= self.config.max_scenes
                        ):
                            break

                previous_hist = hist

                current_timestamp += (
                    sample_interval
                )

                frame_index += 1

            # 最後のシーン
            if (
                duration >= scene_start
                and len(scenes)
                < self.config.max_scenes
            ):

                scenes.append(
                    SceneInfo(
                        start=scene_start,
                        end=duration,
                        duration=(
                            duration
                            - scene_start
                        ),
                        confidence=1.0,
                    )
                )

        finally:

            capture.release()

        return [
            asdict(scene)
            for scene in scenes
        ]

    # ========================================================
    # Timeline
    # ========================================================

    def _build_timeline(
        self,
        *,
        frames: Sequence[Dict[str, Any]],
        subtitles: Sequence[Dict[str, Any]],
        transcript: Sequence[Dict[str, Any]],
        scenes: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        字幕・音声・OCR・フレーム・シーンを
        時系列へ統合する。
        """

        timestamps = set()

        # ----------------------------------------------------
        # Frame timestamps
        # ----------------------------------------------------

        for frame in frames:

            timestamps.add(
                round(
                    self._safe_float(
                        frame.get(
                            "timestamp",
                            0,
                        )
                    ),
                    2,
                )
            )

        # ----------------------------------------------------
        # Subtitle timestamps
        # ----------------------------------------------------

        for subtitle in subtitles:

            timestamps.add(
                round(
                    self._safe_float(
                        subtitle.get(
                            "start",
                            0,
                        )
                    ),
                    2,
                )
            )

        # ----------------------------------------------------
        # Transcript timestamps
        # ----------------------------------------------------

        for segment in transcript:

            timestamps.add(
                round(
                    self._safe_float(
                        segment.get(
                            "start",
                            0,
                        )
                    ),
                    2,
                )
            )

        # ----------------------------------------------------
        # Scene timestamps
        # ----------------------------------------------------

        for scene in scenes:

            timestamps.add(
                round(
                    self._safe_float(
                        scene.get(
                            "start",
                            0,
                        )
                    ),
                    2,
                )
            )

        timeline = []

        for timestamp in sorted(
            timestamps
        ):

            active_subtitles = [
                s
                for s in subtitles
                if (
                    self._safe_float(
                        s.get(
                            "start",
                            0,
                        )
                    )
                    <= timestamp
                    <=
                    self._safe_float(
                        s.get(
                            "end",
                            0,
                        )
                    )
                )
            ]

            active_transcript = [
                t
                for t in transcript
                if (
                    self._safe_float(
                        t.get(
                            "start",
                            0,
                        )
                    )
                    <= timestamp
                    <=
                    self._safe_float(
                        t.get(
                            "end",
                            0,
                        )
                    )
                )
            ]

            active_scene = next(
                (
                    s
                    for s in scenes
                    if (
                        self._safe_float(
                            s.get(
                                "start",
                                0,
                            )
                        )
                        <= timestamp
                        <=
                        self._safe_float(
                            s.get(
                                "end",
                                0,
                            )
                        )
                    )
                ),
                None,
            )

            nearest_frame = self._nearest_frame(
                frames,
                timestamp,
            )

            item = {
                "timestamp": timestamp,

                "subtitle": [
                    {
                        "text": s.get(
                            "text",
                            "",
                        ),
                        "start": s.get(
                            "start"
                        ),
                        "end": s.get(
                            "end"
                        ),
                        "source": s.get(
                            "source"
                        ),
                    }
                    for s in active_subtitles
                ],

                "transcript": [
                    {
                        "text": t.get(
                            "text",
                            "",
                        ),
                        "start": t.get(
                            "start"
                        ),
                        "end": t.get(
                            "end"
                        ),
                        "confidence": t.get(
                            "confidence"
                        ),
                    }
                    for t in active_transcript
                ],

                "ocr": (
                    nearest_frame.get(
                        "ocr_text",
                        "",
                    )
                    if nearest_frame
                    else ""
                ),

                "frame": (
                    {
                        "timestamp": nearest_frame.get(
                            "timestamp"
                        ),
                        "path": nearest_frame.get(
                            "path"
                        ),
                    }
                    if nearest_frame
                    else None
                ),

                "scene": active_scene,
            }

            timeline.append(
                item
            )

        return timeline

    def _nearest_frame(
        self,
        frames: Sequence[Dict[str, Any]],
        timestamp: float,
    ) -> Optional[Dict[str, Any]]:

        if not frames:
            return None

        return min(
            frames,
            key=lambda frame: abs(
                self._safe_float(
                    frame.get(
                        "timestamp",
                        0,
                    )
                )
                - timestamp
            ),
        )

    # ========================================================
    # Utility
    # ========================================================

    @staticmethod
    def _parse_fraction(
        value: Any,
    ) -> float:

        if not value:
            return 0.0

        try:

            if isinstance(
                value,
                str,
            ) and "/" in value:

                numerator, denominator = (
                    value.split(
                        "/",
                        1,
                    )
                )

                denominator = float(
                    denominator
                )

                if denominator == 0:
                    return 0.0

                return (
                    float(numerator)
                    / denominator
                )

            return float(value)

        except (
            TypeError,
            ValueError,
            ZeroDivisionError,
        ):

            return 0.0

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
        default: Optional[int] = None,
    ) -> Optional[int]:

        try:

            return int(value)

        except (
            TypeError,
            ValueError,
        ):

            return default

    @staticmethod
    def _parse_timestamp(
        value: str,
    ) -> Optional[float]:
        """
        SRT/VTT timestamp:

            HH:MM:SS,mmm
            HH:MM:SS.mmm
            MM:SS.mmm
        """

        value = value.strip()

        value = value.split(
            " ",
            1,
        )[0]

        value = value.replace(
            ",",
            ".",
        )

        parts = value.split(":")

        try:

            if len(parts) == 3:

                hours = float(
                    parts[0]
                )

                minutes = float(
                    parts[1]
                )

                seconds = float(
                    parts[2]
                )

                return (
                    hours * 3600
                    + minutes * 60
                    + seconds
                )

            if len(parts) == 2:

                minutes = float(
                    parts[0]
                )

                seconds = float(
                    parts[1]
                )

                return (
                    minutes * 60
                    + seconds
                )

        except ValueError:

            return None

        return None

    @staticmethod
    def _parse_ass_timestamp(
        value: str,
    ) -> Optional[float]:
        """
        ASS:

            H:MM:SS.cc
        """

        value = value.strip()

        parts = value.split(":")

        if len(parts) != 3:
            return None

        try:

            hours = float(
                parts[0]
            )

            minutes = float(
                parts[1]
            )

            seconds = float(
                parts[2]
            )

            return (
                hours * 3600
                + minutes * 60
                + seconds
            )

        except ValueError:

            return None


# ============================================================
# Convenience Function
# ============================================================


async def analyze_video(
    video_path: str,
    *,
    provider: Optional[VideoProvider] = None,
    prompt: str = "この動画の内容を詳しく解析してください。",
    config: Optional[VideoAnalysisConfig] = None,
    subtitle_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    簡易API。

    例:

        result = await analyze_video(
            "sample.mp4",
            provider=local_video_provider,
        )
    """

    service = VideoAnalysisService(
        provider=provider,
        config=config,
    )

    return await service.analyze_video(
        video_path,
        prompt=prompt,
        subtitle_path=subtitle_path,
    )
