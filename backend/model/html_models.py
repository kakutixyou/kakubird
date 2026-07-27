from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ImageModel:
    """
    HTMLの <img> 要素を表現するデータモデル。
    アクセシビリティ（alt属性）や遅延読み込みの解析に利用する。
    """
    src: Optional[str] = None
    alt: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    loading: Optional[str] = None  # 例: "lazy"
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "src": self.src,
            "alt": self.alt,
            "width": self.width,
            "height": self.height,
            "loading": self.loading,
            "attributes": self.attributes
        }


@dataclass
class LinkModel:
    """
    HTMLの <a> 要素（アンカー）を表現するデータモデル。
    ルーティング（React Router等への変換）や外部リンクの判定に利用する。
    """
    href: Optional[str] = None
    text: str = ""
    target: Optional[str] = None
    rel: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    
    # 解析による自動判定フラグ
    is_external: bool = field(init=False, default=False)
    react_router_compatible: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        """hrefやtargetの値から、外部リンクか内部リンクかを自動判定する"""
        if self.href and (self.href.startswith("http") or self.target == "_blank"):
            self.is_external = True
            self.react_router_compatible = False
        if self.href and self.href.startswith("#"):
            self.react_router_compatible = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "href": self.href,
            "text": self.text,
            "target": self.target,
            "is_external": self.is_external,
            "react_router_compatible": self.react_router_compatible,
            "attributes": self.attributes
        }


@dataclass
class TableModel:
    """
    HTMLの <table> 要素を表現するデータモデル。
    複雑なデータグリッドをReactコンポーネント化する際の下準備として機能する。
    """
    element_id: Optional[str] = None
    row_count: int = 0
    col_count: int = 0
    has_header: bool = False  # <thead> や <th> が存在するか
    caption: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.element_id,
            "row_count": self.row_count,
            "col_count": self.col_count,
            "has_header": self.has_header,
            "caption": self.caption,
            "attributes": self.attributes
        }


@dataclass
class ScriptModel:
    """
    HTML内の <script> 要素を表現するデータモデル。
    外部スクリプトの読み込みや、インラインJSの抽出に利用する。
    """
    src: Optional[str] = None
    script_type: str = "text/javascript"  # 例: "module" など
    is_async: bool = False
    is_defer: bool = False
    inline_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "src": self.src,
            "type": self.script_type,
            "is_async": self.is_async,
            "is_defer": self.is_defer,
            "has_inline_code": bool(self.inline_code)
        }


@dataclass
class StyleModel:
    """
    HTML内の <style> 要素を表現するデータモデル。
    CSSHandler等にそのまま引き渡すための生コードを保持する。
    """
    code: str
    is_scoped: bool = False  # React化する際の CSS Modules や Styled Components 判定用

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "is_scoped": self.is_scoped,
            "length": len(self.code)
        }