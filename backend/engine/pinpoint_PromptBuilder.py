"""
PromptBuilder
=============
役割: KnowledgeLoader.load() の結果 + ユーザーのメッセージ + 常時適用ルールを
      1本のプロンプト文字列に組み立てて LLM に渡す。

設計方針:
  - 「常時適用ルール（あなた専用ルール）」は Router のヒット有無に関係なく
    毎回注入する。knowledge/_global_rules.json という固定ファイルから読む。
    ドメイン知識と混ぜて Router のスコアリング対象にしてしまうと、
    たまたまキーワードが引っかからなかった時にプロジェクトの基本ルールごと
    抜け落ちる、という事故が起きるため、経路を分けている。

  - ドメイン知識は中身の構造に応じて整形する:
      - "rules": [...] を持つ場合 -> 箇条書きに変換（LLMにとって読みやすい）
      - それ以外 -> 素の JSON を出典ラベル付きでそのまま埋め込む
    schema を厳密に強制せず、あるものは活かし、無いものは JSON のまま出す
    という緩い方針。knowledge/ 配下の JSON フォーマットが将来揺れても壊れにくい。

  - プロンプトの知識セクションが肥大化した場合、黙って切り詰めるのではなく
    「何を落としたか」を warning として出す。デバッグ時に「なぜ急に精度が
    落ちたか分からない」を防ぐため。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# import KnowledgeRouter

from .Pinpoint_KnowledgeLoader import LoadResult, LoadedKnowledge

@dataclass
class PromptResult:
    text: str
    included_domains: list[str]
    dropped_domains: list[str] = field(default_factory=list)
    char_count: int = 0
    truncated: bool = False


class PromptBuilder:
    print("★★★★★ PromptBuilder Loaded ★★★★★")
    def __init__(
        self,
        global_rules_path: str | Path | None = "knowledge/_global_rules.json",
        max_knowledge_chars: int = 12000,
    ):
        self.global_rules_path = Path(global_rules_path) if global_rules_path else None
        self.max_knowledge_chars = max_knowledge_chars
        self._global_rules_cache: tuple[float, list[str]] | None = None

    # -----------------------------------------------------------------
    # 常時適用ルールの読み込み（mtimeキャッシュ。Loaderと同じ方式）
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
            print(f"⚠️ [PromptBuilder] global_rules 読み込み失敗: {e}")
            rules = []

        self._global_rules_cache = (mtime, rules)
        return rules

    # -----------------------------------------------------------------
    # 知識1件を整形
    # -----------------------------------------------------------------
    def _format_knowledge_item(self, item: LoadedKnowledge) -> str:
        content = item.content
        lines = [f"## {item.domain_label}"]

        if isinstance(content, dict) and "topic" in content:
            lines.append(f"（{content['topic']}）")

        if isinstance(content, dict) and isinstance(content.get("rules"), list):
            for rule in content["rules"]:
                lines.append(f"- {rule}")
            # rules 以外のキー（project_specific 等）も落とさず JSON で残す
            rest = {k: v for k, v in content.items() if k not in ("topic", "rules")}
            if rest:
                lines.append("```json")
                lines.append(json.dumps(rest, ensure_ascii=False, indent=2))
                lines.append("```")
        else:
            lines.append("```json")
            lines.append(json.dumps(content, ensure_ascii=False, indent=2))
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
                f"⚠️ [PromptBuilder] 文字数上限 ({self.max_knowledge_chars}) を超えたため "
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
            # LLM には投げず、開発者向けにログだけ残す
            print(f"⚠️ [PromptBuilder] {len(load_result.errors)} 件の知識読み込みに失敗した状態でプロンプトを構築しました")

        text = "\n".join(parts)

        return PromptResult(
            text=text,
            included_domains=included,
            dropped_domains=dropped,
            char_count=len(text),
            truncated=truncated,
        )


# ---------------------------------------------------------------------------
# 動作確認用: Router -> Loader -> PromptBuilder のフルパイプライン
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    from .Pinpoint_KnowledgeLoader import LoadResult, LoadedKnowledge
    async def _demo():
        base = Path(__file__).parent

        router = __import__("KnowledgeRouter").KnowledgeRouter(registry_path=base / "knowledge" / "registry.json")
        loader_ = __import__("KnowledgeLoader").KnowledgeLoader(base_dir=base / "knowledge")
        builder = PromptBuilder(global_rules_path=base / "knowledge" / "_global_rules.json")

        message = "ファイルダイアログの実装教えて"
        route_result = await router.route(message)
        load_result = await loader_.load(route_result.json_paths)
        prompt_result = builder.build(message, load_result)

        print("\n================ 最終プロンプト ================\n")
        print(prompt_result.text)
        print("\n==================================================")
        print(f"含まれたドメイン: {prompt_result.included_domains}")
        print(f"文字数: {prompt_result.char_count} / 切り詰め: {prompt_result.truncated}")

    asyncio.run(_demo())