from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class HTMLStatistics:
    """
    HTMLドキュメント（または特定の部分ツリー）全体のメトリクスを保持するデータモデル。
    MetricsAnalyzer によって計算され、最終的な品質評価や、
    React化する際のコンポーネント分割（チャンキング）の要否判定に利用される。
    """
    # --- 基礎ボリューム ---
    total_elements: int = 0
    max_depth: int = 0
    text_length: int = 0

    # --- 要素の出現頻度 ---
    tag_counts: Dict[str, int] = field(default_factory=dict)

    # --- 重要要素のカウント（ショートカット用） ---
    image_count: int = 0
    link_count: int = 0
    form_count: int = 0
    script_count: int = 0
    style_count: int = 0

    # --- 評価・品質指標 ---
    complexity_score: int = 0  # 総合的な複雑度スコア
    accessibility_warnings: List[str] = field(default_factory=list)
    performance_warnings: List[str] = field(default_factory=list)

    def add_tag(self, tag_name: str) -> None:
        """
        要素の集計を追加するヘルパーメソッド。
        DOMAnalyzerなどがツリーを走査する際に呼び出してカウントを蓄積する。
        """
        tag = tag_name.lower()
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        self.total_elements += 1

        # 特筆すべきコンポーネントのカウントをインクリメント
        if tag == "img":
            self.image_count += 1
        elif tag == "a":
            self.link_count += 1
        elif tag in ("form", "input", "select", "textarea"):
            self.form_count += 1
        elif tag == "script":
            self.script_count += 1
        elif tag == "style":
            self.style_count += 1

    def calculate_complexity(self) -> int:
        """
        現在の統計情報から、DOM構造の「複雑度スコア」を算出する。
        このスコアが高いほど、React等への変換時にバグが出やすく、分割が必要と判定される。
        """
        score = 0
        
        # 1. ボリュームによる加点（要素数とテキスト量）
        score += self.total_elements
        score += (self.text_length // 500)  # 500文字ごとに+1
        
        # 2. ネストの深さによるペナルティ（5階層を超えると急激に悪化）
        if self.max_depth > 5:
            score += (self.max_depth - 5) * 5
            
        # 3. 状態管理（State）が必要な要素による加点
        score += self.form_count * 5
        
        # 4. アンチパターン（インラインJS/CSS）のペナルティ
        score += (self.script_count + self.style_count) * 10

        self.complexity_score = score
        return score

    def suggest_react_chunking(self) -> bool:
        """
        このコンポーネントが肥大化しすぎているため、
        複数のサブコンポーネントに分割（チャンキング）すべきかを判定する。
        """
        # スコアが100を超える、またはネストが8階層を超える場合は分割を推奨
        return self.calculate_complexity() > 100 or self.max_depth > 8

    def add_warning(self, category: str, message: str) -> None:
        """
        解析中に発見された問題点（alt属性の欠如など）を記録する。
        """
        if category == "accessibility":
            self.accessibility_warnings.append(message)
        elif category == "performance":
            self.performance_warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """
        BaseKnowledgeResult にメタデータとして格納するためのシリアライズ。
        """
        # 辞書化するタイミングで最新の複雑度を計算しておく
        current_complexity = self.calculate_complexity()
        
        return {
            "volume": {
                "total_elements": self.total_elements,
                "max_depth": self.max_depth,
                "text_length": self.text_length,
            },
            "tag_counts": self.tag_counts,
            "key_elements": {
                "images": self.image_count,
                "links": self.link_count,
                "forms": self.form_count,
                "scripts": self.script_count,
                "styles": self.style_count
            },
            "metrics": {
                "complexity_score": current_complexity,
                "needs_chunking": self.suggest_react_chunking(),
            },
            "warnings": {
                "accessibility": self.accessibility_warnings,
                "performance": self.performance_warnings
            }
        }