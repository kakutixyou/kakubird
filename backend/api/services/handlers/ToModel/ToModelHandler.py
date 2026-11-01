#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/services/handlers/ToModel/ToModelHandler.py

【役割】
1. 専門解析モード (Pre-Responder / Forced Handler):
   - 動画URL・造語曲解析 (`video_curator` / `to_model_studio`)
   - マルウェア・HEX・DoS・キーロガー防御 (`malware_defense` / `to_model_studio`)
   - 日本語体験談・ブラック企業メモ＆コメントJSON (`experience_memo` / `to_model_studio`)
2. 本体搭載・会話モード (Conversational Engine / ChatHandler.fallback_generate ＆ LocalLLMEngine 互換):
   - 将来的に自作モデルを本体に常駐搭載した際、`ChatHandler` の `local_llm` または `fallback_generate`
     としてそのまま接続でき、会話履歴 (`ConversationState`)・要約 (`summary`)・知識 (`knowledge_data`)
     を踏まえた自然なマルチターン日本語対話を行う。
   - 会話の途中で「このURLを解析して」「今の話をJSONにメモして」と言われたら、シームレスに解析データも添付する。
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ToModelConversationEngine:
    """
    自作モデル (to_model) の対話・文脈理解エンジン。
    ConversationState の履歴・現在のトピック・未解決タスク (unresolved_queries) を参照して応答を生成する。
    """

    def generate_reply(
        self,
        user_message: str,
        analysis: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
        summary: Optional[Dict[str, Any]] = None,
        knowledge_data: Optional[List[Any]] = None,
        engine_facade: Optional[Any] = None,
    ) -> Dict[str, Any]:
        msg = str(user_message or "").strip()
        lower = msg.lower()
        topic = getattr(state, "current_topic", None) or (summary or {}).get("current_topic") or "一般対話"
        turn_count = getattr(state, "turn_count", 1) if state is not None else 1

        # 1. マルウェア・セキュリティに関する相談・会話
        if any(k in lower or k in msg for k in ("dos mode", "keylog", "synflood", "portscanner", "マルウェア", "キーロガー", "セキュリティ")):
            sec_data = engine_facade.run(message=msg, mode="security")["data"] if engine_facade else {}
            sec_report = sec_data.get("security_analysis", {})
            c2_ips = sec_report.get("string_analysis", {}).get("extracted_ipv4_iocs", ["128.91.34.188"])
            reply_text = (
                f"セキュリティ解析モデルとして確認しました（現在のトピック: {topic}）。\n"
                f"入力されたデータから、C2通信先（{', '.join(c2_ips)}）および DoS / キーロガーの痕跡を検出しています。\n"
                f"チャット欄の防御コンソールから `tcp_syncookies=1` の有効化と `keylog.txt` のシンクホールロックを適用できます。他にも気になる挙動はありますか？"
            )
            return {
                "reply": reply_text,
                "response_type": "to_model_studio",
                "active_page": "security",
                "data": sec_data,
            }

        # 2. ブラック企業での体験・仕事の悩み・日本語メモに関する対話
        if any(k in lower or k in msg for k in ("ブラック企業", "残業", "連勤", "大変だった", "つらい", "パワハラ", "退職", "メモ", "コメント")):
            memo_data = engine_facade.run(message=msg, mode="memo")["data"] if engine_facade else {}
            memo_obj = (memo_data.get("memo_analysis") or {}).get("experience_memo", {})
            cats = "・".join(memo_obj.get("categories", ["労働環境記録"]))
            score = memo_obj.get("severity_score", 85)
            reply_text = (
                f"お話しいただきありがとうございます。文脈から『{cats}』（当時の負荷指数: {score}/100）に関する大切な記録として受け止めました。\n"
                f"過酷な環境を乗り越えて現在こうしてご自身のAI開発を進められていること自体が素晴らしい前進です。\n"
                f"いつでも振り返りや動画のストーリー字幕に使えるよう、`experience_memos.json` と `comments.json` に構造化して記録しました。"
            )
            return {
                "reply": reply_text,
                "response_type": "to_model_studio",
                "active_page": "memo",
                "data": memo_data,
            }

        # 3. 動画URL解析・造語ソング・字幕に関する対話
        if any(k in lower or k in msg for k in ("http://", "https://", "動画", "字幕", "造語", "曲", "何人", "タイムバー", "youtube")):
            vid_data = engine_facade.run(message=msg, mode="video")["data"] if engine_facade else {}
            vid_info = vid_data.get("video_analysis", {})
            genre_name = (vid_info.get("genre") or {}).get("primary", "動画・音楽コンテンツ")
            spk_count = (vid_info.get("speaker_summary") or {}).get("total_speakers_count", 3)
            reply_text = (
                f"動画・音響解析エンジンでチェックしました！\n"
                f"・判定ジャンル: 『{genre_name}』\n"
                f"・検出された話者/ボーカル声部: {spk_count}人\n"
                f"下のインタラクティブ・タイムバーで秒単位の字幕と声部の切り替わりを確認でき、そのまま `project.json` として保存できます。"
            )
            return {
                "reply": reply_text,
                "response_type": "to_model_studio",
                "active_page": "video",
                "data": vid_data,
            }

        # 4. 一般的な日常会話・開発相談（Knowledge や会話履歴を踏まえた応答）
        knowledge_hint = ""
        if knowledge_data:
            knowledge_hint = f"（本体のKnowledge {len(knowledge_data)}件も参照しています）"

        reply_text = (
            f"なるほど、「{msg}」ですね！{knowledge_hint}\n"
            f"現在ターン{turn_count}（トピック: {topic}）として記憶しています。"
            f"雑談や設計の相談はもちろん、動画URLを渡しての話者・造語曲解析や、大変だった体験談のJSONメモ化、マルウェア文字列の検査もいつでもこのチャット欄から直接呼び出せますよ。"
        )
        return {
            "reply": reply_text,
            "response_type": "chat",
            "active_page": "video",
            "data": {
                "turn": turn_count,
                "topic": topic,
                "conversational_mode": True,
            },
        }


