# -*- coding: utf-8 -*-
"""
LocalVideoProvider.py

LocalLLMEngine を利用して動画解析を行う VideoProvider。

役割:
    VideoAnalysisService
        ↓
    LocalVideoProvider
        ↓
    LocalLLMEngine
        ↓
    構造化JSON

特徴:
    - 字幕・音声文字起こし・OCR・シーン情報を統合
    - 長大な入力をある程度制限
    - JSON抽出を強化
    - JSONスキーマを簡易検証
    - LLMエラー時のリトライ
    - 非同期APIから安全に同期LLMを呼び出す
    - 解析対象とLLMが実際に参照した情報を区別
    - タイムライン情報を維持
"""

import asyncio
import json
import logging
import re
from typing import (
    Dict,
    Any,
    Sequence,
    Optional,
    List,
    Tuple,
)

from api.services.llm.LocalLLMEngine import LocalLLMEngine
from api.services.llm.GenerationResult import GenerationResult


logger = logging.getLogger(__name__)


class LocalVideoProvider:
    """
    LocalLLMEngine を利用する動画解析Provider。

    注意:
        現在の LocalLLMEngine がテキストベースの場合、
        このProvider自身が動画そのものを直接「視覚認識」するわけではありません。

        VideoAnalysisService が事前に抽出した、

            ・動画メタデータ
            ・字幕
            ・音声文字起こし
            ・OCR
            ・シーン
            ・タイムライン

        をLLMへ渡して解析します。

    将来的にVision対応LLMを接続する場合も、
    このProviderを拡張することで対応できます。
    """

    # ---------------------------------------------------------
    # 設定
    # ---------------------------------------------------------

    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_REPEAT_PENALTY = 1.1

    MAX_PROMPT_CHARS = 50000

    MAX_SUBTITLES = 500
    MAX_TRANSCRIPT_SEGMENTS = 500
    MAX_SCENES = 200
    MAX_FRAMES = 100
    MAX_TIMELINE_ITEMS = 500

    MAX_RETRIES = 2

    # ---------------------------------------------------------
    # 初期化
    # ---------------------------------------------------------

    def __init__(
        self,
        llm_engine: LocalLLMEngine,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        repeat_penalty: float = DEFAULT_REPEAT_PENALTY,
        max_retries: int = MAX_RETRIES,
        max_prompt_chars: int = MAX_PROMPT_CHARS,
    ):
        self.llm_engine = llm_engine

        self.max_tokens = max_tokens
        self.temperature = temperature
        self.repeat_penalty = repeat_penalty
        self.max_retries = max(0, max_retries)
        self.max_prompt_chars = max(1000, max_prompt_chars)

    # =========================================================
    # Public API
    # =========================================================

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
        """
        VideoAnalysisService から呼び出されるメイン処理。

        処理:

            1. 入力データ整理
            2. LLM用コンテキスト生成
            3. システムプロンプト生成
            4. LocalLLMEngine実行
            5. JSON抽出
            6. JSON検証
            7. メタ情報を補完
            8. 結果返却
        """

        filename = metadata.get("filename", "video")

        logger.info(
            "LocalVideoProvider: '%s' の解析を開始します。",
            filename,
        )

        try:
            context = self._build_context(
                metadata=metadata,
                frames=frames,
                subtitles=subtitles,
                transcript=transcript,
                timeline=timeline,
                scenes=scenes,
            )

            final_prompt = self._build_prompt(
                user_prompt=prompt,
                context=context,
            )

            messages = self._build_messages(
                final_prompt=final_prompt,
            )

            result = await self._run_llm_with_retry(
                messages=messages,
            )

            if result is None:
                return self._build_fallback_result(
                    "LocalLLMから有効な応答を取得できませんでした。",
                )

            text = getattr(result, "text", "") or ""

            if not text.strip():

                error_message = getattr(
                    result,
                    "error",
                    "LLMが空の応答を返しました。",
                )

                return self._build_fallback_result(
                    str(error_message),
                )

            parsed = self._parse_llm_json(text)

            if parsed is None:

                return self._build_fallback_result(
                    "LLMが正しいJSONを返しませんでした。",
                    raw_text=text,
                )

            parsed = self._normalize_result(
                parsed,
                metadata=metadata,
                subtitles=subtitles,
                transcript=transcript,
                timeline=timeline,
                scenes=scenes,
            )

            logger.info(
                "LocalVideoProvider: '%s' の解析が完了しました。",
                filename,
            )

            return parsed

        except Exception as exc:

            logger.exception(
                "LocalVideoProviderで予期しないエラーが発生しました: %s",
                exc,
            )

            return self._build_fallback_result(
                f"動画解析中に予期しないエラーが発生しました: {exc}",
            )

    # =========================================================
    # LLM
    # =========================================================

    async def _run_llm_with_retry(
        self,
        *,
        messages: List[Dict[str, str]],
    ) -> Optional[GenerationResult]:
        """
        LocalLLMEngineをリトライ付きで実行する。
        """

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):

            try:

                logger.debug(
                    "LocalLLM推論開始 attempt=%s/%s",
                    attempt + 1,
                    self.max_retries + 1,
                )

                result: GenerationResult = await asyncio.to_thread(
                    self.llm_engine.chat,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    repeat_penalty=self.repeat_penalty,
                )

                if result is not None:

                    text = getattr(result, "text", "") or ""

                    if text.strip():
                        return result

                    logger.warning(
                        "LocalLLMが空レスポンスを返しました。attempt=%s",
                        attempt + 1,
                    )

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "LocalLLM推論失敗 attempt=%s: %s",
                    attempt + 1,
                    exc,
                )

            if attempt < self.max_retries:

                await asyncio.sleep(
                    min(2 ** attempt, 5)
                )

        if last_error:

            logger.error(
                "LocalLLM推論が全て失敗しました: %s",
                last_error,
            )

        return None

    # =========================================================
    # Prompt
    # =========================================================

    def _build_messages(
        self,
        *,
        final_prompt: str,
    ) -> List[Dict[str, str]]:
        """
        Chat形式のmessagesを作成する。
        """

        system_prompt = """
あなたは動画解析専用のAIです。

あなたの仕事は、与えられた動画解析データを根拠として、
動画の内容を構造化JSONに整理することです。

重要なルール:

1. 推測で事実を作らない。
2. 与えられていない映像内容を見たことにしない。
3. 字幕と音声文字起こしを区別する。
4. OCR文字列と発話内容を区別する。
5. 時刻情報がある場合は可能な限り維持する。
6. 不明な内容は null または uncertainties に入れる。
7. 必ずJSON Objectを返す。
8. Markdownのコードブロックで囲まない。
9. JSON以外の説明文を書かない。
10. 同じ内容を不必要に繰り返さない。

特に重要:

このLLMが直接動画フレームを見ているとは限りません。

frame情報がファイルパスだけの場合、
その画像の内容を推測してはいけません。

OCR、字幕、音声文字起こし、シーン情報など、
実際に提供された情報だけを根拠にしてください。
"""

        return [
            {
                "role": "system",
                "content": system_prompt.strip(),
            },
            {
                "role": "user",
                "content": final_prompt,
            },
        ]

    def _build_prompt(
        self,
        *,
        user_prompt: str,
        context: Dict[str, Any],
    ) -> str:
        """
        ユーザー要求 + 動画解析データを統合する。
        """

        context_json = json.dumps(
            context,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        prompt = f"""
# ユーザーからの解析要求

{user_prompt}

# 動画解析データ

{context_json}

# 出力形式

次のJSON構造を基本として出力してください。

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

timelineには可能な限り
start_time / end_time / description / evidence
を含めてください。

evidenceには、

- subtitle
- transcript
- ocr
- scene
- metadata

など、何を根拠にした情報なのかを記載してください。
"""

        # 長すぎるプロンプトを制限
        if len(prompt) > self.max_prompt_chars:

            logger.warning(
                "LLMプロンプトが長すぎるため切り詰めます。"
                " length=%s max=%s",
                len(prompt),
                self.max_prompt_chars,
            )

            prompt = (
                prompt[: self.max_prompt_chars]
                + "\n\n"
                "[SYSTEM NOTE] 入力データはサイズ制限により一部省略されています。"
            )

        return prompt

    # =========================================================
    # Context
    # =========================================================

    def _build_context(
        self,
        *,
        metadata: Dict[str, Any],
        frames: Sequence[Dict[str, Any]],
        subtitles: Sequence[Dict[str, Any]],
        transcript: Sequence[Dict[str, Any]],
        timeline: Sequence[Dict[str, Any]],
        scenes: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        VideoAnalysisServiceから渡された情報をLLM用に整理する。
        """

        return {
            "metadata": self._sanitize_metadata(metadata),

            "frames": self._limit_items(
                frames,
                self.MAX_FRAMES,
            ),

            "subtitles": self._limit_items(
                subtitles,
                self.MAX_SUBTITLES,
            ),

            "transcript": self._limit_items(
                transcript,
                self.MAX_TRANSCRIPT_SEGMENTS,
            ),

            "timeline": self._limit_items(
                timeline,
                self.MAX_TIMELINE_ITEMS,
            ),

            "scenes": self._limit_items(
                scenes,
                self.MAX_SCENES,
            ),
        }

    def _sanitize_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        LLMに不要な巨大データや内部情報をある程度除外する。
        """

        allowed_keys = {
            "filename",
            "duration",
            "fps",
            "frame_count",
            "width",
            "height",
            "resolution",
            "codec",
            "video_codec",
            "audio_codec",
            "format",
            "size",
            "has_audio",
            "has_video",
        }

        result = {}

        for key, value in metadata.items():

            if key in allowed_keys:
                result[key] = value

        return result

    def _limit_items(
        self,
        items: Sequence[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        大量データによるLLMコンテキスト爆発を防止する。
        """

        if not items:
            return []

        result = []

        for item in items[:limit]:

            if isinstance(item, dict):
                result.append(dict(item))
            else:
                result.append(
                    {
                        "value": str(item)
                    }
                )

        return result

    # =========================================================
    # JSON Parsing
    # =========================================================

    def _parse_llm_json(
        self,
        text: str,
    ) -> Optional[Dict[str, Any]]:
        """
        LLM出力からJSON Objectを抽出する。

        対応:
            1. 素のJSON
            2. ```json ... ```
            3. JSON前後に説明文
            4. JSON文字列中の括弧を考慮した抽出
        """

        if not text:
            return None

        text = text.strip()

        # ---------------------------------------------
        # 1. まず全文JSONを試す
        # ---------------------------------------------

        try:

            data = json.loads(text)

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            pass

        # ---------------------------------------------
        # 2. Markdownコードブロック
        # ---------------------------------------------

        code_block_pattern = re.compile(
            r"```(?:json|JSON)?\s*(.*?)\s*```",
            re.DOTALL,
        )

        matches = code_block_pattern.findall(text)

        for candidate in matches:

            candidate = candidate.strip()

            try:

                data = json.loads(candidate)

                if isinstance(data, dict):
                    return data

            except json.JSONDecodeError:
                continue

        # ---------------------------------------------
        # 3. バランスを考慮してJSON Objectを探す
        # ---------------------------------------------

        candidate = self._extract_json_object(text)

        if candidate:

            try:

                data = json.loads(candidate)

                if isinstance(data, dict):
                    return data

            except json.JSONDecodeError as exc:

                logger.warning(
                    "JSON Object抽出後のパースに失敗: %s",
                    exc,
                )

        # ---------------------------------------------
        # 4. 最後の手段
        # ---------------------------------------------

        logger.warning(
            "LocalLLMのJSONパースに失敗しました。"
            " raw=%s",
            text[:500],
        )

        return None

    def _extract_json_object(
        self,
        text: str,
    ) -> Optional[str]:
        """
        文字列内から最初の完全なJSON Objectを抽出する。

        単純な

            text.find("{")
            text.rfind("}")

        より安全。
        """

        start = text.find("{")

        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False

        for index in range(start, len(text)):

            char = text[index]

            if escaped:

                escaped = False
                continue

            if char == "\\" and in_string:

                escaped = True
                continue

            if char == '"':

                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":

                depth += 1

            elif char == "}":

                depth -= 1

                if depth == 0:

                    return text[start:index + 1]

        return None

    # =========================================================
    # Result normalization
    # =========================================================

    def _normalize_result(
        self,
        data: Dict[str, Any],
        *,
        metadata: Dict[str, Any],
        subtitles: Sequence[Dict[str, Any]],
        transcript: Sequence[Dict[str, Any]],
        timeline: Sequence[Dict[str, Any]],
        scenes: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        LLM出力をアプリ側で扱いやすい形に統一する。
        """

        result = dict(data)

        defaults = {
            "title": metadata.get(
                "filename",
                "動画解析結果",
            ),
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
            "uncertainties": [],
        }

        for key, default_value in defaults.items():

            if key not in result:
                result[key] = default_value

        # ---------------------------------------------
        # 型補正
        # ---------------------------------------------

        list_fields = [
            "keywords",
            "concepts",
            "important_points",
            "sections",
            "timeline",
            "detected_objects",
            "detected_text",
            "code",
            "questions",
            "answers",
            "knowledge",
            "uncertainties",
        ]

        for field in list_fields:

            if not isinstance(result[field], list):

                result[field] = [result[field]]

        if not isinstance(result["spoken_content"], str):
            result["spoken_content"] = str(
                result["spoken_content"]
            )

        if not isinstance(result["subtitle_summary"], str):
            result["subtitle_summary"] = str(
                result["subtitle_summary"]
            )

        # ---------------------------------------------
        # confidenceを0～1へ正規化
        # ---------------------------------------------

        result["confidence"] = self._normalize_confidence(
            result.get("confidence")
        )

        # ---------------------------------------------
        # Provider情報
        # ---------------------------------------------

        result["_provider"] = "local_llm"

        result["_source"] = {
            "video_path": video_path_safe(metadata),
            "subtitle_count": len(subtitles),
            "transcript_count": len(transcript),
            "scene_count": len(scenes),
            "timeline_count": len(timeline),
        }

        return result

    def _normalize_confidence(
        self,
        value: Any,
    ) -> float:
        """
        confidenceを0～1のfloatにする。
        """

        try:

            number = float(value)

        except (TypeError, ValueError):

            return 0.0

        # 0～100で返してきた場合
        if number > 1.0 and number <= 100.0:

            number /= 100.0

        return max(
            0.0,
            min(
                1.0,
                number,
            ),
        )

    # =========================================================
    # Fallback
    # =========================================================

    def _build_fallback_result(
        self,
        error_message: str,
        raw_text: str = "",
    ) -> Dict[str, Any]:
        """
        LLMエラー時にもVideoAnalysisServiceが
        完全停止しないようにする。
        """

        return {
            "title": "解析エラー",

            "summary": (
                "LocalLLMでの動画解析中にエラーが発生しました。"
            ),

            "description": (
                raw_text
                or error_message
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
            "subtitle_summary": "",

            "questions": [],
            "answers": [],
            "knowledge": [],

            "confidence": 0.0,

            "uncertainties": [
                error_message
            ],

            "_provider": "local_llm",
            "_status": "error",
        }


def video_path_safe(
    metadata: Dict[str, Any],
) -> str:
    """
    LLM結果にローカルの絶対パスをそのまま
    露出させないための補助関数。

    filenameだけを返す。
    """

    filename = metadata.get(
        "filename",
        "",
    )

    return str(filename)
