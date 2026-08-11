"""
tag_analyzer.py
==============================================

HTMLタグ解析モジュール

責務
----------------------------------------------

BeautifulSoupからHTMLタグに関する情報のみを抽出する。

抽出対象

・タグ一覧
・タグ出現回数
・HTML5セマンティックタグ
・Custom Elements
・SVG
・Canvas

属性・イベント・DOM構造などは解析しない。

HTMLEngineから呼び出されることを前提とした
純粋な解析クラス。
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set

from bs4 import BeautifulSoup
from bs4.element import Tag

# pip install beautifulsoup4
class TagAnalyzer:
    """
    HTMLタグ解析器
    """

    ##############################################
    # HTML標準タグ
    ##############################################

    STANDARD_HTML_TAGS: Set[str] = {

        # Document
        "html",
        "head",
        "body",
        "title",
        "meta",
        "base",
        "link",

        # Sections
        "header",
        "footer",
        "main",
        "section",
        "article",
        "aside",
        "nav",

        # Headings
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",

        # Text
        "div",
        "span",
        "p",
        "br",
        "hr",
        "pre",
        "code",
        "blockquote",

        # Lists
        "ul",
        "ol",
        "li",
        "dl",
        "dt",
        "dd",

        # Forms
        "form",
        "input",
        "textarea",
        "button",
        "label",
        "select",
        "option",
        "fieldset",
        "legend",

        # Media
        "img",
        "picture",
        "video",
        "audio",
        "source",
        "track",

        # Table
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "caption",

        # Graphics
        "svg",
        "canvas",

        # Interactive
        "details",
        "summary",
        "dialog",

        # Script
        "script",
        "style",
        "noscript",

        # Others
        "iframe",
        "template",
        "slot"
    }

    ##############################################
    # HTML5 セマンティックタグ
    ##############################################

    SEMANTIC_TAGS: Set[str] = {

        "header",
        "footer",
        "main",
        "section",
        "article",
        "aside",
        "nav"
    }

    ##############################################
    # 初期化
    ##############################################

    def __init__(self):

        self.soup: BeautifulSoup | None = None

        self._reset()

    ##############################################
    # 初期化
    ##############################################

    def _reset(self):

        self.result: Dict[str, Any] = {

            "tags": [],

            "tag_counts": {},

            "semantic_tags": [],

            "custom_elements": [],

            "svg": [],

            "canvas": []
        }

    ##############################################
    # 解析
    ##############################################

    def analyze(self, soup: BeautifulSoup) -> Dict[str, Any]:
        self._reset()
        self.soup = soup
        if self.soup is None:
            return self.result

        # 1回だけDOM全体を探索してキャッシュする
        self._cached_tags = self.soup.find_all(True)

        self._collect_tags()
        self._collect_tag_counts()
        self._collect_semantic_tags()
        self._collect_custom_elements()
        self._collect_svg_canvas()

        # キャッシュをクリア
        self._cached_tags = None

        return self.result

    ##############################################
    # タグ収集
    ##############################################

    def _collect_tags(self):
        """
        HTML内で使用されているタグを収集する。

        重複しないタグ一覧を作成する。
        """

        for tag in self._all_tags():

            self._append_unique(
                "tags",
                tag.name
            )

    ##############################################
    # タグ出現回数
    ##############################################

    def _collect_tag_counts(self):
        """
        タグごとの出現回数を集計する。
        """

        counter = Counter()

        for tag in self._all_tags():

            counter[tag.name] += 1

        self.result["tag_counts"] = dict(counter)

    ##############################################
    # HTML5 セマンティックタグ
    ##############################################

    def _collect_semantic_tags(self):
        """
        HTML5のセマンティックタグを抽出する。
        """

        for tag in self._all_tags():

            if tag.name in self.SEMANTIC_TAGS:

                self._append_unique(
                    "semantic_tags",
                    tag.name
                )
                
    ##############################################
    # Custom Elements
    ##############################################

    def _collect_custom_elements(self):
        """
        Custom Element を抽出する。

        HTML Standardでは
        ハイフン(-)を含むタグ名は
        Custom Elementとして扱われる。
        """

        for tag in self._all_tags():

            tag_name = tag.name.lower()

            # HTML標準タグは除外
            if tag_name in self.STANDARD_HTML_TAGS:
                continue

            # Custom Element判定
            if "-" in tag_name:

                self._append_unique(
                    "custom_elements",
                    tag_name
                )

    ##############################################
    # SVG / Canvas
    ##############################################

    def _collect_svg_canvas(self):
        """
        SVG / Canvasタグを抽出する。
        """

        for tag in self._all_tags():

            tag_name = tag.name.lower()

            if tag_name == "svg":

                self.result["svg"].append({

                    "tag": "svg"

                })

            elif tag_name == "canvas":

                self.result["canvas"].append({

                    "tag": "canvas"

                })

    ##############################################
    # Utility
    ##############################################

    def _append_unique(
        self,
        key: str,
        value: Any
    ):
        """
        重複しないよう追加する。
        """

        if value is None:
            return

        if value == "":
            return

        if value not in self.result[key]:

            self.result[key].append(value)

    ##############################################
    # Utility
    ##############################################

    def _all_tags(self) -> List[Tag]:
        """キャッシュされた全タグを返す"""
        return self._cached_tags if hasattr(self, '_cached_tags') and self._cached_tags else []

    ##############################################
    # Utility
    ##############################################

    def has_semantic_tags(self) -> bool:
        """
        セマンティックタグが存在するか判定する。
        """

        return len(self.result["semantic_tags"]) > 0

    ##############################################
    # Utility
    ##############################################

    def has_custom_elements(self) -> bool:
        """
        Custom Elementが存在するか判定する。
        """

        return len(self.result["custom_elements"]) > 0

    ##############################################
    # Utility
    ##############################################

    def has_svg(self) -> bool:
        """
        SVGタグが存在するか判定する。
        """

        return len(self.result["svg"]) > 0

    ##############################################
    # Utility
    ##############################################

    def has_canvas(self) -> bool:
        """
        Canvasタグが存在するか判定する。
        """

        return len(self.result["canvas"]) > 0