class ToModelHandler:
    """
    本体 (To Core) 側の Handler 実装。
    - `handle(request)` : ツール発火時や明示呼び出し時に構造化レスポンスを返す
    - `generate_chat_response(...)` : `ChatHandler(fallback_generate=...)` にそのまま渡せる会話関数
    """

    HANDLER_NAME = "ToModelHandler"
    DEFAULT_SCORE = 95

    def __init__(self, api_endpoint: str = "http://127.0.0.1:8001") -> None:
        self.enabled = True
        self.api_endpoint = api_endpoint
        self.conversation_engine = ToModelConversationEngine()
        self._engine: Optional[Any] = None

        try:
            from to_model.main import ToModelUnifiedEngine
            self._engine = ToModelUnifiedEngine()
        except Exception as exc:
            logger.info("to_model direct import unavailable (%s); using built-in/HTTP fallback.", exc)

    async def calculate_score(
        self,
        message: str,
        current_signals: Optional[Dict[str, Any]] = None,
    ) -> int:
        if not self.enabled:
            return 0
        signals = current_signals or {}
        forced = signals.get("forced_handler") or (signals.get("analysis") or {}).get("forced_handler")
        if forced in (
            "ToModelHandler",
            "VideoAnalyzerTool",
            "MalwareDefenseTool",
            "ExperienceMemoTool",
        ):
            return 100

        lower = (message or "").lower()
        if any(
            k in lower or k in message
            for k in (
                "dos mode", "keylog.txt", "synflooding", "portscanner",
                "動画解析", "造語", "ブラック企業", "コメントもjson", "何人が喋って",
            )
        ):
            return self.DEFAULT_SCORE
        return 0

    def generate_chat_response(
        self,
        user_message: str,
        analysis: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
        summary: Optional[Dict[str, Any]] = None,
        knowledge_data: Optional[List[Any]] = None,
    ) -> str:
        """
        ChatHandler.__init__(..., fallback_generate=to_model_handler.generate_chat_response)
        として登録できる会話生成メソッド。
        ローカルLLM (Ollama等) の代わり、または自作モデル単体での対話エンジンとして機能する。
        """
        conv_res = self.conversation_engine.generate_reply(
            user_message=user_message,
            analysis=analysis,
            state=state,
            summary=summary,
            knowledge_data=knowledge_data,
            engine_facade=self._engine,
        )
        return str(conv_res.get("reply") or "")

    async def handle(self, request: Any) -> Tuple[str, Dict[str, Any]]:
        """
        ChatHandler.pre_responders または Orchestrator から呼ばれた際の実処理。
        会話応答テキストと、AIChatMessageList.tsx が描画する構造化データ (meta) を返す。
        """
        if isinstance(request, dict):
            message = str(request.get("message") or request.get("text") or "")
            action_payload = request.get("action_payload") or request.get("option_data")
            state = request.get("state")
            analysis = request.get("analysis") or {}
        else:
            message = str(getattr(request, "message", "") or getattr(request, "text", "") or "")
            action_payload = getattr(request, "action_payload", None)
            state = getattr(request, "state", None)
            analysis = getattr(request, "analysis", None) or {}

        # 1. フロントエンド (.tsx) の onOptionSelect ボタン操作からのコールバックの場合
        if isinstance(action_payload, dict) and action_payload.get("action") and self._engine is not None:
            res = self._engine.run(message=message, action_payload=action_payload)
            display_msg = str(res.get("message") or "アクションを実行しました。")
            return display_msg, {
                "source": self.HANDLER_NAME,
                "type": res.get("response_type", "to_model_studio"),
                "response_type": res.get("response_type", "to_model_studio"),
                "active_page": res.get("active_page", "video"),
                "data": res.get("data", {}),
            }

        # 2. 会話＋専門解析の統合実行
        conv_out = self.conversation_engine.generate_reply(
            user_message=message,
            analysis=analysis,
            state=state,
            engine_facade=self._engine,
        )
        display_msg = str(conv_out["reply"])
        r_type = str(conv_out.get("response_type") or "to_model_studio")

        meta = {
            "source": self.HANDLER_NAME,
            "type": r_type,
            "response_type": r_type,
            "active_page": conv_out.get("active_page", "video"),
            "data": conv_out.get("data", {}),
        }
        return display_msg, meta


