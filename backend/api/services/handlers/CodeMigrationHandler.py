import json
from typing import Tuple, Any
from datetime import datetime
from .base_handler import BaseHandler
from core.job_database import get_all_jobs
from .base_handler import BaseHandler
class CodeMigrationHandler(BaseHandler):
    def __init__(self):
        self.keywords = ["jsx", "react", "変換", "移行", "リプレイス", "コンバート"]

    def calculate_score(self, text: str, signals: dict) -> int:
        score = 0
        text_lower = text.lower()
        
        # 「HTML」と「JSX/React」がセットで出現した場合はマイグレーション意図が極めて高い
        if "html" in text_lower and any(k in text_lower for k in ["jsx", "react"]):
            score += 90
            
        # 「〜に変えたい」「〜に変換」などの動詞による加算
        if any(k in text_lower for k in ["変えたい", "変更", "変換", "移行"]):
            score += 15
            
        return min(score, 100)