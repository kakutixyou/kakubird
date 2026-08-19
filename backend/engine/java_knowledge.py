import json
import re
from pathlib import Path
from typing import Any, Dict, Set, Optional
from dataclasses import dataclass, field

@dataclass
class JavaKnowledgeData:
    """読み込んだ知識を保持するデータクラス"""
    keywords: Dict[str, Any] = field(default_factory=dict)
    modifiers: Dict[str, Any] = field(default_factory=dict)
    types: Dict[str, Any] = field(default_factory=dict)
    patterns: Dict[str, Any] = field(default_factory=dict)
    semantics: Dict[str, Any] = field(default_factory=dict)
    compiled_patterns: Dict[str, re.Pattern] = field(default_factory=dict)

class JavaKnowledgeLoader:
    """Javaの知識（JSON）を一括で読み込み、管理するシングルトン的なローダー"""
    
    _instance: Optional['JavaKnowledgeLoader'] = None

    def __new__(cls, knowledge_dir: str | Path):
        # 1回だけ読み込む仕組み（シングルトンパターン）
        if cls._instance is None:
            cls._instance = super(JavaKnowledgeLoader, cls).__new__(cls)
            cls._instance._initialize(knowledge_dir)
        return cls._instance

    def _initialize(self, knowledge_dir: str | Path):
        self.base_dir = Path(knowledge_dir)
        self.data = JavaKnowledgeData()
        
        # 各JSONのロード
        self.data.keywords = self._load_json("java_keywords.json")
        self.data.modifiers = self._load_json("java_modifiers.json")
        self.data.types = self._load_json("java_types.json")
        self.data.patterns = self._load_json("java_patterns.json")
        self.data.semantics = self._load_json("java_semantics.json")
        
        # 正規表現のコンパイル
        self.data.compiled_patterns = self._compile_patterns(self.data.patterns)

    def _load_json(self, filename: str) -> Dict[str, Any]:
        file_path = self.base_dir / filename
        if not file_path.exists():
            print(f"[Warning] Knowledge file not found: {file_path}")
            return {}
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[Error] Failed to parse JSON in {filename}: {e}")
            return {}

    def _compile_patterns(self, patterns_config: Dict[str, Any]) -> Dict[str, re.Pattern]:
        compiled = {}
        for name, config in patterns_config.items():
            if not isinstance(config, dict):
                continue
                
            pattern_str = config.get("pattern")
            if not pattern_str:
                continue
                
            flags = 0
            for flag_name in config.get("flags", []):
                flag = getattr(re, flag_name, None)
                if flag is not None:
                    flags |= flag
                    
            try:
                compiled[name] = re.compile(pattern_str, flags)
            except re.error as e:
                print(f"[JavaKnowledge] Regex error in pattern '{name}': {e}", flush=True)
                
        return compiled

    # --- アクセスメソッド ---

    def get_pattern(self, name: str) -> Optional[re.Pattern]:
        return self.data.compiled_patterns.get(name)

    def get_semantic_meaning(self, category: str, key: str) -> str:
        """意味情報を取得（LLMに渡す用）"""
        return self.data.semantics.get(category, {}).get(key, "")