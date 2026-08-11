"""
dom_analyzer.py
==============================================

DOM構造解析モジュール

責務
----------------------------------------------
BeautifulSoupからHTMLの木構造（トポロジー）に関する情報のみを抽出する。
将来的に BlockBuilder などのコンポーネント再構築エンジンへ
DOMの階層構造や、各要素の識別子（id, class）をバトンタッチするための
解析結果を生成する。

抽出対象
・DOMの最大深度（ネストレベル）
・コンポーネントツリー（タグ、ID、クラスの階層構造）

==============================================
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from bs4 import BeautifulSoup
from bs4.element import Tag


class DOMAnalyzer:
    """
    DOM構造およびツリー階層の解析を専門に行うクラス
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

            "dom_depth": 0,

            "component_tree": {}
        }

    ##############################################
    # 解析実行
    ##############################################

    def analyze(
        self,
        soup: BeautifulSoup
    ) -> Dict[str, Any]:
        """
        HTMLのDOM構造を解析し、深度とツリー構造を取得する。

        Parameters
        ----------
        soup : BeautifulSoup
            HTMLParserから受け取ったDOM

        Returns
        -------
        Dict[str, Any]
            DOM解析結果
        """
        self._reset()

        if soup is None:
            return self.result

        # ルートノード（最初のタグ。通常は <html>）を取得
        root_node = soup.find()

        if root_node and isinstance(root_node, Tag):

            # 最大深度の計算
            self.result["dom_depth"] = self._calculate_dom_depth(root_node)

            # コンポーネントツリーの構築
            self.result["component_tree"] = self._build_component_tree(root_node)

        return self.result

    ##############################################
    # 内部ロジック：DOM深度計算
    ##############################################

    def _calculate_dom_depth(
        self,
        node: Tag,
        current_depth: int = 1
    ) -> int:
        """
        再帰的にDOMを探索し、最大の深度（階層レベル）を計算する。
        """
        max_depth = current_depth

        for child in node.children:

            # テキストノードやコメント（NavigableStringなど）は除外し、Tagのみを走査
            if not isinstance(child, Tag):
                continue

            child_depth = self._calculate_dom_depth(
                child,
                current_depth + 1
            )

            max_depth = max(max_depth, child_depth)

        return max_depth

    ##############################################
    # 内部ロジック：ツリー構造構築
    ##############################################

    def _build_component_tree(
        self,
        node: Tag
    ) -> Dict[str, Any]:
        """
        再帰的にHTML要素を走査し、シリアライズ（JSON化）可能なツリー構造を構築する。
        """
        # クラス属性の安全な取得（BeautifulSoupは複数クラスをリスト、単一を文字列で返す場合があるため追随）
        raw_classes = node.get("class", [])
        classes = raw_classes if isinstance(raw_classes, list) else [raw_classes]

        tree = {
            "tag": node.name,

            "id": node.get("id"),

            "classes": [str(c) for c in classes],

            "children": []
        }

        for child in node.children:

            if not isinstance(child, Tag):
                continue

            # 子要素に対しても再帰的にツリーを構築してリストに追加
            tree["children"].append(
                self._build_component_tree(child)
            )

        return tree

    ##############################################
    # Utility (Engineやその他のコンポーネントが利用)
    ##############################################

    def get_dom_depth(self) -> int:
        """
        解析されたDOMの最大深度を取得する。
        """
        return self.result["dom_depth"]

    def get_component_tree(self) -> Dict[str, Any]:
        """
        構築されたコンポーネントツリーを取得する。
        """
        return self.result["component_tree"]

    def is_empty_tree(self) -> bool:
        """
        ツリー構造が空（要素が存在しない）かどうかを判定する。
        """
        return not bool(self.result["component_tree"])