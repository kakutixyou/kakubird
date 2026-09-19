# -*- coding: utf-8 -*-
"""
LocalVideoProvider.py

自作の LocalLLMEngine を用いて動画解析を行う VideoProvider の実装。
VideoAnalysisService の VideoProvider プロトコルを満たします。
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Sequence, Optional

from api.services.llm.LocalLLMEngine import LocalLLMEngine
from api.services.llm.GenerationResult import GenerationResult

logger = logging.getLogger(__name__)

class LocalVideoProvider:
    """
    LocalLLMEngine をバックエンドとして使用する動画解析Provider。
    
    ※現状のLocalLLMEngineはテキストベースであるため、
    VideoPromptBuilderが生成した「字幕・音声・OCRの統合テキストプロンプト」
    を入力として推論を行います。
    """

    def __init__(self, llm_engine: LocalLLMEngine):
        self.llm_engine = llm_engine

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
        VideoAnalysisService から呼び出されるメインメソッド。
        """
        logger.info(f"LocalVideoProvider: '{metadata.get('filename', 'video')}' の解析を開始します。")

        # Chat形式に変換してエンジンへ渡す
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたは高度な動画解析AIです。"
                    "ユーザーから提供された動画のメタデータ、タイムライン、"
                    "字幕などの情報を元に、指定されたJSONフォーマットで厳密に出力してください。"
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # 同期関数である llm_engine.chat を非同期スレッドで実行し、
        # 他の非同期タスク（APIルーティングなど）をブロックしないようにする
        try:
            result: GenerationResult = await asyncio.to_thread(
                self.llm_engine.chat,
                messages=messages,
                max_tokens=2048,
                temperature=0.3, # 解析・抽出タスクのため低めに設定
                repeat_penalty=1.1,
            )
        except Exception as exc:
            logger.error(f"LocalLLM 推論中にエラーが発生しました: {exc}")
            return self._build_fallback_result(str(exc))

        # 結果のチェック (GenerationResult の実装に依存)
        # 失敗した場合やテキストが空の場合はフォールバックを返す
        text = getattr(result, "text", "")
        if not text:
            error_msg = getattr(result, "error", "LLMが空の応答を返しました。")
            return self._build_fallback_result(error_msg)

        # LLMの出力テキストをJSONとしてパースする
        return self._parse_llm_json(text)


    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        """
        LLMのテキスト出力からJSONを安全に抽出・パースする。
        """
        text = text.strip()

        # LLMが ```json ... ``` のようなマークダウンブロックで囲んでいる場合の対処
        json_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
        match = json_pattern.search(text)
        
        if match:
            json_str = match.group(1)
        else:
            # マークダウンがない場合は、最初の '{' から最後の '}' までを抽出
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = text[start_idx:end_idx+1]
            else:
                json_str = text # 抽出できなければ全体をパースしてみる

        try:
            parsed_data = json.loads(json_str)
            if isinstance(parsed_data, dict):
                return parsed_data
            else:
                return self._build_fallback_result("LLMの出力が辞書形式(Object)ではありませんでした。")
        except json.JSONDecodeError as exc:
            logger.warning(f"LocalLLMのJSONパースに失敗しました: {exc}\n生の出力: {text[:200]}...")
            return self._build_fallback_result(
                "LLMが正しいJSONフォーマットを出力しませんでした。",
                raw_text=text
            )


    def _build_fallback_result(self, error_message: str, raw_text: str = "") -> Dict[str, Any]:
        """
        パースエラーや推論エラー時のフォールバック用の辞書を生成する。
        VideoAnalysisService がエラーで止まらないようにするための措置。
        """
        return {
            "title": "解析エラー",
            "summary": "LocalLLMでの解析中にエラーが発生したか、フォーマットが不正でした。",
            "description": raw_text or error_message,
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
            "uncertainties": [error_message]
        }
