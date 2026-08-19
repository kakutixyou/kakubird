"""
script_analyzer.py
====

Script解析モジュール

責務
----------------------------------------------
BeautifulSoupから <script> タグに関する情報のみを抽出する。
将来的に ScriptEngine や、JSXへの変換を行う自作AIへ
ソースコード本文とその属性を引き渡すための解析結果を生成する。

抽出対象
・scriptタグのtype属性
・scriptタグのsrc属性（外部ファイルリンク）
・インラインスクリプトのコード本文

====
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup


class ScriptAnalyzer:
    """
    <script> タグの解析を専門に行うクラス
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

            "scripts": []
        }

    ##############################################
    # 解析実行
    ##############################################

    def analyze(
        self,
        soup: BeautifulSoup
    ) -> Dict[str, Any]:
        """
        HTML内の <script> タグを解析する。

        Parameters
        ----------
        soup : BeautifulSoup
            HTMLParserから受け取ったDOM

        Returns
        -------
        Dict[str, Any]
            スクリプトの解析結果
        """
        self._reset()

        if soup is None:
            return self.result

        # 全てのscriptタグを抽出
        scripts = soup.find_all("script")

        for script in scripts:

            # コード本文の取得（.stringがNoneの場合はget_textで補足）
            code = script.string
            if code is None:
                code = script.get_text()

            # 本文の前後の余白をトリミング
            cleaned_code = code.strip() if code else ""
            src_attr = script.get("src")

            script_info = {
                # デフォルトは text/javascript として扱う
                "type": script.get("type", "text/javascript"),

                # 外部ソースURL (存在しない場合はNone)
                "src": src_attr,

                # ソースコード本文
                "code": cleaned_code,

                # 判定用メタデータ（EngineやAIが利用しやすいように付与）
                "is_inline": src_attr is None,
                
                "code_length": len(cleaned_code)
            }

            self.result["scripts"].append(script_info)

        return self.result

    ##############################################
    # Utility (Engine側での判定や警告生成用)
    ##############################################

    def has_scripts(self) -> bool:
        """
        スクリプトタグが1つ以上存在するか判定する。
        """
        return len(self.result["scripts"]) > 0

    def get_inline_scripts(self) -> List[Dict[str, Any]]:
        """
        インラインスクリプトのみをフィルタリングして取得する。
        """
        return [s for s in self.result["scripts"] if s["is_inline"]]

    def get_external_scripts(self) -> List[Dict[str, Any]]:
        """
        外部ファイルを読み込んでいるscriptタグのみを取得する。
        """
        return [s for s in self.result["scripts"] if not s["is_inline"]]