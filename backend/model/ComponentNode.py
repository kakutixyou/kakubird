from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ComponentNode:
    """
    HTML解析プロセスにおいて、論理的なコンポーネント（UI部品のまとまり、
    カスタム要素、意味的なブロックなど）の構造化データを保持するデータモデル。
    
    コンポーネントツリーを形成するための親子関係の保持や、
    AI・後続のエンジンが扱いやすいメタデータ・統計情報の集約を担う。
    """

    # コンポーネントの基本識別情報
    name: str  # コンポーネント名 (例: "Card", "Navbar", "SubmitButton")
    component_type: str  # 分類 (例: "layout", "atom", "molecule", "organism", "custom")
    
    # DOM上の識別情報
    element_id: Optional[str] = None  # HTMLの id 属性（存在する場合）
    classes: List[str] = field(default_factory=list)  # HTMLの class 属性のリスト

    # コンポーネントツリー構造
    parent: Optional[ComponentNode] = field(default=None, repr=False)  # 親ノード（無限再帰を防ぐためreprから除外）
    children: List[ComponentNode] = field(default_factory=list)  # 子ノードのリスト

    # 解析によって得られた詳細データ
    attributes: Dict[str, str] = field(default_factory=dict)  # 保持している属性（data-* 属性やプロパティ等）
    inner_html: str = ""  # 内包する生のHTML文字列（部分木）
    inner_text: str = ""  # 内包するプレーンテキストの集約
    
    # 適用された解析ルールや特徴
    matched_rules: List[str] = field(default_factory=list)  # 抽出のトリガーとなったhtml_keywordsのルール名
    props_detected: Dict[str, Any] = field(default_factory=dict)  # 動的なPropsとして抽出されたキーと値の候補

    # メトリクス・評価情報
    complexity_score: int = 0  # このコンポーネント単体の複雑度スコア
    warnings: List[str] = field(default_factory=list)  # 解析中に検出された警告や最適化の余地（アクセシビリティ等）

    def add_child(self, child_node: ComponentNode) -> None:
        """
        自身に子コンポーネントノードを追加し、子ノードの親参照を自身に設定します。
        """
        child_node.parent = self
        self.children.append(child_node)

    def is_root(self) -> bool:
        """
        自身がコンポーネントツリーのルートノード（親を持たない要素）であるか判定します。
        """
        return self.parent is None

    def is_leaf(self) -> bool:
        """
        自身がリーフノード（子を持たない末端の要素）であるか判定します。
        """
        return len(self.children) == 0

    def get_depth(self) -> int:
        """
        コンポーネントツリー内における自身の深さ（ルートからの階層数）を取得します。
        """
        depth = 0
        current = self.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth

    def to_dict(self, include_children: bool = True) -> Dict[str, Any]:
        """
        ビルダーでのマージや、JSONへのシリアライズ、AIへのコンテキスト受け渡しを
        容易にするために、オブジェクトを純粋な辞書（Dict）形式に変換します。
        """
        result = {
            "name": self.name,
            "component_type": self.component_type,
            "element_id": self.element_id,
            "classes": self.classes,
            "depth": self.get_depth(),
            "attributes": self.attributes,
            "inner_text": self.inner_text.strip(),
            "matched_rules": self.matched_rules,
            "props_detected": self.props_detected,
            "complexity_score": self.complexity_score,
            "warnings": self.warnings,
        }

        if include_children:
            result["children"] = [child.to_dict(include_children=True) for child in self.children]
        
        return result

    def traverse(self) -> List[ComponentNode]:
        """
        自身を起点としたコンポーネントサブツリーを深さ優先探索（DFS）で平坦化し、
        全ノードのフラットなリストを返却します。
        """
        nodes = [self]
        for child in self.children:
            nodes.extend(child.traverse())
        return nodes