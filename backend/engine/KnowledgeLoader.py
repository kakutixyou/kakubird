"""
KnowledgeLoader
===
役割:
  KnowledgeRouter.route() が返す file_paths を受け取り、実際のファイル内容を
  読み込んで PromptBuilder に渡せる形にする。

新Routerとの対応関係（重要な設計変更）:
  - 旧: registry.json が「ドメイン→ファイル」の対応表を別に持っていた。
  - 新: registry.json は廃止。knowledge_dir 配下の各ファイル自体が
        name / keywords / weight（ルーティング用メタデータ）と
        実際の知識内容を同じファイル内に持つ「自己記述」方式に変わった。
    そのため Loader は、読み込んだデータから「ルーティング専用フィールド」
    （name / keywords / weight）を取り除いた残りを「知識本体」として扱う。
    description はプロンプトの見出しとして使えるため content とは別に保持する。

  - .md / .mdx にも対応。frontmatter（--- で囲まれた部分）を取り除いた
    本文（Markdown文字列）がそのまま知識内容になる。Router 側の
    frontmatter パーサーとは違い、Loader は routing 用メタデータの厳密な
    パースは行わない（それは Router の責務。二重にロジックを持たせない）。
    frontmatter の有無だけを正規表現で判定し、本文を切り出す。

  - Router が sync 優先に変更されたことに合わせて load() も同期関数にした。
    ファイルI/Oはブロッキングでも軽量なので実利もある。既存の async 呼び出し
    を壊さないよう load_async() を互換ラッパーとして残す。

  - print ではなく logging を使用（Routerの変更と統一）。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# ルーティング専用フィールド。知識本体（プロンプトに載せる内容）からは除外する。
_ROUTING_ONLY_KEYS = {"name", "keywords", "weight"}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
_DESCRIPTION_LINE_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)


@dataclass
class LoadedKnowledge:
    path: str                  # knowledge_dir からの相対パス
    domain_label: str          # 拡張子を除いたパス。出典表示に使う
    content_type: str          # "json" | "markdown"
    description: str = ""      # あれば見出しとして使える
    content: Any = None        # json: メタデータを除いた dict / markdown: 本文文字列


@dataclass
class LoadError:
    path: str
    reason: str                 # "not_found" | "invalid_json" | "no_frontmatter" | "read_error"
    detail: str = ""


@dataclass
class LoadResult:
    items: list[LoadedKnowledge] = field(default_factory=list)
    errors: list[LoadError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def as_merged_dict(self) -> dict:
        """domain_label をキーにした単純マージ（簡易ヘルパー）。"""
        return {item.domain_label: item.content for item in self.items}


class KnowledgeLoader:

    def __init__(
            self,
            knowledge_dirs: list[str | Path],
            cache_enabled: bool = True
        ):

            self.knowledge_dirs = [
                Path(path).resolve()
                for path in knowledge_dirs
            ]

            self.cache_enabled = cache_enabled

            self._cache: dict[
                str,
                tuple[float, LoadedKnowledge]
            ] = {}

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def load(self, file_paths: list[str]) -> LoadResult:
        """
        file_paths: KnowledgeRouter.route(...).file_paths をそのまま渡す想定。
        """
        result = LoadResult()

        for rel_path in file_paths:
            item, error = self._read_one(rel_path)
            if item is not None:
                result.items.append(item)
                logger.info("📚 [Loader] 読み込み成功: %s", rel_path)
            if error is not None:
                result.errors.append(error)
                logger.warning(" [Loader] 読み込み失敗 (%s): %s - %s",
                                error.reason, rel_path, error.detail)

        return result

    async def load_async(self, file_paths: list[str]) -> LoadResult:
        """互換用asyncラッパー（既存の async 呼び出しを壊さないため）。"""
        return self.load(file_paths)

    def clear_cache(self) -> None:
        self._cache.clear()

    # -----------------------------------------------------------------
    # Internal: 1ファイルの読み込み
    # -----------------------------------------------------------------
    def _read_one(
        self,
        file_path: str
    ) -> tuple[LoadedKnowledge | None, LoadError | None]:

        # ---------------------------------------------------------
        # Routerから渡されたファイルパスをPathに変換
        #
        # Routerが、
        #
        # backend/engine/knowledge/example.json
        #
        # または、
        #
        # plugin/knowledge/python/example.json
        #
        # のようなパスを返す想定。
        #
        # knowledge_dirを1つに固定せず、
        # 渡されたパスを直接読み込む。
        # ---------------------------------------------------------
        abs_path = Path(file_path)

        # ---------------------------------------------------------
        # ファイルの存在確認
        # ---------------------------------------------------------
        if not abs_path.exists():

            return None, LoadError(
                path=file_path,
                reason="not_found",
                detail=f"ファイルが存在しません: {abs_path}"
            )

        # ---------------------------------------------------------
        # ファイル更新時刻を取得
        # キャッシュの有効性確認に使用
        # ---------------------------------------------------------
        try:

            mtime = abs_path.stat().st_mtime

        except OSError as e:

            return None, LoadError(
                path=file_path,
                reason="read_error",
                detail=str(e)
            )

        # ---------------------------------------------------------
        # キャッシュ確認
        #
        # 同じファイルを何度も読み込む場合、
        # ファイルが変更されていなければ再読み込みしない。
        # ---------------------------------------------------------
        if (
            self.cache_enabled
            and file_path in self._cache
        ):

            cached_mtime, cached_item = (
                self._cache[file_path]
            )

            if cached_mtime == mtime:

                return cached_item, None

        # ---------------------------------------------------------
        # 拡張子によって読み込み処理を分岐
        # ---------------------------------------------------------
        suffix = abs_path.suffix.lower()

        if suffix == ".json":

            item, error = self._read_json(
                abs_path,
                file_path
            )

        elif suffix in (".md", ".mdx"):

            item, error = self._read_markdown(
                abs_path,
                file_path
            )

        else:

            return None, LoadError(
                path=file_path,
                reason="read_error",
                detail=f"未対応の拡張子です: {suffix}"
            )

        # ---------------------------------------------------------
        # 正常に読み込めた場合はキャッシュへ保存
        # ---------------------------------------------------------
        if (
            item is not None
            and self.cache_enabled
        ):

            self._cache[file_path] = (
                mtime,
                item
            )

        return item, error

    def _domain_label(self, rel_path: str) -> str:
        p = Path(rel_path)
        return str(p.with_suffix(""))

    def _read_json(self, abs_path: Path, rel_path: str) -> tuple[LoadedKnowledge | None, LoadError | None]:
        try:
            with abs_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return None, LoadError(path=rel_path, reason="invalid_json", detail=str(e))
        except OSError as e:
            return None, LoadError(path=rel_path, reason="read_error", detail=str(e))

        if not isinstance(data, dict):
            content: Any = data
            description = ""
        else:
            description = str(data.get("description", ""))
            content = {k: v for k, v in data.items() if k not in _ROUTING_ONLY_KEYS}

        item = LoadedKnowledge(
            path=rel_path,
            domain_label=self._domain_label(rel_path),
            content_type="json",
            description=description,
            content=content,
        )
        return item, None

    def _read_markdown(self, abs_path: Path, rel_path: str) -> tuple[LoadedKnowledge | None, LoadError | None]:
        try:
            text = abs_path.read_text(encoding="utf-8")
        except OSError as e:
            return None, LoadError(path=rel_path, reason="read_error", detail=str(e))

        match = _FRONTMATTER_RE.match(text)
        if not match:
            # Router は frontmatter が無いファイルをそもそもドメイン登録しないため
            # 通常ここには来ないはずだが、直接パスを渡された場合の防御として扱う
            return None, LoadError(path=rel_path, reason="no_frontmatter",
                                    detail="frontmatter（--- ... ---）が見つかりません")

        frontmatter_text = match.group(1)
        body = text[match.end():].strip()

        desc_match = _DESCRIPTION_LINE_RE.search(frontmatter_text)
        description = desc_match.group(1).strip().strip("'\"") if desc_match else ""

        item = LoadedKnowledge(
            path=rel_path,
            domain_label=self._domain_label(rel_path),
            content_type="markdown",
            description=description,
            content=body,
        )
        return item, None


# ---------------------------------------------------------------------------
# 動作確認用
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    from pathlib import Path
    from KnowledgeRouter import KnowledgeRouter

    # ---------------------------------------------------------
    # プロジェクトルートを取得
    #
    # 例:
    # project/
    # ├── backend/
    # │   └── engine/
    # │       └── knowledge/
    # │           └── KnowledgeLoader.py
    # │
    # └── plugin/
    #     └── knowledge/
    #
    # KnowledgeLoader.pyから3階層上がると project/
    # ---------------------------------------------------------

    PROJECT_ROOT = Path(__file__).resolve().parents[3]

    backend_engine_knowledge = (
        PROJECT_ROOT
        / "backend"
        / "engine"
        / "knowledge"
    )

    plugin_knowledge = (
        PROJECT_ROOT
        / "plugin"
        / "knowledge"
    )

    # router = KnowledgeRouter(
    #     knowledge_dirs=[
    #         backend_engine_knowledge,
    #         plugin_knowledge
    #     ]
    # )

    loader = KnowledgeLoader(
        knowledge_dirs=[
            backend_engine_knowledge,
            plugin_knowledge
        ]
    )

    for msg in [
        "ラーメンのナルトみたいな柄にして！",
        "洋服っぽい　マットな質感がいいな"
    ]:

        route_result = router.route(msg) # type: ignore

        load_result = loader.load(
            route_result.file_paths
        )

        print(f"\n📨 「{msg}」")

        print(
            f"   マッチしたファイル: "
            f"{route_result.file_paths}"
        )

        print(
            f"   成功: "
            f"{len(load_result.items)} 件 / "
            f"失敗: "
            f"{len(load_result.errors)} 件"
        )

        for item in load_result.items:

            print(
                f"   --- "
                f"{item.domain_label} "
                f"({item.content_type}) "
                f"desc='{item.description}' ---"
            )

            print(
                f"   {item.content}"
            )