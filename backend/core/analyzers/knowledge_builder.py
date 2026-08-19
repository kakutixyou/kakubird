"""
knowledge_builder.py
====

Knowledge（解析結果オブジェクト）構築モジュール

責務
----------------------------------------------
各独立したAnalyzer（Tag, Attribute, DOM, Component, Script, CSS等）から
得られた断片的な解析結果（Dict）を集約・マージする。
集約されたメタデータを MetricsAnalyzer に引き渡して最終評価（スコア、複雑度、警告）を
算出し、後続のEngineやAIが利用する `BaseKnowledgeResult` オブジェクトを厳密にビルドする。

ビルド手順
1. 空のベースメタデータの準備
2. 各Analyzerの結果をマージ
3. MetricsAnalyzer による総合評価の算出
4. BaseKnowledgeResult のインスタンス化と返却

====
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from backend.core.knowledge_core import BaseKnowledgeResult

# 各Analyzerのインポート（同一パッケージ内を想定）
from .HtmlAnalyzerSet.tag_analyzer import TagAnalyzer
from .attribute_analyzer import AttributeAnalyzer
from .HtmlAnalyzerSet.dom_analyzer import DOMAnalyzer
from .component_analyzer import ComponentAnalyzer
from .script_analyzer import ScriptAnalyzer
from .metrics_analyzer import MetricsAnalyzer

class KnowledgeBuilder:
    """
    各Analyzerの成果物を集約し、BaseKnowledgeResultを構築するビルダーパターンのクラス
    """

    ##############################################
    # 初期化
    ##############################################

    def __init__(self):

        # 評価用のMetricsAnalyzerのみ内部に保持
        self.metrics_analyzer = MetricsAnalyzer()

        self._reset()

    ##############################################
    # リセット
    ##############################################

    def _reset(self):
        """
        ビルド状態および内部メタデータを初期化する。
        """
        self.meta: Dict[str, Any] = {
            # タグ系
            "tags": [],
            "tag_counts": {},
            "semantic_tags": [],
            "custom_elements": [],

            # 属性・イベント系
            "attributes": [],
            "ids": [],
            "classes": [],
            "events": [],

            # 特定要素詳細系
            "forms": [],
            "images": [],
            "links": [],
            "tables": [],
            "scripts": [],
            "styles": [],

            # 構造系
            "dom_depth": 0,
            "component_tree": {},

            # 推測・コンポーネント系
            "detected_components": [],
            "semantic_components": [],
            "custom_components": []
        }

    ##############################################
    # 成果物のマージ
    ##############################################

    def merge_result(
        self,
        analyzer_result: Dict[str, Any]
    ) -> KnowledgeBuilder:
        """
        各Analyzerが解析した辞書データを内部メタデータへマージする。
        流れるようなインターフェース（メソッドチェーン）に対応。

        Parameters
        ----------
        analyzer_result : Dict[str, Any]
            各Analyzerの analyze() メソッドから返された辞書データ
        """
        if not analyzer_result:
            return self

        # 渡された辞書のキーで内部メタデータを更新
        for key, value in analyzer_result.items():
            if key in self.meta:
                self.meta[key] = value

        return self

    ##############################################
    # 特定要素の一括手動回収（Engineの既存ロジック用）
    ##############################################

    def collect_specific_elements(
        self,
        soup: BeautifulSoup
    ) -> KnowledgeBuilder:
        """
        Form, Image, Link, Table, Style などの
        まだ個別Analyzer化されていない特定タグの詳細データを抽出し、マージする。
        """
        if soup is None:
            return self

        # --- Form ---
        for form in soup.find_all("form"):
            form_info = {
                "id": form.get("id"),
                "method": form.get("method", "GET"),
                "action": form.get("action"),
                "inputs": []
            }
            for control in form.find_all(["input", "textarea", "select", "button"]):
                form_info["inputs"].append({
                    "tag": control.name,
                    "type": control.get("type"),
                    "name": control.get("name"),
                    "id": control.get("id")
                })
            self.meta["forms"].append(form_info)

        # --- Image ---
        for img in soup.find_all("img"):
            self.meta["images"].append({
                "src": img.get("src"),
                "alt": img.get("alt"),
                "width": img.get("width"),
                "height": img.get("height")
            })

        # --- Link ---
        for link in soup.find_all("a"):
            self.meta["links"].append({
                "href": link.get("href"),
                "text": link.get_text(strip=True),
                "target": link.get("target")
            })

        # --- Table ---
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            table_info = {
                "rows": len(rows),
                "columns": len(rows[0].find_all(["th", "td"])) if rows else 0
            }
            self.meta["tables"].append(table_info)

        # --- Styles ---
        for style in soup.find_all("style"):
            self.meta["styles"].append({
                "code": style.get_text().strip()
            })

        return self

    ##############################################
    # 最終ビルド
    ##############################################

    def build(self) -> BaseKnowledgeResult:
        """
        マージされたすべてのメタデータを基にMetricsAnalyzerで評価を行い、
        最終的な BaseKnowledgeResult オブジェクトを生成して返す。
        """
        # MetricsAnalyzerによる数値・警告の算出
        metrics = self.metrics_analyzer.analyze(self.meta)

        # 結果オブジェクトの構築
        result = BaseKnowledgeResult(
            score=metrics.get("score", 0),
            complexity=metrics.get("complexity", 0),
            extracted_components=sorted(self.meta.get("tags", [])),
            warnings=metrics.get("warnings", []),
            meta=self.meta
        )

        # 次回ビルドのために状態をリセット
        self._reset()

        return result