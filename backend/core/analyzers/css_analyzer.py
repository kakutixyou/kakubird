"""
css_analyzer.py
==============================================

CSS解析モジュール

責務
----------------------------------------------
BeautifulSoupから <style> タグに関する情報のみを抽出する。
将来的に CSSEngine や、JSX/コンポーネントへの変換を行う自作AIに対して
埋め込まれているスタイルシートのコード本文とその属性を引き渡すための
解析結果を生成する。

抽出対象
・styleタグのmedia属性などのメタデータ
・埋め込まれているCSSコード本文
・CSSコードの文字数やインライン判定

==============================================
"""

from __future__ import annotations

from typing import Any, Dict, List
from bs4 import BeautifulSoup


class CSSAnalyzer:
    """
    <style> タグの解析を専門に行うクラス
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

            "styles": []
        }

    ##############################################
    # 解析実行
    ##############################################

    def analyze(
        self,
        soup: BeautifulSoup
    ) -> Dict[str, Any]:
        """
        HTML内の <style> タグを解析する。

        Parameters
        ----------
        soup : BeautifulSoup
            HTMLParserから受け取ったDOM

        Returns
        -------
        Dict[str, Any]
            CSSの解析結果
        """
        self._reset()

        if soup is None:
            return self.result

        # 全てのstyleタグを抽出
        styles = soup.find_all("style")

        for style in styles:

            # CSSコード本文の取得
            css_code = style.string
            if css_code is None:
                css_code = style.get_text()

            # 前後の余白をトリミング
            cleaned_css = css_code.strip() if css_code else ""

            style_info = {
                # 適用対象のメディア（screen, print等。指定がない場合はデフォルトで None）
                "media": style.get("media"),

                # CSSコード本文
                "code": cleaned_css,

                # コードの文字数（EngineやAIが規模を測るメタデータとして利用）
                "code_length": len(cleaned_css)
            }

            self.result["styles"].append(style_info)

        return self.result

    ##############################################
    # Utility (Engine側での判定や警告生成用)
    ##############################################

    def has_styles(self) -> bool:
        """
        スタイルタグが1つ以上存在するか判定する。
        """
        return len(self.result["styles"]) > 0

    def get_total_css_length(self) -> int:
        """
        解析されたすべてのCSSコードの総文字数を取得する。
        """
        return sum(s["code_length"] for s in self.result["styles"])