"""
semantic_builder_analyzer.py
====

自作AI用 セマンティック（意味的）グラフ構築モジュール

責務
----------------------------------------------
各独立したコードAnalyzerから得られたフラットなリストデータを、
「エンティティ（ノード）」と「リレーションシップ（エッジ）」からなる
グラフ構造（Semantic Graph）に変換する。

設計方針:
  - 自作AI（RAGや推論エンジン）が文脈を論理的に辿れるようにする。
  - 例: "LoginComponent" (ノード) --[CALLS_API]--> "/api/auth" (ノード)
  - テキストの羅列ではなく、厳密にキーと値が定義された JSON スキーマを生成する。

====
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# セマンティック定義 (グラフ理論に基づくスキーマ)
# ──────────────────────────────────────────────

class EntityType(str, Enum):
    COMPONENT = "Component"
    API = "ApiEndpoint"
    FUNCTION = "Function"
    DEPENDENCY = "Dependency"
    TODO = "Todo"

class RelationType(str, Enum):
    CALLS = "CALLS"             # 関数やコンポーネントがAPIを呼ぶ
    IMPORTS = "IMPORTS"         # 依存関係のインポート
    CONTAINS = "CONTAINS"       # 親が子を内包する
    IMPLEMENTS = "IMPLEMENTS"   # Todoや要件を実装している

@dataclass
class SemanticNode:
    """知識の単位（エンティティ）"""
    node_id: str
    entity_type: EntityType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.entity_type.value,
            "name": self.name,
            "properties": self.properties
        }

@dataclass
class SemanticEdge:
    """知識間の関係性（リレーション）"""
    source_id: str
    target_id: str
    relation: RelationType
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "relation": self.relation.value,
            "description": self.description
        }

@dataclass
class SemanticGraph:
    """自作AIに渡す最終的なセマンティックJSONツリー"""
    nodes: List[SemanticNode] = field(default_factory=list)
    edges: List[SemanticEdge] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }


# ──────────────────────────────────────────────
# SemanticBuilderAnalyzer クラス本体
# ──────────────────────────────────────────────

class SemanticBuilderAnalyzer:
    """
    フラットな解析データをナレッジグラフ形式にビルドするアナライザー
    """

    def analyze(self, raw_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        生データを解析し、ノードとエッジを持つセマンティックJSONを生成する
        """
        logger.info("[SemanticBuilderAnalyzer] セマンティックグラフの構築を開始します")
        
        self.graph = SemanticGraph()
        
        # 1. ノード（エンティティ）の生成
        self._build_component_nodes(raw_meta.get("components", []))
        self._build_api_nodes(raw_meta.get("apis", []))
        self._build_dependency_nodes(raw_meta.get("dependencies", {}))
        
        # 2. エッジ（関係性）の推論と生成
        self._infer_relationships()
        
        logger.info(f"[SemanticBuilderAnalyzer] 構築完了: ノード {len(self.graph.nodes)}件, エッジ {len(self.graph.edges)}件")
        
        return self.graph.to_dict()

    # ──────────────────────────────────────────────
    # ノード構築ロジック
    # ──────────────────────────────────────────────

    def _build_component_nodes(self, components: List[Dict[str, Any]]) -> None:
        for comp in components:
            name = comp.get("name", "UnknownComponent")
            node = SemanticNode(
                node_id=f"comp_{name}",
                entity_type=EntityType.COMPONENT,
                name=name,
                properties={
                    "props": comp.get("props", []),
                    "code_snippet": comp.get("code_snippet", "")
                }
            )
            self.graph.nodes.append(node)

    def _build_api_nodes(self, apis: List[Dict[str, Any]]) -> None:
        for api in apis:
            endpoint = api.get("endpoint", "UnknownEndpoint")
            method = api.get("method", "GET")
            node = SemanticNode(
                node_id=f"api_{method}_{endpoint}",
                entity_type=EntityType.API,
                name=f"{method} {endpoint}",
                properties={
                    "params": api.get("params", [])
                }
            )
            self.graph.nodes.append(node)

    def _build_dependency_nodes(self, dependencies: Dict[str, str]) -> None:
        for dep_name, version in dependencies.items():
            node = SemanticNode(
                node_id=f"dep_{dep_name}",
                entity_type=EntityType.DEPENDENCY,
                name=dep_name,
                properties={"version": version}
            )
            self.graph.nodes.append(node)

    # ──────────────────────────────────────────────
    # エッジ（関係性）推論ロジック
    # ──────────────────────────────────────────────

    def _infer_relationships(self) -> None:
        """
        ノード間のプロパティを分析し、関係性のエッジを自動的に結ぶ。
        """
        # 例: コンポーネントのコード内に、APIエンドポイントの文字列が含まれていたら「CALLS」エッジを張る
        components = [n for n in self.graph.nodes if n.entity_type == EntityType.COMPONENT]
        apis = [n for n in self.graph.nodes if n.entity_type == EntityType.API]
        
        for comp in components:
            code = comp.properties.get("code_snippet", "")
            if not code:
                continue
                
            for api in apis:
                # 簡易的なマッチング。実際はAST解析結果などを使うとより正確。
                endpoint = api.properties.get("endpoint") or api.name.split(" ")[-1]
                if endpoint in code:
                    edge = SemanticEdge(
                        source_id=comp.node_id,
                        target_id=api.node_id,
                        relation=RelationType.CALLS,
                        description=f"Component '{comp.name}' invokes API '{api.name}'"
                    )
                    self.graph.edges.append(edge)