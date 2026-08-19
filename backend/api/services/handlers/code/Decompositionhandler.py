# backend/api/services/handlers/code/Decompositionhandler.py
from __future__ import annotations

import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from api.services.handlers.base_handler import BaseHandler
from api.services.inspectors.IntentInSpector import IntentInspector

from plugins.line_formatter.formatters.js_formatter import JsFormatter


class DecompositionHandler(BaseHandler):
    """
    DecompositionHandler
    

    プロジェクト・コードの「分解」を担当するHandler。

    主な役割
    ------------------------------------------------------------
    1. ユーザー入力からIntentを確認する
    2. <script>タグを抽出する
    3. 複数の<script>を個別のJSとして扱う
    4. JsFormatterによる安全な整形を行う
    5. ScriptDownloadBlockを生成する
    6. フォルダー構成（tree形式）を検知し、
       ProjectTreeBlock / FileDownloadBlockを生成する
       ※ set.pyのコア解析ロジックを移植（サーバーへの書き込みは行わない）

    ChatOrchestratorから見ると、

        ChatOrchestrator
              ↓
        DecompositionHandler
              ↓
        ┌─────────────┬─────────────┐
        script分解      tree構成分解
        ↓                ↓
        JS files         project structure
        (ダウンロード形式で返す。サーバーには保存しない)

    

    重要な注意（実装ノート）
    ------------------------------------------------------------
    ・tree構成のパースには「祖先ディレクトリ名のスタック」方式を採用している。
      旧実装（Path(*stack)ベース）には、3階層目以降でrootパスが
      混入したり祖先ディレクトリ名を見失ったりするバグがあったため、
      dir_stackへ「これまでの祖先ディレクトリ名のみ」を積み、
      depthに合わせて末尾を切り詰める方式に変更している。

    ・チャット入力欄側で改行(\\n)が失われ、tree構成が1行に
      フラット化されて届くケースがある(実運用で確認済み)。
      この場合は誤ったroot_name等を生成してしまうため、
      パースを試みる前に検知し、ユーザーへ再送を促す。
    
    """

    # ===
    # Python雛形テンプレート（set.pyから最小限を移植）
    # ===

    PYTHON_TEMPLATES: Dict[str, str] = {
        "__init__.py": '''"""
Package initialization.
"""
''',
        "main.py": '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py

アプリケーションのエントリーポイント。
"""


def main() -> None:
    print("Application started.")


if __name__ == "__main__":
    main()
''',
    }

    # tree記号を含む行を検出する正規表現(1行ずつのパース用)
    _TREE_PREFIX_PATTERN = re.compile(
        r"^(?P<prefix>(?:│   |    |│  |   )*)"
        r"(?P<branch>[├└]──\s*)?"
        r"(?P<name>.+)$"
    )

    # tree形式かどうかの一次判定用
    _TREE_HINT_PATTERN = re.compile(
        r"[│├└]──|^\s*[\w\-.]+/\s*$",
        re.MULTILINE,
    )

    _TREE_KEYWORDS = [
        "フォルダー構成",
        "フォルダ構成",
        "ディレクトリ構成",
        "プロジェクト構造",
        "プロジェクト構成",
    ]

    # ===
    # 初期化
    # ===

    def __init__(self):
        super().__init__()

        # IntentInspectorで検出されたモード（デバッグ用の生値）
        self.detected_mode: Optional[str] = None

        # 最後に抽出したscript数
        self.last_script_count: int = 0

        # 最後に生成したファイル一覧
        self.last_generated_files: List[str] = []

    # ===
    # Message → text
    # ===

    def _get_text(self, message: Any) -> str:
        """
        ChatRequest / dict / str / その他の入力を
        安全に文字列へ変換する。
        """

        if isinstance(message, str):
            return message

        if isinstance(message, dict):
            value = message.get(
                "message",
                message.get(
                    "text",
                    message.get(
                        "content",
                        "",
                    ),
                ),
            )

            if value:
                return str(value)

            return str(message)

        # ChatRequestなど
        if hasattr(message, "message"):
            value = getattr(message, "message", None)

            if value is not None:
                return str(value)

        if hasattr(message, "text"):
            value = getattr(message, "text", None)

            if value is not None:
                return str(value)

        if hasattr(message, "content"):
            value = getattr(message, "content", None)

            if value is not None:
                return str(value)

        return str(message)

    # ===
    # IntentInspector
    # ===

    def _inspect_intent(self, text: str) -> Dict[str, Any]:
        """
        IntentInspectorによる意図解析。

        IntentInspector自身に判定を集約し、
        DecompositionHandler側では必要最小限の補助判定だけ行う。
        """

        try:
            inspector = IntentInspector(text)
            result = inspector.inspect()

            if not isinstance(result, dict):
                return {}

            self.detected_mode = result.get("mode")

            return result

        except Exception as e:
            print(
                f" [DecompositionHandler] "
                f"IntentInspectorでエラー: {e}",
                flush=True,
            )

            traceback.print_exc()

            return {}

    # ===
    # script判定
    # ===

    def _contains_script_request(self, text: str) -> bool:
        """
        <script>関連要求かどうかを判定する。

        IntentInspectorが主判定。
        ここではフォールバックとして使用する。
        """

        lower = text.lower()

        # 実際のscriptタグ
        if "<script" in lower:
            return True

        # scriptという単語
        if "script" in lower:
            return True

        return False

    # ===
    # tree構成判定
    # ===

    def _looks_like_tree_structure(self, text: str) -> bool:
        """
        フォルダー構成（tree形式 / 単純パス列挙）かどうかを判定する。

        優先度:
            1. tree記号 (│ ├ └ ── ) の存在
            2. 「api/」のようなスラッシュ終わりの行が複数ある
            3. 「フォルダー構成」等のキーワード
        """

        if self._TREE_HINT_PATTERN.search(text):
            return True

        if any(keyword in text for keyword in self._TREE_KEYWORDS):
            return True

        # スラッシュ終わりの行が2つ以上あれば構成っぽいと判定
        slash_lines = [
            line
            for line in text.splitlines()
            if line.strip().endswith("/")
        ]

        if len(slash_lines) >= 2:
            return True

        return False

    # ===
    # フラット化（改行消失）検知
    # ===

    def _looks_flattened(self, text: str) -> bool:
        """
        tree記号は複数あるのに実際の改行(\\n)がほぼ無い場合、
        フロント側で改行が失われた「1行に潰れたtree構成」だと判定する。

        この状態でパースを強行すると、ユーザーの発言文まるごとが
        root_nameになる等、致命的に誤った構造を生成してしまうため、
        ここで検知して安全側に倒す。
        """

        marker_count = text.count("├──") + text.count("└──")

        if marker_count < 3:
            return False

        newline_count = text.count("\n")

        # markerの数に対して改行が半分未満しか無ければフラット化とみなす
        return newline_count < (marker_count // 2)

    # ===
    # can_handle
    # ===

    async def can_handle(self, message: Any) -> bool:
        """
        このHandlerが入力を処理できるか判定する。

        ChatOrchestratorではcalculate_score()が優先されるが、
        BaseHandler互換のためcan_handleも実装する。
        """

        text = self._get_text(message)

        analysis = self._inspect_intent(text)

        # IntentInspectorが明示的に
        # DecompositionHandlerを指定した場合
        forced_handler = analysis.get(
            "forced_handler"
        )

        if forced_handler == "DecompositionHandler":
            return True

        # script関連
        if self._contains_script_request(text):
            return True

        # tree構成関連
        if self._looks_like_tree_structure(text):
            return True

        return False

    # ===
    # calculate_score
    # ===

    async def calculate_score(
        self,
        message: Any,
        signals: Optional[dict] = None,
    ) -> int:
        """
        ChatOrchestrator用のスコア計算。

        重要:
        IntentInspectorが

            mode = script_extraction / project_structure
            score = 100
            forced_handler = DecompositionHandler

        を返した場合、その判断を最優先する。
        """

        text = self._get_text(message)
        lower = text.strip().lower()

        analysis = self._inspect_intent(text)

        # -----------------------------------------------------
        # IntentInspectorの強制Handler
        # -----------------------------------------------------

        forced_handler = analysis.get(
            "forced_handler"
        )

        if forced_handler == "DecompositionHandler":
            mode = analysis.get("mode")

            self.detected_mode = mode

            score = analysis.get("score", 100)

            try:
                return int(score)
            except (TypeError, ValueError):
                return 100

        # -----------------------------------------------------
        # 別Handlerが明示されている場合
        # -----------------------------------------------------

        if forced_handler:
            return 0

        # -----------------------------------------------------
        # script_extraction
        # -----------------------------------------------------

        if analysis.get("mode") == "script_extraction":
            self.detected_mode = "script_extraction"

            score = analysis.get("score", 100)

            try:
                return int(score)
            except (TypeError, ValueError):
                return 100

        # -----------------------------------------------------
        # project_structure（tree構成）
        # -----------------------------------------------------

        if analysis.get("mode") == "project_structure":
            self.detected_mode = "project_structure"

            score = analysis.get("score", 100)

            try:
                return int(score)
            except (TypeError, ValueError):
                return 100

        # -----------------------------------------------------
        # 実際のscriptタグ
        # -----------------------------------------------------

        if "<script" in lower:
            return 90

        # -----------------------------------------------------
        # script + JS
        # -----------------------------------------------------

        if (
            "script" in lower
            and (
                "js" in lower
                or "javascript" in lower
            )
        ):
            return 90

        # -----------------------------------------------------
        # 抽出要求
        # -----------------------------------------------------

        extraction_words = [
            "抽出",
            "取り出して",
            "読み取って",
            "分離して",
            "分けて",
        ]

        if (
            "script" in lower
            and any(
                word in lower
                for word in extraction_words
            )
        ):
            return 90

        # -----------------------------------------------------
        # JS生成
        # -----------------------------------------------------

        if (
            "jsを作って" in lower
            or "jsを生成" in lower
            or "javascriptを作って" in lower
            or "javascriptを生成" in lower
        ):
            return 80

        # -----------------------------------------------------
        # tree構成（フォールバック判定）
        # -----------------------------------------------------

        if self._looks_like_tree_structure(text):
            self.detected_mode = "project_structure"
            return 85

        return 0

    # ===
    # <script>抽出
    # ===

    def _extract_scripts(
        self,
        text: str,
    ) -> List[str]:
        """
        HTML等から<script>タグ内部だけを抽出する。

        外部script:

            <script src="..."></script>

        は現時点ではコードとして抽出しない。

        将来的にsrc解析へ拡張可能。
        """

        pattern = re.compile(
            r"<script\b[^>]*>"
            r"(.*?)"
            r"</script\s*>",
            re.DOTALL | re.IGNORECASE,
        )

        matches = pattern.findall(text)

        scripts: List[str] = []

        for script in matches:
            clean = script.strip()

            if not clean:
                continue

            scripts.append(clean)

        return scripts

    # ===
    # scriptの種類を判定
    # ===

    def _extract_script_metadata(
        self,
        text: str,
    ) -> List[Dict[str, Any]]:
        """
        scriptタグごとの簡易メタ情報を作る。

        現時点では、

        - index
        - code
        - src
        - inline

        を保持する。

        """

        pattern = re.compile(
            r"<script\b([^>]*)>"
            r"(.*?)"
            r"</script\s*>",
            re.DOTALL | re.IGNORECASE,
        )

        results: List[Dict[str, Any]] = []

        matches = pattern.findall(text)

        for index, (attributes, code) in enumerate(
            matches,
            start=1,
        ):
            attr_text = attributes.strip()
            code_text = code.strip()

            src_match = re.search(
                r'\bsrc\s*=\s*["\']([^"\']+)["\']',
                attr_text,
                re.IGNORECASE,
            )

            src = (
                src_match.group(1)
                if src_match
                else None
            )

            results.append(
                {
                    "index": index,
                    "code": code_text,
                    "src": src,
                    "inline": src is None,
                }
            )

        return results

    # ===
    # JS整形
    # ===

    async def _format_js(
        self,
        code: str,
    ) -> Tuple[str, str]:
        """
        JsFormatterでJSを整形する。

        Formatterが失敗しても、生コードを返す。
        """

        metrics_msg = ""

        try:
            formatter = JsFormatter()

            clean_code = await formatter.format(
                code
            )

            if hasattr(
                formatter,
                "get_metrics",
            ):
                metrics = formatter.get_metrics()

                if metrics:
                    corrections = getattr(
                        metrics,
                        "corrections_made",
                        0,
                    )

                    metrics_msg = (
                        f"✨ JsFormatterが "
                        f"{corrections}箇所のコード揺れを"
                        f"自動修正しました"
                    )

            return clean_code, metrics_msg

        except Exception as e:
            print(
                f" [DecompositionHandler] "
                f"JsFormatter失敗: {e}",
                flush=True,
            )

            return (
                code,
                " コード自動整形はスキップされました",
            )

    # ===
    # ファイル名生成（JS）
    # ===

    def _build_file_name(
        self,
        index: int,
        total: int,
    ) -> str:
        """
        scriptから生成するJSファイル名。

        1つだけなら app.js。
        複数なら script_001.js の形式。
        """

        if total == 1:
            return "app.js"

        return f"script_{index:03d}.js"

    # ===
    # ScriptDownloadBlock生成
    # ===

    def _build_script_block(
        self,
        file_name: str,
        code: str,
        index: int,
    ) -> Dict[str, Any]:
        """
        フロントエンド用ScriptDownloadBlockを生成する。
        """

        return {
            "type": "ScriptDownloadBlock",
            "props": {
                "fileName": file_name,
                "code": code,
                "index": index,
            },
        }

    # ===
    # ここから: フォルダー構成（tree）解析ロジック
    # set.pyのコア部分を移植（サーバーへの書き込みは一切行わない）
    #
    # 【重要】祖先ディレクトリ名は dir_stack に「rootを含まず」積む。
    # depthに応じて末尾を切り詰めてから relative パスを組み立てるため、
    # 旧実装で発生していた「root/collectors/github/... のようにroot
    # が二重に混入する」「3階層目以降で祖先ディレクトリを見失い、
    # ファイルがrootの直下に飛び出す」というバグを回避できる。
    # ===

    def _normalize_tree_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        lines = []

        for line in text.split("\n"):
            stripped = line.strip()

            if stripped.startswith("```"):
                continue

            if not stripped:
                continue

            lines.append(line.rstrip())

        return "\n".join(lines)

    def _split_comment(self, name: str) -> Tuple[str, str]:
        if "#" not in name:
            return name.strip(), ""

        path_part, comment = name.split("#", 1)

        return path_part.strip(), comment.strip()

    def _parse_tree(self, text: str) -> Dict[str, Any]:
        """
        tree形式のテキストを解析する。

        戻り値:
            {
                "root_name": str,
                "entries": [
                    {"path": str, "is_dir": bool, "comment": str, "depth": int},
                    ...
                ],
            }
        """

        text = self._normalize_tree_text(text)

        if not text:
            raise ValueError("フォルダー構成が空です。")

        root_name = "root"
        entries: List[Dict[str, Any]] = []

        # 祖先ディレクトリ名のみを保持するスタック（rootは含めない）
        dir_stack: List[str] = []

        first_valid_line = True

        for raw_line in text.splitlines():
            if not raw_line.strip():
                continue

            match = self._TREE_PREFIX_PATTERN.match(raw_line)

            if not match:
                continue

            prefix = match.group("prefix") or ""
            raw_name = match.group("name").strip()

            name, comment = self._split_comment(raw_name)
            name = name.strip()

            if not name:
                continue

            # -------------------------------------------------
            # root判定（最初の有効行）
            # -------------------------------------------------

            if first_valid_line:
                first_valid_line = False

                if name.endswith("/"):
                    name = name[:-1]

                root_name = name

                entries.append(
                    {"path": "", "is_dir": True, "comment": comment, "depth": 0}
                )

                continue

            # -------------------------------------------------
            # depth: 1 = rootの直下
            # -------------------------------------------------

            depth = (len(prefix) // 4) + 1

            is_dir = name.endswith("/")

            if name.endswith("/"):
                name = name[:-1]

            # 祖先を depth-1 個だけ残して切り詰める
            del dir_stack[depth - 1:]

            relative = "/".join(dir_stack + [name])

            entries.append(
                {
                    "path": relative,
                    "is_dir": is_dir,
                    "comment": comment,
                    "depth": depth,
                }
            )

            if is_dir:
                dir_stack.append(name)

        return {"root_name": root_name, "entries": entries}

    def _parse_simple_paths(self, text: str) -> Dict[str, Any]:
        """
        tree形式として解析できなかった場合のフォールバック。

            api/
            api/routes/
            api/main.py

        のような単純列挙にも対応する。
        """

        root_name = "root"
        entries: List[Dict[str, Any]] = []

        lines = self._normalize_tree_text(text).splitlines()

        root_found = False

        for line in lines:
            line = line.strip()

            if not line:
                continue

            name, comment = self._split_comment(line)
            name = name.strip()

            if not name:
                continue

            if not root_found:
                candidate = name[:-1] if name.endswith("/") else name

                if candidate.lower() in ("root", "root:"):
                    root_name = "root"
                    entries.append(
                        {"path": "", "is_dir": True, "comment": "", "depth": 0}
                    )
                    root_found = True
                    continue

            is_dir = name.endswith("/")

            if is_dir:
                name = name[:-1]

            entries.append(
                {"path": name, "is_dir": is_dir, "comment": comment, "depth": 1}
            )

        if not entries:
            raise ValueError("有効なパスを解析できませんでした。")

        return {"root_name": root_name, "entries": entries}

    def _parse_structure(self, text: str) -> Dict[str, Any]:
        try:
            structure = self._parse_tree(text)

            if len(structure["entries"]) > 1:
                return structure

        except Exception:
            pass

        return self._parse_simple_paths(text)

    def _get_python_template(self, path: str) -> Optional[str]:
        file_name = Path(path).name

        if file_name in self.PYTHON_TEMPLATES:
            return self.PYTHON_TEMPLATES[file_name]

        if file_name.endswith(".py"):
            return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
{file_name}

自動生成されたPythonファイル。

TODO:
    このファイルの責務を実装する。
"""


def main() -> None:
    pass


if __name__ == "__main__":
    main()
'''

        return None

    def _build_file_content(self, entry: Dict[str, Any]) -> str:
        path = entry["path"]

        template = self._get_python_template(path)

        if template is not None:
            header = ""

            if entry.get("comment"):
                header = f"# [構成情報] {entry['comment']}\n\n"

            return header + template

        if path.endswith(".json"):
            return "{}\n"

        if path.endswith(".yaml") or path.endswith(".yml"):
            return "# 自動生成されたYAMLファイル\n"

        if path.endswith(".md"):
            return (
                f"# {Path(path).stem}\n\n"
                f"<!-- 自動生成されたファイル -->\n"
            )

        if path.endswith(".ts"):
            return f"// {Path(path).name}\n// 自動生成されたTypeScriptファイル\n"

        if Path(path).name == ".gitkeep":
            return ""

        if Path(path).name == ".env":
            return (
                "# ====\n"
                "# Environment Variables\n"
                "# ====\n"
                "# API_KEY=\n"
                "# DATABASE_URL=\n"
            )

        if path.endswith(".db"):
            return ""

        return ""

    # ===
    # ProjectTreeBlock / FileDownloadBlock生成
    # ===

    def _build_tree_block(
        self,
        root_name: str,
        entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        フロントエンド用ProjectTreeBlockを生成する。

        注意:
            ProjectTreeBlock.jsxの実装を未確認のため、
            props形状は暫定。実物と異なる場合は要調整。
        """

        tree_entries = [
            {
                "path": entry["path"],
                "isDir": entry["is_dir"],
                "comment": entry.get("comment", ""),
            }
            for entry in entries
            if entry["path"]  # rootそのものは除外
        ]

        return {
            "type": "ProjectTreeBlock",
            "props": {
                "rootName": root_name,
                "entries": tree_entries,
            },
        }

    def _build_file_download_block(
        self,
        file_name: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        フロントエンド用FileDownloadBlockを生成する。

        注意:
            FileDownloadBlock.jsxの実装を未確認のため、
            props形状は暫定（fileName / content）。
            実物と異なる場合は要調整。
        """

        return {
            "type": "FileDownload",
            "props": {
                "fileName": file_name,
                "content": content,
            },
        }

    # ===
    # tree構成のhandle本体
    # ===

    async def _handle_project_structure(
        self,
        text: str,
        intent_mode: Optional[str],
    ) -> Tuple[str, Any]:
        """
        フォルダー構成（tree形式）を解析し、
        ProjectTreeBlock + FileDownloadBlock群を返す。

        重要:
            サーバーのファイルシステムには一切書き込まない。
            全てレスポンスのblocksに内包してフロントへ渡す。
        """

        # -----------------------------------------------------
        # 改行消失（フラット化）検知
        # -----------------------------------------------------

        if self._looks_flattened(text):
            return (
                "text",
                {
                    "message": (
                        "フォルダー構成の改行が失われているようです"
                        "（1行につながった状態で届いています）。\n\n"
                        "このままだと誤った構造で解析してしまうため、"
                        "お手数ですが以下のいずれかで再送してください。\n"
                        "- 構成全体をコードブロック（```で囲む）にして送る\n"
                        "- .txtファイルとして添付する\n\n"
                        "※ チャット入力欄側で改行が送信時に失われている"
                        "可能性があります。入力欄が複数行対応"
                        "（textarea）になっているかも確認してみてください。"
                    ),
                    "blocks": [],
                },
            )

        # -----------------------------------------------------
        # 解析
        # -----------------------------------------------------

        try:
            structure = self._parse_structure(text)

        except Exception as e:
            return (
                "text",
                {
                    "message": (
                        "フォルダー構成の解析に失敗しました。\n"
                        f"原因: {e}"
                    ),
                    "blocks": [],
                },
            )

        root_name = structure["root_name"]
        entries = structure["entries"]

        file_entries = [e for e in entries if not e["is_dir"] and e["path"]]
        dir_entries = [e for e in entries if e["is_dir"] and e["path"]]

        blocks: List[Dict[str, Any]] = []

        # ツリー全体のプレビュー
        blocks.append(self._build_tree_block(root_name, entries))

        # ファイルごとのダウンロードブロック
        generated_files: List[str] = []

        for entry in file_entries:
            content = self._build_file_content(entry)

            blocks.append(
                self._build_file_download_block(
                    file_name=entry["path"],
                    content=content,
                )
            )

            generated_files.append(entry["path"])

        self.last_generated_files = generated_files

        # tree構成として処理した場合は、表示上のモードは
        # 常に project_structure に固定する
        # （IntentInspectorが script_extraction 等を誤検出していても
        #   ユーザーへの表示を混乱させないため）
        display_mode = "project_structure"

        message_text = (
            f"フォルダー構成を解析しました。\n\n"
            f"ルート: `{root_name}`\n"
            f"ディレクトリ数: {len(dir_entries)}\n"
            f"ファイル数: {len(file_entries)}"
        )

        message_text += f"\n\n検出モード: `{display_mode}`"

        if generated_files:
            message_text += (
                "\n\n生成ファイル:"
                + "".join(f"\n- `{name}`" for name in generated_files)
            )

        return (
            "ui_code",
            {
                "message": message_text,
                "blocks": blocks,
                "decomposition": {
                    "mode": display_mode,
                    "intent_mode": intent_mode,  # IntentInspectorの生の判定値（デバッグ用）
                    "root_name": root_name,
                    "file_count": len(file_entries),
                    "dir_count": len(dir_entries),
                    "generated_files": generated_files,
                },
            },
        )

    # ===
    # handle
    # ===

    async def handle(
        self,
        message: Any,
    ) -> Tuple[str, Any]:
        """
        DecompositionHandler本体。

        現在:
            <script> → JS分離 → ScriptDownloadBlock
            tree構成 → 構造解析 → ProjectTreeBlock + FileDownloadBlock
        """

        print(
            "📦 [DecompositionHandler] "
            "コード分解処理を開始します",
            flush=True,
        )

        try:
            # -------------------------------------------------
            # 1. 入力文字列化
            # -------------------------------------------------

            text = self._get_text(message)

            if not text.strip():
                return (
                    "text",
                    {
                        "message":
                            "処理対象のテキストがありません。",
                        "blocks": [],
                    },
                )

            # -------------------------------------------------
            # 2. Intent解析
            # -------------------------------------------------

            analysis = self._inspect_intent(text)

            mode = analysis.get(
                "mode"
            )

            self.detected_mode = mode

            print(
                "[DecompositionHandler] "
                f"mode={mode}",
                flush=True,
            )

            # -------------------------------------------------
            # 3. script抽出を試みる
            # -------------------------------------------------

            metadata = (
                self._extract_script_metadata(
                    text
                )
            )

            scripts = [
                item["code"]
                for item in metadata
                if item.get("inline")
                and item.get("code")
            ]

            self.last_script_count = len(
                scripts
            )

            # -------------------------------------------------
            # 4. scriptが無ければtree構成として処理
            # -------------------------------------------------

            if not scripts:
                if mode == "project_structure" or self._looks_like_tree_structure(text):
                    print(
                        "📦 [DecompositionHandler] "
                        "フォルダー構成として処理します",
                        flush=True,
                    )

                    return await self._handle_project_structure(
                        text,
                        mode,
                    )

                # ---------------------------------------------
                # scriptタグもtree構成も見つからない場合
                # ---------------------------------------------

                return (
                    "text",
                    {
                        "message": (
                            "送信されたテキストの中に "
                            "`<script>` タグやフォルダー構成が"
                            "見つかりませんでした。"
                        ),
                        "blocks": [],
                    },
                )

            print(
                f"📦 [DecompositionHandler] "
                f"{len(scripts)}個の<script>を検出",
                flush=True,
            )

            # -------------------------------------------------
            # 5. JS生成
            # -------------------------------------------------

            blocks: List[Dict[str, Any]] = []

            generated_files: List[str] = []

            total = len(scripts)

            for index, raw_code in enumerate(
                scripts,
                start=1,
            ):
                print(
                    f"✨ JS {index}/{total} を整形中...",
                    flush=True,
                )

                clean_code, metrics_msg = (
                    await self._format_js(
                        raw_code
                    )
                )

                file_name = self._build_file_name(
                    index,
                    total,
                )

                generated_files.append(
                    file_name
                )

                block = self._build_script_block(
                    file_name=file_name,
                    code=clean_code,
                    index=index,
                )

                # Formatterの結果をBlockへ付加
                if metrics_msg:
                    block["props"][
                        "metrics"
                    ] = metrics_msg

                blocks.append(block)

            self.last_generated_files = (
                generated_files
            )

            # -------------------------------------------------
            # 6. メッセージ生成
            # -------------------------------------------------

            if total == 1:
                message_text = (
                    "HTMLからJavaScriptコードを "
                    "1個抽出しました。"
                )
            else:
                message_text = (
                    f"HTMLからJavaScriptコードを "
                    f"{total}個抽出しました。"
                )

            if mode:
                message_text += (
                    f"\n\n検出モード: `{mode}`"
                )

            message_text += (
                "\n\n生成ファイル:"
                + "".join(
                    f"\n- `{name}`"
                    for name in generated_files
                )
            )

            # -------------------------------------------------
            # 7. UI Response
            # -------------------------------------------------

            content: Dict[str, Any] = {
                "message": message_text,

                "blocks": blocks,

                "decomposition": {
                    "mode": mode,
                    "script_count": total,
                    "generated_files":
                        generated_files,
                },
            }

            print(
                "✅ [DecompositionHandler] "
                f"処理完了: {generated_files}",
                flush=True,
            )

            return (
                "ui_code",
                content,
            )

        except Exception as e:
            traceback.print_exc()

            print(
                f"🚨 [DecompositionHandler] "
                f"処理失敗: {e}",
                flush=True,
            )

            return (
                "text",
                {
                    "message":
                        "処理中に"
                        f"エラーが発生しました: {e}",
                    "blocks": [],
                },
            )