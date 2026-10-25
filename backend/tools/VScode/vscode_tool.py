# tools/VScode/vscode_tool.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


class VSCodeTool:
    """
    IntentInspector._run_tool_detector() から呼ばれる高速意図判定プラグイン。
    「VS Codeについて聞いている」「tasks.jsonのオプションを聞いている」時に確実に捕捉する。
    """

    # VS Code 固有のキーワード・ファイル名
    CORE_REGEX = re.compile(
        r"(?:vscode|vs\s*code|\.vscode|tasks\.json|settings\.json|launch\.json|"
        r"keybindings\.json|コマンドパレット|マルチカーソル|ワークスペース)",
        re.IGNORECASE,
    )

    # 本で学んだ tasks.json / settings.json のオプション群（これが出たら100% VS Code意図）
    TASK_OPTION_REGEX = re.compile(
        r"\b(?:problemMatcher|ploblemMatcher|revealProblems|showReuseMessage|"
        r"beginsPattern|endsPattern|activeOnStart|dependsOn|dependsOrder|"
        r"isBackground|promptOnClose|runOptions|reevaluateOnRerun|folderOpen|"
        r"autoDetect|isDefault|fileLocation)\b",
        re.IGNORECASE,
    )

    @classmethod
    def can_fast_route(
        cls,
        message: str,
        msg_lower: str,
        inspector_cache: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, str]:
        # 1. スラッシュコマンド
        if msg_lower.startswith(("/vscode", "/task", "/tasks", "/setting")):
            return True, "vscode_slash_command"

        # 2. VS Code または .vscode 設定ファイル名が明示されている
        if cls.CORE_REGEX.search(message):
            return True, "vscode_core_keyword"

        # 3. 本に出てきた tasks.json の専門プロパティ名が含まれている
        if cls.TASK_OPTION_REGEX.search(message):
            return True, "vscode_task_option_keyword"

        # 4. 「ショートカット」「トリビア」「ビルドタスク」＋「教えて/やりたい」の組み合わせ
        if any(w in msg_lower for w in ("ショートカット", "トリビア", "タスク設定", "コンパイル設定")):
            return True, "vscode_trivia_or_task_intent"

        return False, ""

    @classmethod
    def detect_language(
        cls,
        message: str,
        msg_lower: str,
        inspector_cache: Dict[str, Any],
    ) -> Optional[str]:
        if re.search(r"(?:\bc言語\b|\bgcc\b|#include\s*<stdio\.h>)", message, re.IGNORECASE):
            return "c"
        if "typescript" in msg_lower or "tsc" in msg_lower:
            return "typescript"
        if "python" in msg_lower:
            return "python"
        return None