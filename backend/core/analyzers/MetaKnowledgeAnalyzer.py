import ast
import tokenize
import io
import re
import json
from collections import defaultdict

class MetaKnowledgeAnalyzer:
    def __init__(self):
        self.todos = []
        self.specifications = defaultdict(dict)
        self.inline_comments = []

    def analyze_docstrings(self, source_code: str):
        """ASTを用いてクラスや関数のDocstring（仕様）を抽出"""
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node)
                if docstring:
                    node_type = "class" if isinstance(node, ast.ClassDef) else "function"
                    self.specifications[node_type][node.name] = docstring

    def analyze_comments(self, source_code: str):
        """tokenizeを用いてインラインコメントとTODOタグを抽出"""
        tokens = tokenize.generate_tokens(io.StringIO(source_code).readline)
        
        # 検出するキーワード
        todo_pattern = re.compile(r'#\s*(TODO|FIXME|HACK|NOTE|OPTIMIZE):\s*(.*)', re.IGNORECASE)

        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                comment_text = tok.string
                line_num = tok.start[0]
                
                # TODOやFIXMEの検出
                match = todo_pattern.search(comment_text)
                if match:
                    tag = match.group(1).upper()
                    content = match.group(2).strip()
                    self.todos.append({
                        "type": tag,
                        "line": line_num,
                        "content": content
                    })
                else:
                    # 通常のコメント
                    self.inline_comments.append({
                        "line": line_num,
                        "content": comment_text.lstrip('#').strip()
                    })

    def analyze(self, source_code: str, filename: str):
        self.analyze_docstrings(source_code)
        self.analyze_comments(source_code)
        
        return {
            "filename": filename,
            "technical_debt": self.todos,
            "specifications": dict(self.specifications),
            # 通常のコメントは多すぎる場合があるので、長さなどでフィルタリング推奨
            "key_comments": [c for c in self.inline_comments if len(c["content"]) > 20] 
        }

# --- テスト用コード ---
if __name__ == "__main__":
    sample_code = """
class PaymentProcessor:
    \"\"\"
    Stripe APIを利用して決済を処理するクラス。
    冪等性を担保するためにトランザクションIDを記録する。
    \"\"\"
    def __init__(self):
        # FIXME: 開発環境ではモックを使うように切り替えること
        self.api_key = "sk_test_123" 
        
    def process(self, amount):
        \"\"\"指定された金額を決済する\"\"\"
        # TODO: レートリミットのエラーハンドリングを追加する
        # このコメントは単なる補足説明です。短すぎるものは無視されます。
        pass
"""
    analyzer = MetaKnowledgeAnalyzer()
    result = analyzer.analyze(sample_code, "payment.py")
    print(json.dumps(result, indent=2, ensure_ascii=False))