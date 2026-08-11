from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import urllib.parse


@dataclass
class ImageModel:
    """
    HTMLの <img> 要素を表現する高度なデータモデル。
    Next.jsの `next/image` 等への変換を見据え、外部ドメイン判定、
    Base64判定、レスポンシブ対応（srcset）などの自動解析機能を備える。
    """
    # --- 基本属性 ---
    src: Optional[str] = None
    alt: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    
    # --- パフォーマンス・レスポンシブ属性 ---
    loading: Optional[str] = None  # "lazy", "eager" など
    decoding: Optional[str] = None # "async", "sync", "auto"
    srcset: Optional[str] = None
    sizes: Optional[str] = None
    
    # --- その他の生属性 ---
    attributes: Dict[str, str] = field(default_factory=dict)

    # --- 解析による自動判定メタデータ (init=False) ---
    is_external: bool = field(init=False, default=False)
    is_base64: bool = field(init=False, default=False)
    external_domain: Optional[str] = field(init=False, default=None)
    aspect_ratio: Optional[float] = field(init=False, default=None)
    has_accessibility_issue: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        """
        インスタンス生成時に、src属性やwidth/heightから
        React変換時に必要なメタデータを自動計算する。
        """
        # 1. アクセシビリティチェック（altが空、または未設定）
        if self.alt is None or str(self.alt).strip() == "":
            self.has_accessibility_issue = True

        if self.src:
            # 2. Base64 (インライン画像) の判定
            if self.src.startswith("data:image/"):
                self.is_base64 = True
            
            # 3. 外部ドメインの判定（Next.jsの next.config.js 設定用などに利用）
            elif self.src.startswith(("http://", "https://")):
                self.is_external = True
                parsed_url = urllib.parse.urlparse(self.src)
                self.external_domain = parsed_url.netloc

        # 4. アスペクト比の計算（CLS: Cumulative Layout Shift 対策用）
        if self.width and self.height:
            try:
                # 'px' や '%' などの単位が含まれている場合を考慮し、数値のみ抽出して計算する簡易ロジック
                w_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', str(self.width))))
                h_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', str(self.height))))
                if h_val > 0:
                    self.aspect_ratio = round(w_val / h_val, 3)
            except ValueError:
                pass # 複雑な calc() などの場合はスキップ

    def to_nextjs_image_props(self) -> Dict[str, Any]:
        """
        Next.jsの <Image> コンポーネントに直接渡せるPropsの形式に変換するヘルパー。
        Handler層（ReactHandler等）でこの出力をそのままJSXにマッピングできる。
        """
        props: Dict[str, Any] = {
            "src": self.src,
            "alt": self.alt or "", # Next.jsではalt必須
        }
        
        if self.width and self.height:
            props["width"] = self.width
            props["height"] = self.height
        else:
            # width/heightが不明な場合は fill モードを推奨するフラグを立てる
            props["fill"] = True
            props["style"] = {"objectFit": "cover"}

        # 外部画像でサイズ指定がない、かつ fill でもない場合は警告を出すなど、
        # ここでフレームワーク特有の最適化ロジックを吸収できる
        return props

    def to_dict(self) -> Dict[str, Any]:
        """
        KnowledgeBuilderのメタデータとして集約するための辞書化。
        """
        return {
            "src": self.src,
            "alt": self.alt,
            "dimensions": {
                "width": self.width,
                "height": self.height,
                "aspect_ratio": self.aspect_ratio
            },
            "performance": {
                "loading": self.loading,
                "srcset": self.srcset,
                "sizes": self.sizes
            },
            "source_info": {
                "is_external": self.is_external,
                "external_domain": self.external_domain,
                "is_base64": self.is_base64
            },
            "warnings": {
                "accessibility_issue": self.has_accessibility_issue
            },
            "attributes": self.attributes
        }