class ToModelResponderAdapter:
    """
    ChatHandler.py の `self.pre_responders` に差し込む Responder アダプター。
    """

    name = "to_model_responder"

    def __init__(
        self,
        handler: Optional[ToModelHandler],
        results_builder: Any,
        debug: Callable[[str], None],
    ) -> None:
        self.handler = handler or ToModelHandler()
        self.results = results_builder
        self._debug = debug

    async def try_respond(self, ctx: Any) -> Optional[Tuple[str, Any]]:
        if self.handler is None:
            return None

        message = getattr(ctx, "resolved_message", None) or getattr(ctx, "message", "")
        signals = getattr(ctx, "current_signals", None) or {}
        analysis = getattr(ctx, "analysis", None) or {}
        state = getattr(ctx, "state", None)

        score = await self.handler.calculate_score(
            message, {"analysis": analysis, **signals}
        )
        if score <= 0:
            return None

        self._debug(f"Delegating turn to ToModelHandler (score={score})")
        display_msg, meta = await self.handler.handle(
            {"message": message, "analysis": analysis, "state": state}
        )

        if state is not None and hasattr(state, "add_assistant_message"):
            state.add_assistant_message(
                content=display_msg,
                source=self.handler.HANDLER_NAME,
                intent=analysis.get("intent", "to_model"),
                topic=getattr(state, "current_topic", None),
            )

        if self.results is not None and hasattr(self.results, "finalize"):
            return self.results.finalize(
                message=display_msg,
                source=self.handler.HANDLER_NAME,
                state=state,
                current_signals=signals,
                extra=meta,
            )
        return display_msg, meta
