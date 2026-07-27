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
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KnowledgeDomain:
    name: str                      # 例: "video_editor"
    description: str               # 人間向けの説明
    json_paths: list[str]          # knowledge/ からの相対パス。例: ["video_editor/video_import.json"]
    keywords: list[str]            # このドメインが反応するキーワード（部分一致）
    weight: int = 1                # キーワード1個あたりの得点の重み


@dataclass
class RouteResult:
    """route() の戻り値。デバッグ情報も一緒に持たせておく。"""
    json_paths: list[str]
    matched_domains: list[str]
    scores: dict[str, int] = field(default_factory=dict)  # domain_name -> score


class KnowledgeRouter:
    print("★★★★★ KnowledgeRouter Loaded ★★★★★")
    def __init__(self, registry_path: Path | str, threshold: int = 1, top_k: int | None = None):
        """
        threshold: これ未満のスコアのドメインは採用しない
        top_k:     採用ドメイン数の上限。None なら閾値を超えた全ドメインを採用
        """
        self.registry_path = Path(registry_path)
        self.threshold = threshold
        self.top_k = top_k
        self.domains: list[KnowledgeDomain] = []
        self._load_registry()

    def _load_registry(self) -> None:
        if not self.registry_path.exists():
            raise FileNotFoundError(
                f"registry.json が見つかりません: {self.registry_path}\n"
                f"knowledge/registry.json にドメイン定義を用意してください。"
            )

        with self.registry_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        self.domains = [
            KnowledgeDomain(
                name=d["name"],
                description=d.get("description", ""),
                json_paths=d["json_paths"],
                keywords=d["keywords"],
                weight=d.get("weight", 1),
            )
            for d in raw.get("domains", [])
        ]

    def reload(self) -> None:
        """registry.json を更新した後、プロセスを再起動せず反映したい場合に呼ぶ"""
        self._load_registry()

    def _score_domain(self, message: str, domain: KnowledgeDomain) -> int:
        """
        キーワードの部分一致数 × weight で得点化する。
        大文字小文字を無視し、全角/半角スペースの差異も吸収する。
        """
        normalized = message.lower().replace("　", " ")
        score = 0
        for kw in domain.keywords:
            if kw.lower() in normalized:
                score += domain.weight
        return score

    async def route(self, message: str, signals: dict | None = None) -> RouteResult:
        """
        signals: ChatOrchestrator.active_context 等を渡せば、
                 「直前の文脈と同じドメインならボーナス加点」といった拡張が可能。
                 現時点では未使用（フックだけ用意）。
        """
        scores: dict[str, int] = {}
        for domain in self.domains:
            score = self._score_domain(message, domain)

            # 文脈継続ボーナス（将来の拡張フック）
            if signals and signals.get("active_context") == domain.name:
                score += domain.weight

            scores[domain.name] = score

        # スコア降順でソート
        ranked = sorted(
            (d for d in self.domains if scores[d.name] >= self.threshold),
            key=lambda d: scores[d.name],
            reverse=True,
        )

        if self.top_k is not None:
            ranked = ranked[: self.top_k]

        json_paths: list[str] = []
        for domain in ranked:
            for p in domain.json_paths:
                if p not in json_paths:
                    json_paths.append(p)

        return RouteResult(
            json_paths=json_paths,
            matched_domains=[d.name for d in ranked],
            scores=scores,
        )


# ---------------------------------------------------------------------------
# 動作確認用（このファイル単体で実行して挙動を見られるようにしておく）
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def _demo():
        router = KnowledgeRouter(
            registry_path=Path(__file__).parent / "knowledge" / "registry.json"
        )
        for msg in ["動画を追加するボタンを作って", "ファイルダイアログの実装教えて", "今日の天気は？"]:
            result = await router.route(msg)
            print(f"📨 「{msg}」")
            print(f"   スコア: {result.scores}")
            print(f"   採用ドメイン: {result.matched_domains}")
            print(f"   読み込むJSON: {result.json_paths}\n")

    asyncio.run(_demo())
    
#     この「ピンポイントな分業」がもたらすメリット
# Routerの仕事が「パスを出すだけ」に絞られることで、開発・運用において以下のような大きな強みが生まれます。

# テストが圧倒的に簡単になる
# Routerの挙動をテストする際、実際にファイルを読み込ませる必要がなくなります。「『動画のボタンを作りたい』と入力したら ["video_editor/video_import.json"] という文字列が返ってくるか」を確認するだけで済むため、バグの特定が一瞬で終わります。

# Loader側で高度な最適化ができる
# ファイルの非同期読み込み（asyncio）、一度読んだファイルのメモリキャッシュ、Markdownのテキスト分割（チャンキング）といった複雑な処理はすべて Loader.py に押し付けることができます。これによって Routerのコードが肥大化するのを防げます。

# 将来の検索エンジンのすげ替えが容易
# もし将来、「キーワード一致じゃ限界だから、ベクトル検索（Embedding）やLLM自身にルーティングさせよう」となった場合でも、Routerの中身を書き換えるだけで済みます。パスを出力するという結果さえ同じなら、Loader側は一切修正する必要がありません。

# 全体として、バグが起きにくく拡張しやすい、非常に見通しの良いアーキテクチャになりそうですね。

