from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import urllib.parse


@dataclass
class LinkModel:
    """
    HTMLの <a> 要素（アンカー）を表現する高度なデータモデル。
    React Router や Next.js の <Link> コンポーネントへの変換を見据え、
    内部/外部リンクの判定、セキュリティ（noopener）、ルーティングの最適化を行う。
    """
    # --- 基本属性 ---
    href: Optional[str] = None
    text: str = ""
    target: Optional[str] = None
    rel: Optional[str] = None
    
    # --- その他の生属性 ---
    attributes: Dict[str, str] = field(default_factory=dict)

    # --- 解析による自動判定メタデータ (init=False) ---
    is_external: bool = field(init=False, default=False)
    is_anchor: bool = field(init=False, default=False)
    is_mailto_or_tel: bool = field(init=False, default=False)
    react_router_compatible: bool = field(init=False, default=True)
    has_security_issue: bool = field(init=False, default=False)
    parsed_path: Optional[str] = field(init=False, default=None)

    def __post_init__(self) -> None:
        """
        インスタンス生成時に、hrefの値やtarget属性から
        SPAルーティングの可否やセキュリティ上の問題を自動解析する。
        """
        if not self.href:
            self.react_router_compatible = False
            return

        # 1. mailto: や tel: の判定
        if self.href.startswith(("mailto:", "tel:")):
            self.is_mailto_or_tel = True
            self.react_router_compatible = False
            return

        # 2. ページ内リンク（#アンカー）の判定
        if self.href.startswith("#"):
            self.is_anchor = True
            self.react_router_compatible = False  # SPAでは通常の<a>か専用のスクロール処理を使うため
            return

        # 3. 外部リンクの判定
        if self.href.startswith(("http://", "https://", "//")):
            self.is_external = True
            self.react_router_compatible = False

        # 4. セキュリティチェック (Reverse Tabnabbing 対策)
        # target="_blank" なのに rel="noopener" または "noreferrer" がない場合は危険と判定
        if self.target == "_blank":
            rel_str = str(self.rel or "").lower()
            if "noopener" not in rel_str and "noreferrer" not in rel_str:
                self.has_security_issue = True

        # 5. パスのパース（内部リンクの場合、クエリパラメータやハッシュを分離）
        if self.react_router_compatible:
            parsed = urllib.parse.urlparse(self.href)
            self.parsed_path = parsed.path

    def to_nextjs_link_props(self) -> Dict[str, Any]:
        """
        Next.jsの <Link> コンポーネント（または標準の <a> タグ）に
        直接渡せるPropsの形式に変換し、セキュリティ問題も自動修復するヘルパー。
        """
        props: Dict[str, Any] = {
            "href": self.href or "#",
        }
        if self.target:
            props["target"] = self.target
        
        # セキュリティ問題の自動修復：
        # target="_blank" の場合、強制的に noopener noreferrer を付与する
        if self.target == "_blank":
            existing_rel = set((self.rel or "").split())
            existing_rel.update(["noopener", "noreferrer"])
            # 空文字を除去して結合
            props["rel"] = " ".join(filter(None, existing_rel))
        elif self.rel:
            props["rel"] = self.rel
            
        return props

    def to_dict(self) -> Dict[str, Any]:
        """
        KnowledgeBuilderのメタデータとして集約するための辞書化。
        """
        return {
            "href": self.href,
            "text": self.text,
            "target": self.target,
            "rel": self.rel,
            "routing_info": {
                "is_external": self.is_external,
                "is_anchor": self.is_anchor,
                "is_mailto_or_tel": self.is_mailto_or_tel,
                "react_router_compatible": self.react_router_compatible,
                "parsed_path": self.parsed_path
            },
            "warnings": {
                "security_issue": self.has_security_issue
            },
            "attributes": self.attributes
        }