#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IntentInspector.py
==================

ユーザー入力を複数のDetectorで解析し、
ChatOrchestrator / Handler選択に必要なIntent情報を生成する。

基本方針
--------
IntentInspector自身は細かな意味判定を抱え込まず、

    Detector
        ↓
    Context
        ↓
    ModeRule
        ↓
    System Routing補正（Parser / Decomposition）

という流れでIntentを構築する司令塔（オーケストレーション層）。

Detector役割
------------
ForcedHandlerDetector
    メッセージ内の強制Handler指定を検出する。

ActionDetector
    actions.json のキーワードからユーザーの意図アクションを検出する。

TargetDetector
    targets.json のキーワードから操作対象を検出する。

ThemeSurfaceDetector
    UI（テーマ・面・レスポンシブ有無）の文脈を検出する。

DeploymentMetricDetector
    デプロイ関連のキーワード・テーマを検出する。

MessageTypeDetector
    メッセージ種別（コードか、HTMLを含むか等）を判定する。

System Routing（IntentInspectorが最後に補正するもの）
------------------------------------------------------
DecompositionHandler
    <script>...</script> の抽出・分解などを扱う。

ParserHandler
    Python / Java / JavaScript / JSX などのソースコード解析を扱う。

    誤ルーティングを防ぐため、ModeRuleのスコアリング結果よりも
    優先して最後に上書きする。
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .detectors import (
    ForcedHandlerDetector,
    ActionDetector,
    TargetDetector,
    ThemeSurfaceDetector,
    DeploymentMetricDetector,
    load_json,
)
from .MessageTypeDetector import MessageTypeDetector
from .mode_rule import build_mode_rules


# ============================================================
# Path / Cache
# ============================================================

_DIR = os.path.dirname(os.path.abspath(__file__))
_KNOWLEDGE_DIR = os.path.join(_DIR, "Intentknowledge")

_INSPECTOR_CACHE: Dict[str, Any] = {}

_REQUIRED_KNOWLEDGE_KEYS = (
    "actions",
    "targets",
    "scoring",
    "mode_rules",
    "deployment_keywords",
    "deployment_themes",
)

# 旧配置（Intentknowledge/ができる前の名残）との互換用
_LEGACY_KNOWLEDGE_FILES = (
    "deployment_keywords.json",
    "deployment_themes.json",
)


# ============================================================
# Parser Routing Settings
# ============================================================

PARSER_COMMANDS = (
    "/parse",
    "/code",
    "/analyze",
)

PARSER_STRONG_KEYWORDS = (
    "コードを解析",
    "コード解析",
    "コードを説明",
    "コードを読んで",
    
    "コードを読み取って",
    "コードを読み取る",
    "コードを見て",
    "ソースを解析",
    "ソースコードを解析",
    "関数を説明",
    "関数を解析",
    "メソッドを説明",
    "メソッドを解析",
    "クラスを説明",
    "クラスを解析",
    "変数を説明",
    "変数を解析",
)

ANALYSIS_KEYWORDS = (
    "解析",
    "分析",
    "説明",
    "読み取",
    "調べ",
    "見て",
)

LANGUAGE_ALIASES = {
    "python": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "jsx": "javascript",
    "react": "javascript",
    "java": "java",
}

DECOMPOSITION_KEYWORDS = (
    "抽出",
    "取り出",
    "分解",
    "切り出",
    "script",
    "jsに",
    "javascriptに",
)


# ============================================================
# IntentInspector
# ============================================================

