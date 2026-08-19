"""
PromptBuilder
=
役割: KnowledgeLoader.load() の結果 + ユーザーのメッセージ + 常時適用ルールを
      1本のプロンプト文字列に組み立てて LLM に渡す。

設計のコア（知識非依存）:
  - 汎用化: PromptBuilderは特定のキー（rules, anti_patterns等）や
    ドメイン知識を一切ハードコードしません。
  - フォーマット駆動: JSON内に `sections` という配列があれば、
    その `style` (list, text, code等) に従ってMarkdownに変換します。
  - JSONフォールバック: `sections` 以外の未知のキー（dependencies等）は
    すべてそのまま純粋なJSON文字列として末尾にダンプします。
    これにより、将来どんなデータ構造が追加されてもコード修正は不要です。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .KnowledgeLoader import LoadResult, LoadedKnowledge


@dataclass
class PromptResult:
    text: str
    included_domains: list[str]
    dropped_domains: list[str] = field(default_factory=list)
    char_count: int = 0
    truncated: bool = False


class PromptBuilder:
    def __init__(
        self,
        global_rules_path: str | None = "knowledge/_global_rules.json",
        max_knowledge_chars: int = 12000,
    ):
        self.global_rules_path = Path(global_rules_path) if global_rules_path else None
        self.max_knowledge_chars = max_knowledge_chars
        self._global_rules_cache: tuple[float, list[str]] | None = None

    # -----------------------------------------------------------------
    # 常時適用ルールの読み込み
    # -----------------------------------------------------------------
    def _load_global_rules(self) -> list[str]:
        if self.global_rules_path is None or not self.global_rules_path.exists():
            return []

        mtime = self.global_rules_path.stat().st_mtime
        if self._global_rules_cache and self._global_rules_cache[0] == mtime:
            return self._global_rules_cache[1]

        try:
            with self.global_rules_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            rules = data.get("rules", []) if isinstance(data, dict) else list(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f" [PromptBuilder] global_rules 読み込み失敗: {e}")
            rules = []

        self._global_rules_cache = (mtime, rules)
        return rules

    # -----------------------------------------------------------------
    # 知識1件を整形（ドメイン知識を一切持たない設計）
    # -----------------------------------------------------------------
    def _format_knowledge_item(self, item: LoadedKnowledge) -> str:
        lines = [f"## {item.domain_label}"]

        if item.description:
            lines.append(f"（{item.description}）")

        if item.content_type == "markdown":
            # Markdownならそのまま出力（責務1）
            lines.append(item.content or "")
            return "\n".join(lines)

        # JSONの処理（責務2: 構造に依存せず出力）
        content = item.content if isinstance(item.content, dict) else {}
        display = {k: v for k, v in content.items() if k != "description"}

        # 動的セクションの処理
        if "sections" in display and isinstance(display["sections"], list):
            sections = display.pop("sections")
            for sec in sections:
                title = sec.get("title", "")
                style = sec.get("style", "text")
                
                if title:
                    lines.append(f"### {title}")
                    
                # スタイルに応じたMarkdown化（知識ではなく表示形式のみを知っている）
                if style == "list" and isinstance(sec.get("items"), list):
                    for list_item in sec["items"]:
                        lines.append(f"- {list_item}")
                elif style == "text" and "content" in sec:
                    lines.append(str(sec["content"]))
                elif style == "code" and "code" in sec:
                    lang = sec.get("language", "")
                    lines.append(f"```{lang}\n{sec['code']}\n```")

        # sections以外の未知のキー（dependencies, pitfalls 等）はそのままJSONで出す
        if display:
            lines.append("```json")
            lines.append(json.dumps(display, ensure_ascii=False, indent=2))
            lines.append("```")

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # 知識セクション全体を組み立て、上限を超えたら末尾から間引く
    # -----------------------------------------------------------------
    def _build_knowledge_section(
        self, load_result: LoadResult
    ) -> tuple[str, list[str], list[str], bool]:
        formatted = [
            (item.domain_label, self._format_knowledge_item(item))
            for item in load_result.items
        ]

        included: list[str] = []
        dropped: list[str] = []
        blocks: list[str] = []
        total = 0
        truncated = False

        for label, text in formatted:
            block_len = len(text) + 2  # 区切りの改行分
            if total + block_len > self.max_knowledge_chars:
                truncated = True
                dropped.append(label)
                continue
            blocks.append(text)
            included.append(label)
            total += block_len

        if dropped:
            print(
                f" [PromptBuilder] 文字数上限 ({self.max_knowledge_chars}) を超えたため "
                f"{len(dropped)} 件を除外しました: {dropped}"
            )

        return "\n\n".join(blocks), included, dropped, truncated

    # -----------------------------------------------------------------
    # 本体
    # -----------------------------------------------------------------
    def build(
        self,
        user_message: str,
        load_result: LoadResult,
        signals: dict | None = None,
    ) -> PromptResult:
        knowledge_section, included, dropped, truncated = self._build_knowledge_section(
            load_result
        )
        global_rules = self._load_global_rules()

        parts = [
            "# ユーザーの指示",
            user_message.strip(),
        ]

        if knowledge_section:
            parts += ["", "# 参考知識（プロジェクト固有）", knowledge_section]

        if global_rules:
            rule_lines = "\n".join(f"- {r}" for r in global_rules)
            parts += ["", "# 常時適用ルール", rule_lines]

        if signals and signals.get("active_context"):
            parts += ["", f"# 直前の文脈: {signals['active_context']}"]

        if load_result.errors:
            print(f" [PromptBuilder] {len(load_result.errors)} 件の知識読み込みに失敗した状態でプロンプトを構築しました")

        text = "\n".join(parts)

        return PromptResult(
            text=text,
            included_domains=included,
            dropped_domains=dropped,
            char_count=len(text),
            truncated=truncated,
        )


# ---------------------------------------------------------------------------
# 動作確認用
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from KnowledgeLoader import LoadResult, LoadedKnowledge

    # テスト用のモックデータ
    mock_json_content = {
        "description": "動画編集画面のタイムライン",
        "sections": [
            {
                "title": "🎯 実装ルール",
                "style": "list",
                "items": ["React.memo を利用する", "状態管理はZustand"]
            },
            {
                "title": "🚫 アンチパターン",
                "style": "list",
                "items": ["useStateで現在位置を持つ", "毎フレームDOMを書き換える"]
            },
            {
                "title": "💻 実装例",
                "style": "code",
                "language": "tsx",
                "code": "const Cursor = () => <div />;"
            }
        ],
        "dependencies": {
            "framer-motion": "^10.0.0"
        },
        "performance_tips": [
            "Canvas APIの使用を検討"
        ]
    }

    item = LoadedKnowledge(
        path="video_editor/timeline.json",
        domain_label="video_editor/timeline",
        content_type="json",
        description=mock_json_content["description"],
        content=mock_json_content
    )

    load_result = LoadResult(items=[item])
    builder = PromptBuilder(global_rules_path=None)
    
    result = builder.build("タイムラインを実装して", load_result)
    print(result.text)