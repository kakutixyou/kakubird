from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


@dataclass
class VSCodeIntent:
    """VSCode パッケージおよび ProjectBuilderHandler 連携用の統一意図モデル。"""

    raw_message: str
    # mode:
    # - "chat": 一般的なVS Code質問・会話（LLMへ透過）
    # - "code_analysis": コード解析要求（ProjectBuilderHandler / LLMへ委譲）
    # - "partial_patch": 1部分ピンポイント修正（ProjectBuilderHandlerへ委譲）
    # - "app_development": アプリ開発・プロジェクト生成（ProjectBuilderHandlerへ委譲）
    # - "task_build": .vscode/tasks.json 動的生成
    # - "write_workspace": ワークスペース設定ファイル書き込み・注入
    # - "vscode_action": Diff表示 / 行ジャンプ / ロールバック等の直接操作
    # - "launch": VS Code エディタ起動
    mode: str = "chat"
    language: str = "general"  # "cpp" | "python" | "typescript" | "javascript" | "general"
    target_files: List[str] = field(default_factory=list)
    target_symbol: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    vscode_action: Optional[str] = None
    should_write: bool = False
    should_launch: bool = False
    allow_overwrite: bool = False
    should_pass_to_llm: bool = False
    delegate_to_project_builder: bool = False
    has_code_snippet: bool = False
    action_keywords: List[str] = field(default_factory=list)


