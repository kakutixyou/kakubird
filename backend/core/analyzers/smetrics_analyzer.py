"""
metrics_analyzer.py
====

Metrics（指標・評価）解析モジュール

責務
----------------------------------------------
他のAnalyzerによって抽出されたHTMLのメタデータ（Dict）を基に、
HTML全体の品質や構造に関する「定量的な評価指標」および「警告」を算出する。
Engineが最終的な BaseKnowledgeResult を構築する際の評価フェーズを専門に担当する。

算出対象
・完成度スコア（calculate_score: 100点満点）
・構造複雑度（estimate_complexity: 相対値）
・構造上の懸念や最適化への警告一覧（generate_warnings）

====
"""

from __future__ import annotations

from typing import Any, Dict, List


class MetricsAnalyzer:
    """
    HTMLの品質スコア、複雑度、および構造警告の計算を専門に行うクラス
    """

    ##############################################
    # 初期化
    ##############################################

    def __init__(self):

        self._reset()

    ##############################################
    # リセット
    ##############################################

    def _reset(self):
        """
        解析状態を初期化する。
        """
        self.result: Dict[str, Any] = {

            "score": 0,

            "complexity": 0,

            "warnings": []
        }

    ##############################################
    # 解析実行
    ##############################################

    def analyze(
        self,
        meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        集約されたメタデータを評価し、スコア、複雑度、警告を算出する。

        Parameters
        ----------
        meta : Dict[str, Any]
            各Analyzerによって収集されたHTMLの構造・要素に関するメタデータ辞書

        Returns
        -------
        Dict[str, Any]
            指標の解析結果（score, complexity, warnings）
        """
        self._reset()

        if not meta:
            self.result["warnings"].append("No metadata available for evaluation.")
            return self.result

        # 各指標の計算処理を実行
        self.result["score"] = self._calculate_score(meta)
        self.result["complexity"] = self._estimate_complexity(meta)
        self.result["warnings"] = self._generate_warnings(meta)

        return self.result

    ##############################################
    # 内部ロジック：完成度スコア計算
    ##############################################

    def _calculate_score(
        self,
        meta: Dict[str, Any]
    ) -> int:
        """
        HTML全体の要素の多様性や実装状況から完成度を100点満点で評価する。
        """
        score = 0

        # メタデータからの要素数カウント（キーが存在しない場合のフォールバック付き）
        tag_count = len(meta.get("tags", []))
        attribute_count = len(meta.get("attributes", []))
        event_count = len(meta.get("events", []))
        form_count = len(meta.get("forms", []))
        image_count = len(meta.get("images", []))
        table_count = len(meta.get("tables", []))
        script_count = len(meta.get("scripts", []))
        style_count = len(meta.get("styles", []))

        # 1. HTMLタグの多様性 (最大30点)
        score += min(tag_count * 2, 30)

        # 2. 属性の利用度 (最大20点)
        score += min(attribute_count, 20)

        # 3. インラインイベントの利用 (最大10点)
        score += min(event_count * 2, 10)

        # 4. フォーム要素の有無 (最大10点)
        score += min(form_count * 5, 10)

        # 5. 画像要素の有無 (最大5点)
        score += min(image_count * 2, 5)

        # 6. テーブル要素の有無 (最大5点)
        score += min(table_count * 2, 5)

        # 7. スクリプトの実装有無 (10点)
        if script_count > 0:
            score += 10

        # 8. スタイルの実装有無 (10点)
        if style_count > 0:
            score += 10

        # 100点満点を超えないように制限
        return min(score, 100)

    ##############################################
    # 内部ロジック：構造複雑度の算出
    ##############################################

    def _estimate_complexity(
        self,
        meta: Dict[str, Any]
    ) -> int:
        """
        タグ数、属性数、スクリプトの量、DOMの深度などから、
        HTML全体の構造的な複雑度（相対値）を算出する。
        """
        complexity = 0

        complexity += len(meta.get("tags", []))
        complexity += len(meta.get("attributes", []))
        complexity += len(meta.get("events", [])) * 2
        complexity += len(meta.get("forms", [])) * 3
        complexity += len(meta.get("scripts", [])) * 5
        complexity += len(meta.get("styles", [])) * 3
        
        # DOM深度を加算
        complexity += meta.get("dom_depth", 0)

        return complexity

    ##############################################
    # 内部ロジック：警告（インサイト）の生成
    ##############################################

    def _generate_warnings(
        self,
        meta: Dict[str, Any]
    ) -> List[str]:
        """
        HTML構造上のベストプラクティスから逸脱している懸念点を検出し、警告一覧を生成する。
        """
        warnings = []

        tag_count = len(meta.get("tags", []))
        script_count = len(meta.get("scripts", []))
        style_count = len(meta.get("styles", []))
        dom_depth = meta.get("dom_depth", 0)

        # タグが一切検出されない場合
        if tag_count == 0:
            warnings.append("No HTML tags detected.")

        # scriptタグが多すぎる（React化やバンドル前のVanilla JSに多い傾向）
        if script_count > 10:
            warnings.append("Large number of <script> tags.")

        # styleタグが多すぎる（CSSの管理が煩雑化している可能性）
        if style_count > 5:
            warnings.append("Large number of <style> tags.")

        # DOM treeが深すぎる（描画パフォーマンス低下やコンポーネント分割不足のシグナル）
        if dom_depth > 15:
            warnings.append("DOM tree is very deep.")

        return warnings

    ##############################################
    # Utility
    ##############################################

    def get_score(self) -> int:
        return self.result["score"]

    def get_complexity(self) -> int:
        return self.result["complexity"]

    def get_warnings(self) -> List[str]:
        return self.result["warnings"]