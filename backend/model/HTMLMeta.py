from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class MetaTagModel:
    """
    個別の <meta> タグを表現する軽量モデル。
    """
    name: Optional[str] = None
    property: Optional[str] = None
    content: Optional[str] = None
    charset: Optional[str] = None
    http_equiv: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # Noneの項目を除外してスッキリとした辞書にする
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class HTMLMetaModel:
    """
    HTMLの <head> 内のメタ情報全体を集約・管理するデータモデル。
    生のメタタグを SEO, OGP (Open Graph Protocol), Twitter Cards など
    用途別に自動分類し、Next.js等のフレームワークでのメタデータ生成を容易にする。
    """
    # --- 基本情報 ---
    title: Optional[str] = None
    charset: str = "utf-8"
    viewport: str = "width=device-width, initial-scale=1.0"
    canonical_url: Optional[str] = None
    
    # --- SEO・標準メタデータ ---
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    
    # --- SNS・共有用メタデータ（自動振り分け） ---
    og_tags: Dict[str, str] = field(default_factory=dict)       # property="og:*" 
    twitter_tags: Dict[str, str] = field(default_factory=dict)  # name="twitter:*"
    
    # --- その他分類されない生タグ ---
    raw_meta_tags: List[MetaTagModel] = field(default_factory=list)

    def add_meta_tag(self, tag: MetaTagModel) -> None:
        """
        メタタグを追加し、その属性 (name や property) に応じて
        適切なカテゴリ (SEO, OGP, Twitter) へ自動的にルーティングする。
        """
        # 1. Charset
        if tag.charset:
            self.charset = tag.charset
            return

        # 2. Viewport
        if tag.name == "viewport" and tag.content:
            self.viewport = tag.content
            return

        # 3. Description
        if tag.name == "description" and tag.content:
            self.description = tag.content
            return

        # 4. Keywords
        if tag.name == "keywords" and tag.content:
            # カンマ区切りの文字列をリストに変換して空白除去
            self.keywords = [k.strip() for k in tag.content.split(",") if k.strip()]
            return

        # 5. OGP (Open Graph Protocol)
        if tag.property and tag.property.startswith("og:") and tag.content:
            key = tag.property.replace("og:", "")
            self.og_tags[key] = tag.content
            return

        # 6. Twitter Cards
        if tag.name and tag.name.startswith("twitter:") and tag.content:
            key = tag.name.replace("twitter:", "")
            self.twitter_tags[key] = tag.content
            return

        # 上記のどれにも当てはまらない特殊なタグは生リストへ
        self.raw_meta_tags.append(tag)

    def generate_nextjs_metadata(self) -> Dict[str, Any]:
        """
        Next.js (App Router) の generateMetadata() で要求される
        オブジェクト形式に極力近い形で出力するヘルパーメソッド。
        ReactHandlerがこれを受け取ることで、一瞬でコード化可能になる。
        """
        metadata = {
            "title": self.title,
            "description": self.description,
            "keywords": self.keywords,
        }
        if self.og_tags:
            metadata["openGraph"] = self.og_tags
        if self.twitter_tags:
            metadata["twitter"] = self.twitter_tags
            
        return {k: v for k, v in metadata.items() if v}

    def to_dict(self) -> Dict[str, Any]:
        """
        KnowledgeBuilderのメタデータとして集約するための辞書化。
        """
        return {
            "title": self.title,
            "charset": self.charset,
            "viewport": self.viewport,
            "canonical_url": self.canonical_url,
            "description": self.description,
            "keywords": self.keywords,
            "og_tags": self.og_tags,
            "twitter_tags": self.twitter_tags,
            "unclassified_tags": [tag.to_dict() for tag in self.raw_meta_tags]
        }