class VSCodeIntentParser:
    """
    操作・言語・対象ファイル・書き込み意図・アプリ開発/部分修正連携を解析するクラス。
    「VSCodeHandler.pyを解析して」や「VSCodeについて色々教えて」といった発話を
    誤って tasks.json 生成UIで潰さないためのガードレールと、
    将来的なアプリ開発・1部分コード修正（ProjectBuilderHandler）へのブリッジ判定を行う。
    """

    # 1. コード解析・レビュー要求パターン
    CODE_ANALYSIS_PATTERNS = (
        r"vscodehandler\.py",
        r"vscode[_\-]?handler",
        r"\.(?:py|ts|tsx|js|jsx|java|cs|cpp|c)\s*(?:を|の)?\s*(?:解析|分析|レビュー|読んで|見て|診断|解説|説明)",
        r"(?:コード|ファイル|クラス|関数|実装)\s*(?:を|の)?\s*(?:解析|分析|レビュー|診断|解説)",
    )

    # 2. 1部分ピンポイント修正（Surgical Partial Patch）要求パターン
    PARTIAL_PATCH_KEYWORDS = (
        "1部分",
        "一部分",
        "部分修正",
        "だけ修正",
        "のみ修正",
        "だけ直",
        "のみ直",
        "ピンポイント",
        "1部分追加",
        "機能追加",
        "機能の追加",
        "一部コード",
        "partial",
        "<<<<<<< search",
    )

    # 3. アプリ開発・新規プロジェクト生成要求パターン
    APP_DEV_PATTERNS = (
        r"(?:web)?アプリ\s*(?:を|の)?\s*(?:作|作成|生成|実装|開発|構築)",
        r"プロジェクト\s*(?:を|の)?\s*(?:作|作成|生成|実装|開発|構築)",
        r"(?:react|next\.?js|vue|fastapi|flask)\s*(?:で|の)?\s*(?:アプリ|サイト|プロジェクト)",
    )

    # 4. VS Code に関する一般的な雑談・質問パターン
    CONVERSATIONAL_PATTERNS = (
        r"について(?:色々|いろいろ|詳しく)?(?:教えて|知りたい|語って|説明して)",
        r"(?:とは|って何|どう思う|おすすめ|比較|歴史|メリット|デメリット|使い方)",
        r"会話(?:も|を)?",
    )

    # 5. 明示的な VS Code 設定・タスクツール要求キーワード
    TOOL_ACTION_KEYWORDS = (
        "tasks.json",
        "settings.json",
        "launch.json",
        "problemmatcher",
        "タスク生成",
        "タスクを作",
        "ビルド設定",
        "コンパイル設定",
        "ショートカット一覧",
        "マルチカーソル",
        "コマンドパレット",
    )

    WRITE_KEYWORDS = ("連携", "書き込", "反映", "注入", "適用", "保存", "生成して開く")
    OVERWRITE_KEYWORDS = ("上書き", "強制", "overwrite", "force", "差し替え")
    LAUNCH_KEYWORDS = ("起動", "開く", "開いて", "フォーカス", "launch", "open")
    ROLLBACK_KEYWORDS = ("ロールバック", "元に戻", "復元", "rollback", "undo")
    DIFF_KEYWORDS = ("diff", "差分", "比較")

    FILE_PATTERN = re.compile(
        r"([A-Za-z0-9_./\\-]+\.(?:py|ts|tsx|js|jsx|json|c|cpp|h|hpp|java|cs|md))"
    )
    LINE_RANGE_PATTERN = re.compile(r"L?(\d+)\s*(?:〜|~|-|から)\s*L?(\d+)行?目?")
    SYMBOL_PATTERN = re.compile(r"(?:関数|メソッド|クラス|def|function|class)\s+`?([A-Za-z_][A-Za-z0-9_]*)`?")

    @classmethod
    def parse(
        cls,
        message: str,
        signals: Optional[Mapping[str, Any]] = None,
        *,
        explicit_file_path: Optional[str] = None,
        target_symbol: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        vscode_action: Optional[str] = None,
    ) -> VSCodeIntent:
        msg = (message or "").strip()
        msg_lower = msg.lower()
        sig = dict(signals) if isinstance(signals, Mapping) else {}

        # ファイル抽出
        target_files = list(dict.fromkeys(cls.FILE_PATTERN.findall(msg)))
        if explicit_file_path and explicit_file_path not in target_files:
            target_files.insert(0, explicit_file_path)

        # 行番号・シンボル抽出
        if start_line is None or end_line is None:
            line_match = cls.LINE_RANGE_PATTERN.search(msg)
            if line_match:
                start_line = int(line_match.group(1))
                end_line = int(line_match.group(2))

        if not target_symbol:
            sym_match = cls.SYMBOL_PATTERN.search(msg)
            if sym_match:
                target_symbol = sym_match.group(1)

        resolved_action = (
            vscode_action
            or str(sig.get("vscode_action") or "").strip()
            or cls._detect_vscode_action(msg, msg_lower)
        )

        language = cls._detect_language(msg_lower, target_files)
        has_code_snippet = "```" in msg or "<<<<<<< SEARCH" in msg or "def " in msg or "export " in msg

        should_write = any(k in msg for k in cls.WRITE_KEYWORDS)
        allow_overwrite = any(k in msg_lower for k in cls.OVERWRITE_KEYWORDS) or should_write
        should_launch = should_write or any(k in msg_lower for k in cls.LAUNCH_KEYWORDS)
        matched_actions = [k for k in cls.TOOL_ACTION_KEYWORDS if k in msg_lower]

        # ------------------------------------------------------------------
        # 優先度1: 明示的な VSCode アクション (Rollback / Diff / Goto / PartialPatch)
        # ------------------------------------------------------------------
        if resolved_action in {
            "vscode_rollback",
            "vscode_open_diff",
            "vscode_goto_line",
            "vscode_connect",
            "apply_partial_patch",
        }:
            is_patch = resolved_action == "apply_partial_patch"
            return VSCodeIntent(
                raw_message=msg,
                mode="partial_patch" if is_patch else "vscode_action",
                language=language,
                target_files=target_files,
                target_symbol=target_symbol,
                start_line=start_line,
                end_line=end_line,
                vscode_action=resolved_action,
                should_write=True,
                should_launch=True,
                allow_overwrite=True,
                should_pass_to_llm=False,
                delegate_to_project_builder=is_patch,
                has_code_snippet=has_code_snippet,
                action_keywords=matched_actions,
            )

        # ------------------------------------------------------------------
        # 優先度2: 1部分コード修正・機能追加 (ProjectBuilderHandler と連携)
        # ------------------------------------------------------------------
        is_partial_patch = any(k in msg_lower for k in cls.PARTIAL_PATCH_KEYWORDS)
        if is_partial_patch and (target_files or has_code_snippet or target_symbol):
            return VSCodeIntent(
                raw_message=msg,
                mode="partial_patch",
                language=language,
                target_files=target_files,
                target_symbol=target_symbol,
                start_line=start_line,
                end_line=end_line,
                vscode_action="apply_partial_patch",
                should_write=True,
                should_launch=should_launch,
                allow_overwrite=True,
                should_pass_to_llm=False,
                delegate_to_project_builder=True,
                has_code_snippet=has_code_snippet,
                action_keywords=matched_actions,
            )

        # ------------------------------------------------------------------
        # 優先度3: コード解析要求（「VSCodeHandler.pyを解析して」等）
        # ------------------------------------------------------------------
        is_code_analysis = any(re.search(pat, msg_lower) for pat in cls.CODE_ANALYSIS_PATTERNS)
        if is_code_analysis or any("vscodehandler" in f.lower() for f in target_files):
            return VSCodeIntent(
                raw_message=msg,
                mode="code_analysis",
                language=language if language != "general" else "python",
                target_files=target_files or ["VSCodeHandler.py"],
                target_symbol=target_symbol,
                should_write=False,
                should_launch=False,
                allow_overwrite=False,
                should_pass_to_llm=True,  # PreResponder で横取りせず LLM / ProjectBuilderHandler に回す
                delegate_to_project_builder=bool(has_code_snippet or target_files),
                has_code_snippet=has_code_snippet,
                action_keywords=matched_actions,
            )

        # ------------------------------------------------------------------
        # 優先度4: アプリ開発・新規プロジェクト生成要求
        # ------------------------------------------------------------------
        is_app_dev = any(re.search(pat, msg_lower) for pat in cls.APP_DEV_PATTERNS)
        if is_app_dev and not matched_actions:
            return VSCodeIntent(
                raw_message=msg,
                mode="app_development",
                language=language,
                target_files=target_files,
                should_write=False,
                should_launch=should_launch,
                allow_overwrite=False,
                should_pass_to_llm=True,
                delegate_to_project_builder=True,
                has_code_snippet=has_code_snippet,
                action_keywords=matched_actions,
            )

        # ------------------------------------------------------------------
        # 優先度5: 一般会話（「VSCodeについて色々教えて」等）
        # ------------------------------------------------------------------
        has_tool_keyword = bool(matched_actions)
        is_conversational = any(re.search(pat, msg_lower) for pat in cls.CONVERSATIONAL_PATTERNS)
        if is_conversational and not has_tool_keyword and not should_write:
            return VSCodeIntent(
                raw_message=msg,
                mode="chat",
                language=language,
                target_files=target_files,
                should_write=False,
                should_launch=False,
                allow_overwrite=False,
                should_pass_to_llm=True,
                delegate_to_project_builder=False,
                has_code_snippet=has_code_snippet,
                action_keywords=[],
            )

        # ------------------------------------------------------------------
        # 優先度6: タスク生成 / ワークスペース書き込み / 起動
        # ------------------------------------------------------------------
        if should_write:
            mode = "write_workspace"
        elif has_tool_keyword or any(k in msg_lower for k in ("gcc", "コンパイル", "ビルド", "task", "タスク")):
            mode = "task_build"
        elif should_launch:
            mode = "launch"
        else:
            mode = "chat"

        return VSCodeIntent(
            raw_message=msg,
            mode=mode,
            language=language,
            target_files=target_files,
            target_symbol=target_symbol,
            start_line=start_line,
            end_line=end_line,
            vscode_action=resolved_action,
            should_write=should_write,
            should_launch=should_launch,
            allow_overwrite=allow_overwrite,
            should_pass_to_llm=(mode == "chat" and not has_tool_keyword),
            delegate_to_project_builder=False,
            has_code_snippet=has_code_snippet,
            action_keywords=matched_actions,
        )

    @classmethod
    def _detect_vscode_action(cls, msg: str, msg_lower: str) -> Optional[str]:
        if any(k in msg or k in msg_lower for k in cls.ROLLBACK_KEYWORDS):
            return "vscode_rollback"
        if any(k in msg_lower for k in cls.DIFF_KEYWORDS) and (
            "vscode" in msg_lower or "vs code" in msg_lower or "開" in msg
        ):
            return "vscode_open_diff"
        return None

    @staticmethod
    def _detect_language(msg_lower: str, target_files: List[str]) -> str:
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".c": "cpp",
            ".cpp": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
        }
        for f in target_files:
            ext = Path(f).suffix.lower()
            if ext in ext_map:
                return ext_map[ext]

        if any(k in msg_lower for k in ("python", "pytest", "ruff", "flake8", "fastapi", "flask")):
            return "python"
        if any(k in msg_lower for k in ("typescript", "tsc", "npm", "pnpm", "yarn", "vite", "react", "next")):
            return "typescript"
        if any(k in msg_lower for k in ("gcc", "clang", "g++", "c言語", "c++")):
            return "cpp"
        return "general"