class IntentInspector:
    """
    Detector群をまとめ、Handler選択用のIntentを生成する。
    """

    def __init__(
        self,
        message: Any,
        available_knowledge_keys: Optional[List[str]] = None,
    ) -> None:
        self.raw_message = message
        self.available_knowledge_keys = available_knowledge_keys or []

        self.message = self._normalize_message(message)
        self.msg_lower = self.message.lower().strip()

        self._load_knowledge()
        self._initialize_detectors()

    # ========================================================
    # Message Normalization
    # ========================================================

    @staticmethod
    def _normalize_message(message: Any) -> str:
        """str / オブジェクト形式のmessageを文字列へ統一する。"""
        if isinstance(message, str):
            return message

        return str(
            getattr(
                message,
                "text",
                getattr(message, "content", getattr(message, "body", message)),
            )
        )

    # ========================================================
    # Knowledge Load
    # ========================================================

    def _load_knowledge(self) -> None:
        """Intentknowledge配下のJSONをプロセス全体で1回だけキャッシュする。"""
        global _INSPECTOR_CACHE

        if _INSPECTOR_CACHE:
            return

        print("📦 [IntentInspector] Intentknowledge JSONを読み込みます...", flush=True)

        # Intentknowledge/ 配下を再帰ロード
        if os.path.exists(_KNOWLEDGE_DIR):
            for root, _, files in os.walk(_KNOWLEDGE_DIR):
                for file_name in files:
                    if not file_name.lower().endswith(".json"):
                        continue

                    file_path = os.path.join(root, file_name)
                    cache_key = os.path.splitext(file_name)[0]

                    try:
                        _INSPECTOR_CACHE[cache_key] = load_json(file_path)
                    except Exception as exc:
                        print(
                            f"⚠️ [IntentInspector] {file_name} 読み込み失敗: {exc}",
                            flush=True,
                        )

        # 旧配置（Intentknowledge/より前）との互換
        for extra_file in _LEGACY_KNOWLEDGE_FILES:
            cache_key = os.path.splitext(extra_file)[0]
            if cache_key in _INSPECTOR_CACHE:
                continue

            extra_path = os.path.join(_DIR, extra_file)
            if not os.path.exists(extra_path):
                continue

            try:
                _INSPECTOR_CACHE[cache_key] = load_json(extra_path)
            except Exception as exc:
                print(
                    f"⚠️ [IntentInspector] {extra_file} 読み込み失敗: {exc}",
                    flush=True,
                )

        # 必須キーが無い場合は空dictで保証（後段の.get()を安全にする）
        for key in _REQUIRED_KNOWLEDGE_KEYS:
            _INSPECTOR_CACHE.setdefault(key, {})

    # ========================================================
    # Detector Initialization
    # ========================================================

    def _initialize_detectors(self) -> None:
        self.forced_detector = ForcedHandlerDetector()
        self.action_detector = ActionDetector(_INSPECTOR_CACHE["actions"])
        self.target_detector = TargetDetector(_INSPECTOR_CACHE["targets"])
        self.theme_detector = ThemeSurfaceDetector()
        self.deployment_detector = DeploymentMetricDetector(
            _INSPECTOR_CACHE["deployment_keywords"],
            _INSPECTOR_CACHE["deployment_themes"],
        )
        self.message_detector = MessageTypeDetector(self.message)

        mode_rule_data = _INSPECTOR_CACHE["mode_rules"]
        self.mode_rules = build_mode_rules(
            _INSPECTOR_CACHE["scoring"],
            mode_rule_data,
            list(mode_rule_data.keys()),
        )

    # ========================================================
    # Context
    # ========================================================

    def _build_context(
        self,
        message_type: Dict[str, Any],
        ui_context: Dict[str, Any],
        deployment: Dict[str, Any],
        target_categories: List[str],
    ) -> Dict[str, Any]:
        return {
            "message_type": message_type.get("type", "unknown"),
            "is_code": message_type.get("is_code", False),
            "has_html": message_type.get("has_html", False),
            "theme": ui_context.get("theme"),
            "surface": ui_context.get("surface"),
            "responsive": ui_context.get("responsive", False),
            "modify_existing": ui_context.get("modify_existing", False),
            "deployment_metrics": deployment.get("deployment_metrics", {}),
            "deployment_surface": deployment.get("deployment_surface"),
            "deployment_theme": deployment.get("deployment_theme"),
            "target_categories": target_categories,
            "_KW_named_themes": _INSPECTOR_CACHE.get("deployment_keywords", {}).get(
                "named_themes", {}
            ),
        }

    # ========================================================
    # Code Language Detection
    # ========================================================

    def _detect_code_language(self) -> Optional[str]:
        # Markdown fence（```python, ```js など）を最優先
        fence_match = re.search(r"```([a-zA-Z0-9_+\-#]+)", self.message)
        if fence_match:
            hint = fence_match.group(1).lower()
            detected = LANGUAGE_ALIASES.get(hint)
            if detected:
                return detected

        # 自然文からの推測
        for alias, language in LANGUAGE_ALIASES.items():
            if self._contains_word(self.msg_lower, alias):
                return language

        return None

    # ========================================================
    # Parser Routing
    # ========================================================

    def _detect_parser_request(self, message_type: Dict[str, Any]) -> Tuple[bool, str]:
        msg = self.msg_lower

        if any(msg.startswith(command) for command in PARSER_COMMANDS):
            return True, "parser_command"

        if "```" in self.message:
            return True, "markdown_code_block"

        if any(keyword in msg for keyword in PARSER_STRONG_KEYWORDS):
            return True, "explicit_code_analysis"

        language = self._detect_code_language()
        has_analysis_request = any(keyword in msg for keyword in ANALYSIS_KEYWORDS)

        if language and has_analysis_request:
            return True, "language_and_analysis"

        # message_type.is_code だけでは強制ルーティングしない
        return False, ""

    # ========================================================
    # Decomposition Routing
    # ========================================================

    def _detect_decomposition_request(self) -> Tuple[bool, str]:
        has_script_tag = bool(
            re.search(r"<script\b[^>]*>", self.message, flags=re.IGNORECASE)
        )
        if not has_script_tag:
            return False, ""

        if any(keyword in self.msg_lower for keyword in DECOMPOSITION_KEYWORDS):
            return True, "script_tag_extraction"

        return True, "script_tag_detected"

    # ========================================================
    # Mode Rules
    # ========================================================

    def _calculate_mode(
        self,
        actions: Any,
        targets: Any,
        context: Dict[str, Any],
    ) -> Tuple[str, int]:
        best_mode = "unknown"
        highest_score = 0

        for rule in self.mode_rules:
            try:
                matched = rule.match(self.msg_lower, actions, targets, context)
            except Exception as exc:
                print(f"⚠️ [IntentInspector] ModeRule.match失敗: {exc}", flush=True)
                continue

            if not matched:
                continue

            try:
                score = rule.calculate_score(self.msg_lower, actions, targets, context)
            except Exception as exc:
                print(f"⚠️ [IntentInspector] ModeRule.calculate_score失敗: {exc}", flush=True)
                continue

            if score > highest_score:
                highest_score = score
                best_mode = rule.mode_name

        scoring = _INSPECTOR_CACHE.get("scoring", {})
        max_score = scoring.get("global", {}).get("max_score_cap", 85)
        highest_score = min(highest_score, max_score)

        return best_mode, highest_score

    # ========================================================
    # Utility
    # ========================================================

    @staticmethod
    def _contains_word(text: str, word: str) -> bool:
        """短い英語alias（js / py等）の誤爆を防ぐための単語境界チェック。"""
        if len(word) <= 2:
            pattern = rf"(?<![a-z0-9_]){re.escape(word)}(?![a-z0-9_])"
            return bool(re.search(pattern, text, flags=re.IGNORECASE))
        return word in text

    # ========================================================
    # Inspect（エントリーポイント）
    # ========================================================

    def inspect(self) -> Dict[str, Any]:
        # --- Detector実行 ---
        forced_handler = self.forced_detector.detect(self.message)
        message_type = self.message_detector.detect()
        actions = self.action_detector.detect(self.msg_lower)
        targets = self.target_detector.detect_words(self.msg_lower)
        target_categories = self.target_detector.detect_categories(self.msg_lower)
        ui_context = self.theme_detector.detect(self.msg_lower)
        deployment = self.deployment_detector.detect(self.msg_lower)

        context = self._build_context(message_type, ui_context, deployment, target_categories)

        # --- ModeRuleによるスコアリング ---
        best_mode, highest_score = self._calculate_mode(actions, targets, context)

        result: Dict[str, Any] = {
            "mode": best_mode,
            "score": highest_score,
            "forced_handler": forced_handler,
            "actions": actions,
            "targets": targets,
            "target_categories": target_categories,
            "message_type_info": message_type,
            "available_knowledge": self.available_knowledge_keys,
            **ui_context,
            **deployment,
        }

        # --- 例外ルール：「空箱を作らない」 ---
        if "空箱" in self.msg_lower and "作らない" in self.msg_lower:
            best_mode = "unknown"
            highest_score = 0
            result["forced_handler"] = None

        # --- System Handler Routing（最終補正） ---
        use_decomposition, decomposition_reason = self._detect_decomposition_request()
        use_parser, parser_reason = self._detect_parser_request(message_type)
        detected_language = self._detect_code_language()
        routing_reason = ""

        if use_decomposition:
            best_mode = "script_extraction"
            highest_score = 100
            result["forced_handler"] = "DecompositionHandler"
            routing_reason = decomposition_reason
        elif use_parser:
            best_mode = "code_analysis"
            highest_score = 100
            result["forced_handler"] = "ParserHandler"
            routing_reason = parser_reason

        result.update(
            {
                "mode": best_mode,
                "score": highest_score,
                "detected_language": detected_language,
                "routing_reason": routing_reason,
                "routing": {
                    "parser": use_parser,
                    "decomposition": use_decomposition,
                },
            }
        )

        print(
            "[IntentInspector]",
            {
                "mode": best_mode,
                "score": highest_score,
                "handler": result.get("forced_handler"),
                "language": detected_language,
                "reason": routing_reason,
                "is_code": message_type.get("is_code", False),
            },
            flush=True,
        )

        return result


# ============================================================
# Standalone Test
# ============================================================

if __name__ == "__main__":
    TEST_MESSAGES = [
        "こんにちは",
        "Pythonについて教えて",
        "Pythonコードを解析して",
        "/parse python",
        "```python\ndef hello():\n    print('hello')\n```",
        "<script>\nconsole.log('hello');\n</script>",
        "すごい、完璧だね！",
    ]

    print("=== IntentInspector Standalone Test ===")
    # 実運用ではdetectors / MessageTypeDetector / mode_rule 等が
    # importできる環境で実行してください（単体では import エラーになります）。