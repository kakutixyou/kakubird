"""
synthesis_analyzer.py
====

自作AI用 コンテキスト統合・蒸留モジュール

責務
----------------------------------------------
RepomixAnalyzerの配下にある各独立したAnalyzer（Component, Api, Dependency, Todo等）から
得られた断片的な解析結果（Dict）を集約する。
単なるマージにとどまらず、情報同士の「関連性（Synthesis）」を構築し、
自作AIの推論精度を落とさないために不要なノイズを削ぎ落とす「蒸留（Distillation）」を行う。
最終的に、自作AIエンジンが直接解釈できる `SynthesizedContext` オブジェクトをビルドする。

ビルド手順
1. 空のベースメタデータの準備
2. 各Analyzerの結果をカテゴリ別にIngest（取り込み）
3. 情報の関連付け（例: どのコンポーネントがどのAPIを叩いているか）
4. 情報の蒸留（重要度の低いTodoや肥大化したログのカット）
5. SynthesizedContext のインスタンス化と返却

====
"""

from __future__ import annotations

from typing import Any, Dict, List
from dataclasses import dataclass, field

# ──────────────────────────────────────────────
# 最終出力用 データクラス
# ──────────────────────────────────────────────
@dataclass
class SynthesizedContext:
    """自作AIにそのまま渡すための、蒸留済みコンテキスト"""
    core_architecture: Dict[str, Any] = field(default_factory=dict)
    api_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    key_components: List[Dict[str, Any]] = field(default_factory=list)
    actionable_todos: List[str] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)  # 統合された関係性（AIへのヒント）
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_architecture": self.core_architecture,
            "api_endpoints": self.api_endpoints,
            "key_components": self.key_components,
            "actionable_todos": self.actionable_todos,
            "cross_references": self.cross_references,
            "metrics": self.metrics
        }


class SynthesisAnalyzer:
    """
    各コードAnalyzerの成果物を集約し、関連付けとノイズ除去を行い、
    自作AI向けの SynthesizedContext を構築するビルダーパターンのクラス
    """

    ##############################################
    # 初期化
    ##############################################

    def __init__(self):
        # 必要に応じて、関係性抽出専用のエンジンなどをここに持たせる
        # self.relationship_engine = RelationshipEngine()
        self._reset()

    ##############################################
    # リセット
    ##############################################

    def _reset(self):
        """
        ビルド状態および内部メタデータを初期化する。
        """
        self.raw_meta: Dict[str, Any] = {
            "components": [],
            "apis": [],
            "dependencies": {},
            "classes": [],
            "functions": [],
            "todos": [],
            "comments": []
        }
        self.synthesized_relations: List[str] = []

    ##############################################
    # 成果物の取り込み (Ingest)
    ##############################################

    def ingest_result(
        self,
        category: str,
        analyzer_result: List[Dict[str, Any]] | Dict[str, Any]
    ) -> SynthesisAnalyzer:
        """
        特定のAnalyzer（category）からの結果を内部のraw_metaに格納する。
        流れるようなインターフェース（メソッドチェーン）に対応。

        Parameters
        ----------
        category : str
            格納先のカテゴリ名 (例: "components", "apis", "todos")
        analyzer_result : List[Dict[str, Any]] | Dict[str, Any]
            対象Analyzerから出力されたデータ
        """
        if not analyzer_result:
            return self

        if category in self.raw_meta:
            # リストの場合はextend、辞書の場合はupdate等、よしなにマージ
            if isinstance(analyzer_result, list) and isinstance(self.raw_meta[category], list):
                self.raw_meta[category].extend(analyzer_result)
            elif isinstance(analyzer_result, dict) and isinstance(self.raw_meta[category], dict):
                self.raw_meta[category].update(analyzer_result)
            else:
                self.raw_meta[category] = analyzer_result
                
        return self

    ##############################################
    # 関連付け (Synthesis)
    ##############################################

    def _synthesize_relationships(self) -> None:
        """
        独立して収集されたデータ同士を掛け合わせ、AI向けの「ヒント」を生成する。
        例: Component内の記述とAPIのエンドポイントをマッチングさせる。
        """
        components = self.raw_meta.get("components", [])
        apis = self.raw_meta.get("apis", [])

        # 簡易的なマッチングロジック（実際は名前の包含関係などをチェック）
        for comp in components:
            comp_name = comp.get("name", "UnknownComponent")
            comp_code = comp.get("code_snippet", "")
            
            for api in apis:
                endpoint = api.get("endpoint", "")
                if endpoint and endpoint in comp_code:
                    relation_text = f"💡 [Relation] Component '{comp_name}' highly likely calls API Endpoint '{endpoint}'."
                    self.synthesized_relations.append(relation_text)

    ##############################################
    # 蒸留 (Distillation)
    ##############################################

    def _distill_context(self) -> Dict[str, Any]:
        """
        自作AIのコンテキスト（入力制限）を圧迫しないよう、
        重要度の低い情報（軽微なTodoや過剰なコメント）を削ぎ落とす。
        """
        distilled = {}
        
        # 1. Todoのフィルタリング（HIGHやTODOタグなど、重要なもののみ残す）
        raw_todos = self.raw_meta.get("todos", [])
        distilled["actionable_todos"] = [
            todo.get("text") for todo in raw_todos 
            if todo.get("priority", "low").upper() in ["HIGH", "CRITICAL"]
        ]

        # 2. コンポーネントのフィルタリング（文字数制限や重要度スコアでカット）
        raw_components = self.raw_meta.get("components", [])
        # 例として、上位10件の重要なコンポーネントのみを抽出
        distilled["key_components"] = sorted(
            raw_components, 
            key=lambda x: x.get("complexity_score", 0), 
            reverse=True
        )[:10]

        # 3. APIは全て保持
        distilled["api_endpoints"] = self.raw_meta.get("apis", [])
        
        return distilled

    ##############################################
    # 最終ビルド
    ##############################################

    def build(self) -> SynthesizedContext:
        """
        マージされたデータから関係性を構築・蒸留し、
        最終的な SynthesizedContext オブジェクトを生成して返す。
        """
        # 1. データ間の関係性を分析
        self._synthesize_relationships()

        # 2. データのノイズを除去（蒸留）
        distilled_data = self._distill_context()

        # 3. 結果オブジェクトの構築
        result = SynthesizedContext(
            core_architecture={"dependencies": self.raw_meta.get("dependencies", {})},
            api_endpoints=distilled_data.get("api_endpoints", []),
            key_components=distilled_data.get("key_components", []),
            actionable_todos=distilled_data.get("actionable_todos", []),
            cross_references=self.synthesized_relations,
            metrics={"total_components_analyzed": len(self.raw_meta.get("components", []))}
        )

        # 次回ビルドのために状態をリセット
        self._reset()

        return result