from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class EventModel:
    """
    HTML要素に紐づくイベント属性（onclick, onchangeなど）を表現するデータモデル。
    静的なHTML解析結果を構造化し、後続のUIファクトリー（ReactのJSXなど）での
    変換や再利用を容易にするためのマッピング情報を提供する。
    """

    # --- 解析時に取得する生のデータ ---
    raw_attribute: str  # HTML上の実際の属性名 (例: "onclick", "onmouseover")
    handler_code: str   # 属性内に記述されたJSコード (例: "handleSubmit(event)")

    # --- イベントが紐づいている要素の情報 ---
    element_tag: Optional[str] = None  # 要素のタグ名 (例: "button", "input")
    element_id: Optional[str] = None   # 要素のID (関連付けやデバッグ用)

    # --- 自動生成されるメタデータ (init=False) ---
    event_type: str = field(init=False)         # イベントの純粋な種類 (例: "click")
    react_equivalent: str = field(init=False)   # React/JSX用のイベント名 (例: "onClick")

    def __post_init__(self) -> None:
        """
        インスタンス生成時に、生の属性名から純粋なイベントタイプを抽出し、
        フレームワーク（React等）で利用されるキャメルケースのイベント名へ自動マッピングする。
        """
        # 1. "onclick" 等から "on" を取り除いて小文字化
        lower_attr = self.raw_attribute.lower()
        if lower_attr.startswith("on"):
            self.event_type = lower_attr[2:]
        else:
            self.event_type = lower_attr

        # 2. JSX（React）向けのマッピングを実行
        self.react_equivalent = self._map_to_react_event(self.event_type)

    def _map_to_react_event(self, event_type: str) -> str:
        """
        標準的なDOMイベント名を、ReactのSyntheticEvent（合成イベント）の
        キャメルケース命名規則に変換する。
        """
        mapping = {
            # マウスイベント
            "click": "onClick",
            "dblclick": "onDoubleClick",
            "mouseover": "onMouseOver",
            "mouseout": "onMouseOut",
            "mouseenter": "onMouseEnter",
            "mouseleave": "onMouseLeave",
            "mousemove": "onMouseMove",
            
            # フォーム・入力イベント
            "change": "onChange",
            "input": "onInput",
            "submit": "onSubmit",
            "focus": "onFocus",
            "blur": "onBlur",
            
            # キーボードイベント
            "keydown": "onKeyDown",
            "keyup": "onKeyUp",
            "keypress": "onKeyPress",
            
            # その他UIイベント
            "scroll": "onScroll",
            "load": "onLoad",
            "error": "onError"
        }
        
        # マッピング辞書に存在すればそれを返し、なければキャメルケースを推測して返す
        return mapping.get(event_type, f"on{event_type.capitalize()}")

    def to_dict(self) -> Dict[str, Any]:
        """
        KnowledgeBuilderの `self.meta["events"]` に集約するため、
        オブジェクトを辞書形式にシリアライズする。
        """
        return {
            "raw_attribute": self.raw_attribute,
            "event_type": self.event_type,
            "react_equivalent": self.react_equivalent,
            "handler_code": self.handler_code,
            "element_tag": self.element_tag,
            "element_id": self.element_id,
        }