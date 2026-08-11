# To(と)/backend/engine/knowledgeRouter.py
"""

KnowledgeRouter
===============
役割: ユーザーのメッセージを見て「どのナレッジJSONを読み込むべきか」を決める。

設計方針:
  - ChatOrchestrator.calculate_score と同じ「キーワードスコアリング」方式を採用。
    決定的（同じ入力なら常に同じ出力）でデバッグしやすいことを優先し、
    LLMによる意味的分類はまだ導入しない。精度が足りなくなったら
    route() の中身だけを埋め込み検索 or LLM分類に差し替えられるよう、
    呼び出し側のインターフェース（route() の引数・戻り値）は変えない設計にする。

  - ドメイン定義（どのJSONが、どんなキーワードに反応するか）はコードに
    書かず registry.json に外出しする。JSON倉庫が増えるたびにコードを
    書き換えなくて済むようにするため。

使い方:
    router = KnowledgeRouter("knowledge/registry.json")
    json_paths = await router.route("動画を追加するボタンを作って")
    # -> ["video_editor/video_import.json", "electron/ipc.json", "electron/dialog.json"]


役割:
  ユーザーのメッセージを見て「どのナレッジファイル（JSON/MD）を読み込むべきか」を決める。

改善ポイント（元コードからの主な変更）:
  - 文字正規化を強化（NFKC + 小文字化 + 全角空白の吸収）
  - print -> logging
  - Markdown frontmatterの簡易パースを少し堅牢化
  - 同点時の安定ソート（score降順 + name昇順）
  - domain名衝突に備えて内部キーを導入（relative_pathを優先）
  - routeを同期関数化（必要ならroute_asyncで互換）
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
<<<<<<< HEAD
# from engine.KnowledgeLoader import KnowledgeLoader
=======

>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDomain:
    name: str
    description: str
    file_paths: list[str]
    keywords: list[str]
    searchable_text: str = ""
    weight: int = 1
    domain_id: str = ""


@dataclass
class RouteResult:
    file_paths: list[str]
    matched_domains: list[str]
    scores: dict[str, int] = field(default_factory=dict)  # domain_id -> score

    def __iter__(self):
        """
        【重要】このオブジェクト自体を反復可能（Iterable）にします。
        これにより、呼び出し側で `for path in route_result:` や `list(route_result)` と
        書かれた場合、自動的に `file_paths` の中身を安全にループします。
        """
        return iter(self.file_paths)

    @property
    def matched_files(self) -> list[str]:
        """
        オーケストレーター側が `route_result.matched_files` を参照しに来た場合、
        安全に `file_paths` を返すためのエイリアスプロパティです。
        """
        return self.file_paths
class KnowledgeRouter:
    def __init__(self, knowledge_dir: str, threshold: int = 1, top_k: int | None = None):
        self.knowledge_dir = Path(knowledge_dir)
        self.threshold = threshold
        self.top_k = top_k
        self.domains: list[KnowledgeDomain] = []
        self._load_knowledge_files()

    # ---------------------------
    # Public API
    # ---------------------------
    def reload(self) -> None:
        logger.info("🔄 [Router] ナレッジファイルを再読み込みします...")
        self._load_knowledge_files()

    def route(self, message: str, signals: dict[str, Any] | None = None) -> RouteResult:
        """
        同期版ルーティング。
        """
        normalized_message = self._normalize_text(message or "")
        scores: dict[str, int] = {}
        name_map: dict[str, str] = {}  # domain_id -> display name

        for domain in self.domains:
            score = self._score_domain(normalized_message, domain)

            # 文脈ボーナス
            if signals and signals.get("active_context") in (domain.name, domain.domain_id):
                score += domain.weight

            scores[domain.domain_id] = score
            name_map[domain.domain_id] = domain.name

        # 閾値以上 + 安定ソート（score desc, name asc）
        ranked = [
            d for d in self.domains
            if scores.get(d.domain_id, 0) >= self.threshold
        ]
        ranked.sort(key=lambda d: (-scores[d.domain_id], d.name))

        if self.top_k is not None:
            ranked = ranked[: self.top_k]

        # file_pathsを重複排除しつつ順序保持
        file_paths: list[str] = []
        seen = set()
        for domain in ranked:
            for p in domain.file_paths:
                if p not in seen:
                    seen.add(p)
                    file_paths.append(p)

        return RouteResult(
            file_paths=file_paths,
            matched_domains=[d.name for d in ranked],
            scores={d.domain_id: scores[d.domain_id] for d in ranked},
        )

    async def route_async(self, message: str, signals: dict[str, Any] | None = None) -> RouteResult:
        """
        互換用asyncラッパー（既存呼び出しを壊したくない場合）。
        """
        return self.route(message, signals)

    # ---------------------------
    # Internal loading
    # ---------------------------
    def _load_knowledge_files(self) -> None:
        if not self.knowledge_dir.exists():
            logger.warning("⚠️ [Router] ナレッジディレクトリが存在しません: %s", self.knowledge_dir)
            self.domains = []
            return

        self.domains = []

        for file_path in self.knowledge_dir.rglob("*"):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if suffix == ".json":
                self._parse_json_domain(file_path)
            elif suffix in (".md", ".mdx"):
                self._parse_markdown_frontmatter(file_path)

        logger.info("📁 [Router] 登録ドメイン数: %d", len(self.domains))

    def _parse_json_domain(self, file_path: Path) -> None:
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            name = data.get("name")
            keywords = data.get("keywords")
            if not isinstance(name, str) or not isinstance(keywords, list):
                return

            keywords = [str(k).strip() for k in keywords if str(k).strip()]
            if not keywords:
                return

            rel = str(file_path.relative_to(self.knowledge_dir))
            domain = KnowledgeDomain(
                name=name.strip(),
                description=str(data.get("description", "")),
                file_paths=[rel],
                keywords=keywords,
                weight=self._safe_int(data.get("weight", 1), default=1),
                domain_id=rel,  # pathベースで一意性を確保
            )
            self.domains.append(domain)

        except Exception as e:
            logger.warning("⚠️ [Router] JSON読み込みエラー (%s): %s", file_path, e)

    def _parse_markdown_frontmatter(self, file_path: Path) -> None:
        try:
            content = file_path.read_text(encoding="utf-8")
            # 先頭frontmatterのみ対象
            match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
            if not match:
                return

            frontmatter_text = match.group(1)
            metadata = self._parse_simple_frontmatter(frontmatter_text)

            name = metadata.get("name")
            keywords = metadata.get("keywords")
            if not isinstance(name, str) or not isinstance(keywords, list):
                return

            keywords = [str(k).strip() for k in keywords if str(k).strip()]
            if not keywords:
                return

            rel = str(file_path.relative_to(self.knowledge_dir))
            domain = KnowledgeDomain(
                name=name.strip(),
                description=str(metadata.get("description", "")),
                file_paths=[rel],
                keywords=keywords,
                weight=self._safe_int(metadata.get("weight", 1), default=1),
                domain_id=rel,
            )
            self.domains.append(domain)

        except Exception as e:
            logger.warning("⚠️ [Router] Markdown読み込みエラー (%s): %s", file_path, e)

    # ---------------------------
    # Internal utils
    # ---------------------------
    def _normalize_text(self, text: str) -> str:
        # Unicode正規化 + lower + 全角空白吸収 + 連続空白圧縮
        t = unicodedata.normalize("NFKC", text).lower()
        t = t.replace("\u3000", " ")
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _score_domain(self, normalized_message: str, domain: KnowledgeDomain) -> int:
        score = 0
        for kw in domain.keywords:
            nkw = self._normalize_text(kw)
            if nkw and nkw in normalized_message:
                score += domain.weight
        return score

    def _safe_int(self, value: Any, default: int = 1) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _parse_simple_frontmatter(self, text: str) -> dict[str, Any]:
        """
        依存なしの簡易frontmatterパーサ。
        対応:
          - key: value
          - keywords: [a, b, c]
          - keywords:
              - a
              - b
        """
        metadata: dict[str, Any] = {}
        lines = text.splitlines()

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line.strip() or line.strip().startswith("#"):
                i += 1
                continue

            if ":" not in line:
                i += 1
                continue

            key, raw_value = line.split(":", 1)
            key = key.strip()
            raw_value = raw_value.strip()

            # ブロックリスト形式
            if raw_value == "":
                items = []
                j = i + 1
                while j < len(lines):
                    l2 = lines[j].strip()
                    if l2.startswith("- "):
                        items.append(l2[2:].strip().strip("'\""))
                        j += 1
                    else:
                        break
                metadata[key] = items if items else ""
                i = j
                continue

            # インラインリスト形式 [a, b]
            if raw_value.startswith("[") and raw_value.endswith("]"):
                inner = raw_value[1:-1].strip()
                if inner:
                    metadata[key] = [x.strip().strip("'\"") for x in inner.split(",")]
                else:
                    metadata[key] = []
            else:
                v = raw_value.strip("'\"")
                metadata[key] = int(v) if v.isdigit() else v

            i += 1

        return metadata


# ---------------------------------------------------------------------------
# 動作確認用デモ
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    async def _demo():
        base_dir = Path("test_knowledge")
        base_dir.mkdir(exist_ok=True)
        (base_dir / "shaders").mkdir(exist_ok=True)

        with open(base_dir / "shaders" / "noodle.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "name": "noodle_pattern",
                    "keywords": ["ナルト", "渦巻き", "柄", "ラーメン"],
                    "weight": 2,
                },
                f,
                ensure_ascii=False,
            )

        with open(base_dir / "shaders" / "fabric.md", "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write("name: fabric_material\n")
            f.write("keywords:\n")
            f.write("  - 服\n")
            f.write("  - 布\n")
            f.write("  - 質感\n")
            f.write("  - マット\n")
            f.write("weight: 2\n")
            f.write("---\n")
            f.write("# 布の質感の作り方\nここでは布の質感を説明します。\n")

        router = KnowledgeRouter(knowledge_dir="test_knowledge")
        print(f"📁 登録されたドメイン数: {len(router.domains)}")

        test_messages = [
            "ラーメンのナルトみたいな柄にして！",
            "洋服っぽい　マットな質感がいいな",  # 全角空白混在
            "金属みたいなテカテカにして",
        ]

        for msg in test_messages:
            result = router.route(msg)
            print(f"\n📨 ユーザー入力: 「{msg}」")
            if result.file_paths:
                print(" 🎯 ピンポイントで情報を発見しました！")
                print(f"   ▶ 読み込むファイル: {result.file_paths}")
                print(f"   ▶ 関連ドメイン: {result.matched_domains}")
                print(f"   ▶ スコア内訳(domain_id基準): {result.scores}")
            else:
                print(" 🤷 該当する知識が見つかりませんでした。")

    asyncio.run(_demo())