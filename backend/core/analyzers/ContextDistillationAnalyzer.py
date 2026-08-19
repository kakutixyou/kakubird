"""
ContextDistillationAnalyzer.py
====

自作AI用 コンテキスト蒸留・ルーティングメタデータ付与モジュール

責務
----------------------------------------------
1. 蒸留 (Distillation):
   各コードAnalyzer（Component, Api, Todo等）が抽出した生の巨大なデータを、
   LLMのコンテキスト制限（Token上限）に合わせて削ぎ落とす。
   - 長すぎる関数ボディの削除（シグネチャのみ残す）
   - 優先度の低いTodoの削除
   - 不要なDOMノイズのカット

2. ルーティングメタデータの注入:
   自作AIの `KnowledgeRouter` / `KnowledgeLoader` が解釈できるように、
   `name`, `keywords`, `weight`, `description` をルート階層に付与する。

出力
----------------------------------------------
KnowledgeManager の save() にそのまま渡せる辞書（JSON互換）を生成する。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 最終出力スキーマ (KnowledgeLoader の期待する形)
# ──────────────────────────────────────────────
@dataclass
class DistilledKnowledge:
    # --- ルーティング用メタデータ (KnowledgeRouter が使用) ---
    name: str
    description: str
    keywords: List[str]
    weight: float = 1.0

    # --- 知識本体 (KnowledgeLoader が切り出してプロンプト化する部分) ---
    content: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """JSONとして保存するための辞書化"""
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "weight": self.weight,
            "content": self.content
        }


class ContextDistillationAnalyzer:
    """
    巨大なメタデータを蒸留し、KnowledgeLoader向けに最適化するアナライザー
    """

    def __init__(self, max_code_lines: int = 30, max_todos: int = 10):
        """
        Args:
            max_code_lines: 保存を許容するコードスニペットの最大行数
            max_todos: 保存するTODOの最大件数
        """
        self.max_code_lines = max_code_lines
        self.max_todos = max_todos

    def analyze(
        self, 
        raw_meta: Dict[str, Any], 
        domain_name: str, 
        description: str, 
        keywords: List[str], 
        weight: float = 1.0
    ) -> Dict[str, Any]:
        """
        生データを蒸留し、保存用の辞書を生成するメインメソッド
        """
        logger.info(f"[ContextDistillationAnalyzer] '{domain_name}' の蒸留を開始します")

        distilled_content = {}

        # 1. Todoの蒸留（HIGHプライオリティのみ、上限件数まで）
        distilled_content["todos"] = self._distill_todos(raw_meta.get("todos", []))

        # 2. コンポーネントの蒸留（長過ぎるコードのカット）
        distilled_content["components"] = self._distill_components(raw_meta.get("components", []))

        # 3. APIエンドポイント（基本的に全て重要なのでそのまま通すか、レスポンス例だけ削る）
        distilled_content["apis"] = self._distill_apis(raw_meta.get("apis", []))

        # 最終オブジェクトの構築
        result = DistilledKnowledge(
            name=domain_name,
            description=description,
            keywords=keywords,
            weight=weight,
            content=distilled_content
        )

        return result.to_dict()

    # ──────────────────────────────────────────────
    # 蒸留ロジック群
    # ──────────────────────────────────────────────

    def _distill_todos(self, todos: List[Dict[str, Any]]) -> List[str]:
        """優先度の高いTODOテキストのみを抽出・制限"""
        if not todos:
            return []

        high_priority = [
            t.get("text", "") for t in todos 
            if str(t.get("priority", "")).upper() in ["HIGH", "CRITICAL"]
        ]
        
        # 上限件数でカット
        return high_priority[:self.max_todos]

    def _distill_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """コンポーネント情報からノイズを削ぎ落とす"""
        distilled = []
        for comp in components:
            clean_comp = {
                "name": comp.get("name", "Unknown"),
                "props": comp.get("props", []),
                "events": comp.get("events", [])
            }

            # コードスニペットが長すぎる場合、シグネチャ（冒頭）だけ残してカット
            raw_code = comp.get("code_snippet", "")
            code_lines = raw_code.split("\n")
            if len(code_lines) > self.max_code_lines:
                clean_comp["code_snippet"] = "\n".join(code_lines[:5]) + "\n... (truncated for context limits)"
            else:
                clean_comp["code_snippet"] = raw_code

            distilled.append(clean_comp)
            
        return distilled

    def _distill_apis(self, apis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """API情報から巨大なモックデータ等を削る"""
        distilled = []
        for api in apis:
            clean_api = {
                "endpoint": api.get("endpoint"),
                "method": api.get("method"),
                "params": api.get("params", [])
            }
            # 巨大なレスポンスサンプルはトークンを食うため、型情報だけ残して削るなどの処理をここに書く
            distilled.append(clean_api)
            
        return distilled