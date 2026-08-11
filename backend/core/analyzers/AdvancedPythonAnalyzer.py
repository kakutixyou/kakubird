import ast
import json
from collections import defaultdict

class AdvancedPythonAnalyzer(ast.NodeVisitor):
    def __init__(self):
        # 現在解析中のスコープ（グローバル、または関数名）を追跡
        self.current_scope = "global"
        
        # 関数呼び出しの依存関係 (関数名 -> 呼び出している関数のリスト)
        self.call_graph = defaultdict(list)
        
        # 変数のトラッキング (関数名 -> {定義された変数, 参照された変数})
        self.variables = defaultdict(lambda: {"defined": set(), "used": set()})

    def visit_FunctionDef(self, node):
        """関数定義に入った時の処理。スコープを切り替える"""
        previous_scope = self.current_scope
        self.current_scope = node.name
        
        # 関数内部を解析
        self.generic_visit(node)
        
        # 解析が終わったら元のスコープに戻す
        self.current_scope = previous_scope

    def visit_Call(self, node):
        """関数呼び出し（依存関係）の抽出"""
        func_name = "<unknown>"
        
        if isinstance(node.func, ast.Name):
            # 通常の関数呼び出し (例: print(), len())
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # メソッド呼び出し (例: self.GF(), kzg.generate_proof())
            try:
                func_name = ast.unparse(node.func)
            except AttributeError:
                # Python 3.8以前のフォールバック
                func_name = f"{node.func.value.id}.{node.func.attr}" if isinstance(node.func.value, ast.Name) else node.func.attr

        self.call_graph[self.current_scope].append(func_name)
        
        # 引数の中の関数呼び出しなども解析するため継続
        self.generic_visit(node)

    def visit_Name(self, node):
        """変数の状態（代入か、参照か）を抽出"""
        # node.ctx でその変数がどう使われているか判定できる
        if isinstance(node.ctx, ast.Store):
            # 代入されている (Store)
            self.variables[self.current_scope]["defined"].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # 参照されている (Load)
            self.variables[self.current_scope]["used"].add(node.id)
            
        self.generic_visit(node)

    def get_analysis_result(self):
        """抽出したデータをJSON化可能な辞書に変換"""
        result = {
            "call_graph": {k: list(set(v)) for k, v in self.call_graph.items()},
            "variables_by_scope": {}
        }
        
        for scope, var_data in self.variables.items():
            result["variables_by_scope"][scope] = {
                "defined": list(var_data["defined"]),
                "used": list(var_data["used"])
            }
        return result

# --- テスト用の実行コード ---
if __name__ == "__main__":
    # 解析対象のサンプルコード（KZGコードの一部を簡略化）
    sample_code = """
class KZGCommitment:
    def evaluate_at_trusted_setup(self, polynomial, trusted_setup):
        limit = polynomial.degree + 1
        trusted_setup = trusted_setup[:limit]
        return reduce(add, (multiply(p, c) for p, c in zip(trusted_setup, polynomial.coeffs)), Z1)

    def commit_polynomial(self, polynomial):
        result = self.evaluate_at_trusted_setup(polynomial, self.trusted_setup_g1)
        return result
"""
    
    analyzer = AdvancedPythonAnalyzer()
    tree = ast.parse(sample_code)
    analyzer.visit(tree)
    
    print(json.dumps(analyzer.get_analysis_result(), indent=2))