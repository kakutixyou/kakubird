"""
component_analyzer.py
====

Component解析モジュール

責務
----------------------------------------------
BeautifulSoupからHTML内のコンポーネント（意味的な塊やカスタム要素）に関する情報を推測・抽出する。
将来的に BlockBuilder などのコンポーネント再構築エンジンや、
JSXコンポーネントへの変換を行う自作AIに対して、どのようなUIコンポーネントが
画面内に存在するかという重要な「構成情報（コンテキスト）」を提供する。

抽出・推測対象
・外部ルール（JSON）に基づくコンポーネント候補の検出（detected_components）
・タグ、クラス、ID、特定要素の数から意味的なUI要素を推測（semantic_components）
・Custom ElementsやReact風のカスタムコンポーネントタグを検出（custom_components）

====
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from bs4 import BeautifulSoup


class ComponentAnalyzer:
    """
    HTML内のコンポーネント要素の抽出および意味解析を専門に行うクラス
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

            "detected_components": [],

            "semantic_components": [],

            "custom_components": []
        }

    ##############################################
    # 解析実行
    ##############################################

    def analyze(
        self,
        soup: BeautifulSoup,
        rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        HTMLを走査し、各種コンポーネントの検出と推測を行う。

        Parameters
        ----------
        soup : BeautifulSoup
            HTMLParserから受け取ったDOM
        rules : Optional[Dict[str, Any]]
            html_keywords.json 等から読み込まれたコンポーネント判定ルール

        Returns
        -------
        Dict[str, Any]
            コンポーネント解析結果
        """
        self._reset()

        if soup is None:
            return self.result

        # 解析に必要な基本データ（タグ、クラス、ID、特定要素の数）を下準備として抽出
        all_tags = soup.find_all(True)
        tag_set = {t.name for t in all_tags if t.name}
        
        class_set: Set[str] = set()
        id_set: Set[str] = set()
        
        for tag in all_tags:
            # クラスの回収
            raw_class = tag.get("class", [])
            classes = raw_class if isinstance(raw_class, list) else [raw_class]
            for c in classes:
                if c:
                    class_set.add(str(c).lower())
            
            # IDの回収
            tag_id = tag.get("id")
            if tag_id:
                # 複数IDや数値などのイレギュラーケースを考慮し文字列化
                id_set.add(str(tag_id).lower())

        image_count = len(soup.find_all("img"))
        form_count = len(soup.find_all("form"))
        table_count = len(soup.find_all("table"))

        # 各解析メソッドの実行
        self._apply_html_rules(tag_set, rules)
        self._detect_semantic_components(tag_set, class_set, id_set, image_count, form_count, table_count)
        self._detect_custom_components(tag_set)

        return self.result

    ##############################################
    # 内部ロジック：ルールベース解析
    ##############################################

    def _apply_html_rules(
        self,
        tags: Set[str],
        rules: Optional[Dict[str, Any]]
    ):
        """
        外部から与えられたルール（必須タグ、オプションタグの組み合わせ）に
        適合するコンポーネントを抽出する。
        """
        if not rules:
            return

        detected = []

        for component_name, rule in rules.items():

            required = set(rule.get("required_tags", []))
            optional = set(rule.get("optional_tags", []))

            # 必須タグがすべて含まれているか判定
            if required and required.issubset(tags):
                detected.append(component_name)
                continue

            # オプションタグが2つ以上含まれているか判定
            if optional and len(optional & tags) >= 2:
                detected.append(component_name)

        self.result["detected_components"] = sorted(list(set(detected)))

    ##############################################
    # 内部ロジック：セマンティック（意味論）解析
    ##############################################

    def _detect_semantic_components(
        self,
        tags: Set[str],
        classes: Set[str],
        ids: Set[str],
        image_count: int,
        form_count: int,
        table_count: int
    ):
        """
        タグの組み合わせや、特定のキーワードを含むクラス名・IDから、
        画面上の主要なUIコンポーネント（Hero, Navbar, Card等）を推測する。
        """
        detected = []

        # 1. Heroセクションの推測
        if "section" in tags and "button" in tags and ("h1" in tags or "h2" in tags):
            detected.append("hero")

        # 2. ナビゲーションバーの推測
        if "nav" in tags or "navbar" in classes or "navbar" in ids:
            detected.append("navbar")

        # 3. フッターの推測
        if "footer" in tags or "footer" in classes:
            detected.append("footer")

        # 4. カード型UIの推測
        if "card" in classes or "card" in ids:
            detected.append("card")

        # 5. サイドバーの推測
        if "sidebar" in classes or "aside" in tags:
            detected.append("sidebar")

        # 6. モーダル・ダイアログの推測
        if "modal" in classes or "dialog" in tags:
            detected.append("modal")

        # 7. ギャラリー（画像一覧）の推測
        if image_count >= 3:
            detected.append("gallery")

        # 8. 料金表（Pricing）の推測
        if "pricing" in classes or "price" in classes:
            detected.append("pricing")

        # 9. お問い合わせフォームの推測
        if form_count > 0:
            detected.append("contact_form")

        # 10. テーブルレイアウトの推測
        if table_count > 0:
            detected.append("table_layout")

        self.result["semantic_components"] = sorted(list(set(detected)))

    ##############################################
    # 内部ロジック：カスタム要素・大文字コンポーネント解析
    ##############################################

    def _detect_custom_components(
        self,
        tags: Set[str]
    ):
        """
        Web Components（ハイフンを含むタグ名）や、
        React/JSX等でよく使われる大文字始まりのカスタムタグを検出する。
        """
        custom = []

        for tag in tags:
            if not tag:
                continue

            # Custom Elementsの規格（ハイフンを含む）
            if "-" in tag:
                custom.append(tag)
                continue

            # 先頭が大文字（ReactなどのコンポーネントタグがそのままHTMLに混入・定義されているケースを想定）
            if tag[0].isupper():
                custom.append(tag)

        self.result["custom_components"] = sorted(list(set(custom)))

    ##############################################
    # Utility
    ##############################################

    def get_detected_components(self) -> List[str]:
        return self.result["detected_components"]

    def get_semantic_components(self) -> List[str]:
        return self.result["semantic_components"]

    def get_custom_components(self) -> List[str]:
        return self.result["custom_components"]