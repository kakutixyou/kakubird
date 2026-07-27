"""
KnowledgeLoader
===============
役割: KnowledgeRouter が選んだ json_paths（例: ["electron/ipc.json", ...]）を受け取り、
      knowledge/ ディレクトリから実データを読み込んで PromptBuilder に渡せる形にする。

設計方針:
  - 1リクエストにつき毎回ディスクから読むのはコストなので、mtime（最終更新時刻）
    ベースのキャッシュを持つ。ファイルが更新されていれば自動で読み直す。
    knowledge.json のような「たまに再生成される」JSONと相性が良い。

  - 1ファイルの読み込み失敗（存在しない/JSON壊れ）が全体を落とさないようにする。
    ChatOrchestrator の各ハンドラーが None を返してもエラーにしない、という
    既存の防御的な設計と一貫させている。

  - PromptBuilder 側が「どのファイルの知識か」を出典として明示できるように、
    ファイルパスと中身を紐付けたまま保持する（マージして中身をごちゃ混ぜにしない）。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LoadedKnowledge:
    path: str                 # knowledge/ からの相対パス
    domain_label: str         # 例: "electron/ipc" -> PromptBuilder が出典表示に使う
    content: Any               # 読み込んだ JSON の中身（dict / list など）


@dataclass
class LoadError:
    path: str
    reason: str                # "not_found" | "invalid_json" | "read_error"
    detail: str = ""


@dataclass
class LoadResult:
    items: list[LoadedKnowledge] = field(default_factory=list)
    errors: list[LoadError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def as_merged_dict(self) -> dict:
        """
        domain_label をキーにした単純マージ。PromptBuilder が
        「ラベル付きでそのまま出力したい」場合の簡易ヘルパー。
        中身を混ぜたくない用途では items をそのまま使う方が安全。
        """
        return {item.domain_label: item.content for item in self.items}


class KnowledgeLoader:
    print("★★★★★ KnowledgeLoader Loaded ★★★★★")
    def __init__(self, base_dir: str | Path = "knowledge", cache_enabled: bool = True):
        self.base_dir = Path(base_dir)
        self.cache_enabled = cache_enabled
        # path(str) -> (mtime: float, content: Any)
        self._cache: dict[str, tuple[float, Any]] = {}

    def _domain_label(self, rel_path: str) -> str:
        """'electron/ipc.json' -> 'electron/ipc'（拡張子を落として出典ラベルに使う）"""
        return rel_path[:-5] if rel_path.endswith(".json") else rel_path

    def _read_one(self, rel_path: str) -> tuple[LoadedKnowledge | None, LoadError | None]:
        abs_path = self.base_dir / rel_path

        if not abs_path.exists():
            return None, LoadError(path=rel_path, reason="not_found",
                                    detail=f"ファイルが存在しません: {abs_path}")

        try:
            mtime = abs_path.stat().st_mtime
        except OSError as e:
            return None, LoadError(path=rel_path, reason="read_error", detail=str(e))

        # キャッシュヒット判定（mtime が変わっていなければ読み直さない）
        if self.cache_enabled and rel_path in self._cache:
            cached_mtime, cached_content = self._cache[rel_path]
            if cached_mtime == mtime:
                return LoadedKnowledge(
                    path=rel_path,
                    domain_label=self._domain_label(rel_path),
                    content=cached_content,
                ), None

        try:
            with abs_path.open("r", encoding="utf-8") as f:
                content = json.load(f)
        except json.JSONDecodeError as e:
            return None, LoadError(path=rel_path, reason="invalid_json", detail=str(e))
        except OSError as e:
            return None, LoadError(path=rel_path, reason="read_error", detail=str(e))

        if self.cache_enabled:
            self._cache[rel_path] = (mtime, content)

        return LoadedKnowledge(
            path=rel_path,
            domain_label=self._domain_label(rel_path),
            content=content,
        ), None

    async def load(self, json_paths: list[str]) -> LoadResult:
        """
        json_paths: KnowledgeRouter.route(...).json_paths をそのまま渡す想定。
        ファイルI/Oは軽量なので同期読み込みのままにしているが、
        将来リモートストレージ等に置き換える場合はここを aiofiles / HTTP fetch に差し替える。
        """
        result = LoadResult()

        for rel_path in json_paths:
            item, error = self._read_one(rel_path)
            if item is not None:
                result.items.append(item)
                print(f"📚 [Loader] 読み込み成功: {rel_path}")
            if error is not None:
                result.errors.append(error)
                print(f"⚠️ [Loader] 読み込み失敗 ({error.reason}): {rel_path} - {error.detail}")

        return result

    def clear_cache(self) -> None:
        self._cache.clear()


# ---------------------------------------------------------------------------
# 動作確認用
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def _demo():
        loader = KnowledgeLoader(base_dir=Path(__file__).parent / "knowledge")

        # Router が返す想定のパス（一部わざと存在しないファイルを混ぜてエラー処理も確認）
        paths = [
            "electron/ipc.json",
            "electron/dialog.json",
            "electron/nonexistent.json",
        ]

        result = await loader.load(paths)
        print(f"\n✅ 成功: {len(result.items)} 件 / ❌ 失敗: {len(result.errors)} 件\n")

        for item in result.items:
            print(f"--- {item.domain_label} ---")
            print(json.dumps(item.content, ensure_ascii=False, indent=2))
            print()

        # キャッシュが効くことの確認（2回目は "読み込み成功" ログは出るが実ファイルは読まれない）
        print("🔁 2回目のロード（キャッシュ確認）:")
        await loader.load(paths)

    asyncio.run(_demo())