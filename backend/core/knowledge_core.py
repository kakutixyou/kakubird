#　TO(と)/backend/core/knowledge_core.py
import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# =========================================================
# 1. Model (データ構造層)
# =========================================================
class BaseKnowledgeResult(BaseModel):
    """すべてのEngineが共通して返す解析結果のモデル"""
    score: int = Field(default=0, description="知識解析による適合スコア")
    complexity: int = Field(default=0, description="結果の複雑度（コンポーネント数など）")
    extracted_components: List[str] = Field(default_factory=list, description="抽出された主要要素")
    warnings: List[str] = Field(default_factory=list, description="解析時の警告リスト")
    meta: Dict[str, Any] = Field(default_factory=dict, description="ドメイン固有の追加データ")


# =========================================================
# 2. Provider (知識データ管理層)
# =========================================================
class BaseKnowledgeProvider:
    """JSONファイルからキーワードやルールを読み込み、キャッシュする"""
    def __init__(self, domain: str, memory_dir: str = "backend/.ai_memory"):
        self.domain = domain  # 例: "html", "css"
        self.filepath = os.path.join(memory_dir, f"{domain}_keywords.json")
        self._rules_cache: Optional[dict] = None

    def load_rules(self) -> dict:
        """JSONを読み込み、キャッシュして返す"""
        if self._rules_cache is not None:
            return self._rules_cache
            
        if not os.path.exists(self.filepath):
            print(f"⚠️ 辞書ファイルが見つかりません: {self.filepath}")
            self._rules_cache = {}
            return self._rules_cache

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self._rules_cache = json.load(f)
        except Exception as e:
            print(f"⚠️ {self.domain}のルール読み込みエラー: {e}")
            self._rules_cache = {}
            
        return self._rules_cache


# =========================================================
# 3. Engine (解析ロジック層)
# =========================================================
class BaseEngine(ABC):
    """
    解析の共通パイプライン（Template Method パターン）を提供する基底クラス。
    子クラスはドメイン固有の処理（extract_domain_featuresなど）だけを実装する。
    """
    def __init__(self, provider: BaseKnowledgeProvider):
        self.provider = provider
        self.rules = self.provider.load_rules()

    # --- 共通処理（そのまま使える） ---
    def normalize(self, text: str) -> str:
        """文字列の正規化（小文字化、不要な空白削除など）"""
        return " ".join(text.lower().split())

    def tokenize(self, text: str) -> List[str]:
        """文字列のトークン化（スペース区切りや記号での分割）"""
        # 必要に応じて正規表現などで高度化可能
        return text.split()

    def validate(self, text: str) -> bool:
        """最低限の入力チェック"""
        return bool(text and len(text.strip()) > 0)

    def build_result(self, score: int, complexity: int, extracted: List[str], warnings: List[str] = None) -> BaseKnowledgeResult:
        """結果モデルの構築"""
        return BaseKnowledgeResult(
            score=score,
            complexity=complexity,
            extracted_components=extracted,
            warnings=warnings or []
        )

    # --- 抽象メソッド（子クラスで専門知識を書く場所） ---
    @abstractmethod
    def calculate_score(self, text: str, tokens: List[str]) -> int:
        """辞書(self.rules)を使ってスコアを算出する"""
        pass

    @abstractmethod
    def estimate_complexity(self, extracted: List[str]) -> int:
        """抽出された要素から複雑度を算出する"""
        pass

    @abstractmethod
    def extract_domain_features(self, text: str, tokens: List[str]) -> List[str]:
        """専門知識の抽出（HTMLタグ、CSSプロパティなど）"""
        pass

    # --- 🌟 メインパイプライン（Handlerから呼ばれる唯一の窓口） ---
    def analyze(self, raw_text: str) -> BaseKnowledgeResult:
        """
        共通の処理フローを強制するメソッド。
        Handler はこの `analyze` メソッドだけを呼び出す。
        """
        warnings = []
        if not self.validate(raw_text):
            return self.build_result(0, 0, [], warnings=["Invalid or empty input"])

        # 1. 共通の前処理
        normalized = self.normalize(raw_text)
        tokens = self.tokenize(normalized)

        # 2. ドメイン固有の解析（子クラスの実装を呼ぶ）
        score = self.calculate_score(normalized, tokens)
        extracted = self.extract_domain_features(normalized, tokens)
        complexity = self.estimate_complexity(extracted)

        # 3. 共通の形式（KnowledgeResult）で返す
        return self.build_result(score, complexity, extracted, warnings)