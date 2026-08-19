"""
attribute_analyzer.py
====

Attribute（属性）＆ Event解析モジュール

責務
----------------------------------------------
BeautifulSoupからHTMLタグに付与されている属性、ID、クラス、および
インラインイベントハンドラー（onclick等）に関する情報のみを抽出する。
将来的に JSX への書き換えを行う自作AIや、CSS/Scriptの紐付けを行う
後続エンジンに対して、要素の識別子や動的な挙動のフック（イベント）を
網羅した解析結果を提供する。

抽出対象
・重複のない属性名一覧（attributes）
・重複のないID名一覧（ids）
・重複のないクラス名一覧（classes）
・インラインイベントの詳細（events: イベント名、対象タグ、設定値）

====
"""

from __future__ import annotations

from typing import Any, Dict, List
from bs4 import BeautifulSoup


class AttributeAnalyzer:
    """
    HTML要素の属性、ID、クラス、およびインラインイベントの抽出を専門に行うクラス
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

            "attributes": [],

            "ids": [],

            "classes": [],

            "events": []
        }

    ##############################################
    # 解析実行
    ##############################################

    def analyze(
        self,
        soup: BeautifulSoup
    ) -> Dict[str, Any]:
        """
        HTML内の全タグの属性を走査し、ID、クラス、インラインイベントを抽出する。

        Parameters
        ----------
        soup : BeautifulSoup
            HTMLParserから受け取ったDOM

        Returns
        -------
        Dict[str, Any]
            属性・イベントの解析結果
        """
        self._reset()

        if soup is None:
            return self.result

        # DOM内の全タグを一度の走査で処理
        for tag in soup.find_all(True):
            
            if not tag.attrs:
                continue

            for attr, value in tag.attrs.items():
                
                # 1. 属性名の普遍的な回収（重複排除）
                self._append_unique("attributes", attr)

                # 2. ID属性の回収
                if attr == "id":
                    # 稀に存在する特殊なケースを考慮し文字列化して追加
                    if value:
                        self._append_unique("ids", str(value))

                # 3. クラス属性の回収
                elif attr == "class":
                    # BeautifulSoupは複数クラスをリスト、単一を文字列で返す場合があるため正常化
                    class_list = value if isinstance(value, list) else [value]
                    for c in class_list:
                        if c:
                            self._append_unique("classes", str(c))

                # 4. インラインイベントの回収 (onclick, onchange, onsubmit等)
                elif attr.startswith("on"):
                    # イベントは同一タグ・同一内容でも出現ごとに記録するためappend_uniqueは使わない
                    self.result["events"].append({
                        "event": attr,
                        "tag": tag.name,
                        "value": str(value).strip() if value else ""
                    })

        return self.result

    ##############################################
    # 内部ロジック：Utility
    ##############################################

    def _append_unique(
        self,
        key: str,
        value: Any
    ):
        """
        指定されたキーのリストに対して、重複や空文字を排除して安全に追加する。
        """
        if value is None or value == "":
            return

        if value not in self.result[key]:
            self.result[key].append(value)

    ##############################################
    # Utility (Engine側や外部からのアクセス用)
    ##############################################

    def get_attributes(self) -> List[str]:
        return self.result["attributes"]

    def get_ids(self) -> List[str]:
        return self.result["ids"]

    def get_classes(self) -> List[str]:
        return self.result["classes"]

    def get_events(self) -> List[Dict[str, Any]]:
        return self.result["events"]

    def has_events(self) -> bool:
        """
        インラインイベントハンドラーが1つ以上存在するか判定する。
        """
        return len(self.result["events"]) > 0