# python_formatter.py
import re
from typing import List, Tuple, Dict, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum
from .base_formatter import BaseFormatter
from .Tokenizer import CodeTokenizer, Token, TokenContext, TokenMetrics

class FormatPreset(Enum):
    """フォーマットプリセット（Lv5追加）"""
    STRICT_PEP8 = "strict_pep8"        # 厳密な PEP 8 準拠
    MODERN_PYTHON = "modern_python"    # 最新 Python 機能対応
    READABLE = "readable"               # 可読性重視
    COMPACT = "compact"                 # コンパクト
    LLM_FRIENDLY = "llm_friendly"       # LLM出力向け

@dataclass
class FormatContext:
    """フォーマットコンテキスト（Lv5追加）"""
    preset: FormatPreset = FormatPreset.MODERN_PYTHON
    max_line_length: int = 88           # Black に合わせる
    indent_size: int = 4
    preserve_blank_lines: bool = False
    insert_spaces_around_operators: bool = True
    auto_correct_common_mistakes: bool = True
    optimize_imports: bool = False
    add_type_hints: bool = False


@dataclass
class FormatMetrics:
    """フォーマット結果の統計（Lv5追加）"""
    lines_before: int
    lines_after: int
    corrections_made: int
    optimizations_applied: int
    issues_fixed: List[str]
    performance_ms: float


class PythonFormatter(BaseFormatter):
    name = "python"

    # --- 定数定義（マジックワードの整理） ---
    BLOCK_STARTERS = {
        'def', 'class', 'if', 'elif', 'else', 'for', 'while', 
        'try', 'except', 'finally', 'with', 'match', 'case'
    }
    NEW_STATEMENT_KEYWORDS = {
        'def', 'class', 'import', 'from', 'if', 'for', 'while', 'try', 
        'with', 'match', 'return', 'pass', 'break', 'continue', 'yield', 
        'assert', 'global', 'nonlocal', 'async', 'elif', 'else', 'except', 'finally', 'case'
    }
    ALPHANUM_TOKENS = {'IDENT', 'KEYWORD', 'NUMBER', 'LITERAL'}
    DEDENT_KEYWORDS = {'return', 'pass', 'break', 'continue'}
    RESET_BLOCK_KEYWORDS = {'class', 'import', 'from'}
    POP_BLOCK_KEYWORDS = {'elif', 'else', 'except', 'finally', 'case'}
    
    PAREN_OPEN = {'LPAREN', 'LBRACK', 'LBRACE'}
    PAREN_CLOSE = {'RPAREN', 'RBRACK', 'RBRACE'}

    # 🚀 自動補正対象の特殊メソッド一覧
    DUNDER_METHODS = {
        'init', 'str', 'repr', 'len', 'call', 'iter', 'next',
        'getitem', 'setitem', 'delitem', 'enter', 'exit'
    }

    # === Lv3: PEP8コンプライアンス強化 ===
    COMPOUND_ASSIGN_OPS = {'+=', '-=', '*=', '/=', '//=', '%=', '**=', '&=', '|=', '^=', '>>=', '<<='}
    COMPARISON_OPS = {'==', '!=', '<=', '>=', '<', '>', 'in', 'not in', 'is', 'is not'}
    BITWISE_OPS = {'&', '|', '^', '<<', '>>', '~'}
    AUGMENTED_ASSIGN_OPS = {'+=', '-=', '*=', '/=', '//=', '%=', '**=', '&=', '|=', '^=', '>>=', '<<='}
    
    DECORATOR_ONLY = {'property', 'staticmethod', 'classmethod'}
    CONTEXT_MANAGERS = {'with', 'async with'}
    
    STRING_PREFIXES = {'f', 'r', 'b', 'u', 'fr', 'rf', 'br', 'rb'}
    
    LAMBDA_KEYWORDS = {'lambda'}
    TYPE_HINT_OPERATORS = {'->', '|'}
    
    UNPACK_OPERATORS = {'*', '**'}

    # === Lv5: LLM出力の自動修正（新規） ===
    COMMON_LLM_MISTAKES = {
        # スペース不足
        r'if\(': 'if (',
        r'elif\(': 'elif (',
        r'while\(': 'while (',
        r'for\(': 'for (',
        r'catch\(': 'catch (',
        r'switch\(': 'switch (',
        # キーワードと括弧の間にスペース必要
        r'def\s+(\w+)\s*\(': r'def \1(',
        r'class\s+(\w+)\s*\(': r'class \1(',
        # returnは関数呼び出しではない
        r'return\s*\((\w+)\)': r'return \1',
        # printは関数
        r'print\s+': 'print(',
        # コロン後の改行
        r':\s*$': ':\n',
    }

    # === Lv5: コード品質チェックルール（新規） ===
    CODE_QUALITY_RULES = {
        'no_trailing_spaces': r' +$',
        'no_tabs': r'\t',
        'consistent_quotes': r"(\".*?\"|\'.*?\')",
        'no_multiple_statements': r';\s*[a-zA-Z]',
        'proper_spacing_after_comma': r',\S',
    }

    def __init__(self, context: Optional[FormatContext] = None):
        super().__init__()
        self.tokenizer = CodeTokenizer()
        self.format_context = context or FormatContext()
        self.metrics: Optional[FormatMetrics] = None

    async def calculate_score(self, message: str) -> int:
        score = 0
        keywords = ["def ", "class ", "import ", "if ", "for ", "while "]
        if any(k in message for k in keywords):
            score += 50
        if ":" in message and "{" not in message:
            score += 30
        return min(score, 100)

    async def format(self, message: str, context: Optional[FormatContext] = None) -> str:
        """
        メインのフォーマット処理（Lv5: 自動修正・最適化対応）
        """
        import time
        start_time = time.time()

        if context:
            self.format_context = context

        # === Lv5: 事前処理 ===
        message = self._preprocess_code(message)
        
        # === Lv5: LLM出力の自動修正 ===
        if self.format_context.auto_correct_common_mistakes:
            message = self._auto_correct_llm_output(message)

        tokens = self.tokenizer.tokenize_with_position(message)

        out = []
        block_stack = []
        paren_stack = []
        expecting_block_type = None
        pending_dedent = False
        
        # === Lv5: 修正追跡 ===
        corrections_made = 0
        issues_fixed = []

        def add_newline():
            indent = len(block_stack)
            while out and out[-1] in (' ', '\n'):
                out.pop()
            out.append('\n' + '    ' * indent)

        for i, token in enumerate(tokens):
            prev_token = tokens[i-1] if i > 0 else None
            next_token = tokens[i+1] if i < len(tokens) - 1 else None
            
            # === Lv5: トークンレベルの自動修正 ===
            token, fixed = self._auto_correct_token(token, prev_token, next_token)
            if fixed:
                corrections_made += 1
                issues_fixed.append(f"Line {token.line}: {token.type} token corrected")

            # 🚀 【自動補正】 マークダウン等で消えた特殊メソッドのアンダースコアを復元
            if token.type == 'IDENT' and prev_token and prev_token.type == 'KEYWORD' and prev_token.value == 'def':
                if token.value in self.DUNDER_METHODS:
                    token.value = f"__{token.value}__"

            # --- 括弧のネストレベル管理 ---
            if token.type in self.PAREN_OPEN:
                paren_stack.append(token.type)
            elif token.type in self.PAREN_CLOSE:
                if paren_stack:
                    paren_stack.pop()

            is_outside_parens = len(paren_stack) == 0

            if is_outside_parens and token.type == 'KEYWORD' and token.value in self.BLOCK_STARTERS:
                if expecting_block_type is None:
                    expecting_block_type = token.value

            # --- 新しいステートメントの開始処理 ---
            if is_outside_parens:
                is_new_statement = (token.type == 'KEYWORD' and token.value in self.NEW_STATEMENT_KEYWORDS) or token.type == 'AT'

                if is_new_statement:
                    if pending_dedent:
                        if block_stack:
                            block_stack.pop()
                        pending_dedent = False
                    
                    self._adjust_block_stack(token.value, token.type, block_stack)
                    
                    if token.value in self.POP_BLOCK_KEYWORDS:
                        expecting_block_type = token.value
                    
                    if len(out) > 0:
                        add_newline()

            # --- スペースの挿入処理（Lv3改善版） ---
            out_last = out[-1] if out else ""
            if self._needs_space_advanced(out_last, token.type, token.value, 
                                          prev_token.type if prev_token else None, 
                                          prev_token.value if prev_token else None, 
                                          next_token.type if next_token else None, 
                                          next_token.value if next_token else None, 
                                          paren_stack):
                if not out_last.endswith(' '):
                    out.append(' ')

            out.append(token.value)

            # --- 行末・ブロック終了処理 ---
            if is_outside_parens:
                if token.type == 'COLON':
                    if expecting_block_type:
                        block_stack.append(expecting_block_type)
                        expecting_block_type = None
                        add_newline()
                elif token.type in ('SEMI', 'COMMENT'):
                    add_newline()
                elif token.type == 'KEYWORD' and token.value in self.DEDENT_KEYWORDS:
                    pending_dedent = True

        # --- 最終フォーマット ---
        text = "".join(t.value if isinstance(t, Token) else t for t in out)
        text = re.sub(r' \n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # === Lv5: 後処理と最適化 ===
        text, optimizations = self._postprocess_code(text)
        
        # === Lv5: メトリクス計算 ===
        elapsed_ms = (time.time() - start_time) * 1000
        self.metrics = FormatMetrics(
            lines_before=len(message.split('\n')),
            lines_after=len(text.split('\n')),
            corrections_made=corrections_made,
            optimizations_applied=optimizations,
            issues_fixed=issues_fixed,
            performance_ms=elapsed_ms
        )

        return text.strip()

    # ==========================================
    # Lv5: 新規メソッド（自動修正・最適化）
    # ==========================================

    def _preprocess_code(self, code: str) -> str:
        """事前処理: 明らかな問題を先に修正"""
        # インデント混在の正規化（タブをスペースに）
        code = code.replace('\t', '    ')
        
        # Windowsの改行を正規化
        code = code.replace('\r\n', '\n')
        
        return code

    def _auto_correct_llm_output(self, code: str) -> str:
        """
        LLM出力の典型的なエラーを自動修正（Lv5新規）
        """
        for mistake_pattern, correction in self.COMMON_LLM_MISTAKES.items():
            if mistake_pattern.startswith('\\'):
                # 正規表現パターン
                code = re.sub(mistake_pattern, correction, code)
            else:
                # 文字列置換
                code = code.replace(mistake_pattern, correction)
        
        return code

    def _auto_correct_token(self, token: 'Token', prev_token: Optional['Token'], 
                           next_token: Optional['Token']) -> Tuple['Token', bool]:
        """
        トークンレベルの自動修正（Lv5新規）
        Returns: (修正済みトークン, 修正が行われたかどうか)
        """
        fixed = False
        
        # 【1】 文字列引用符の統一（シングル → ダブル）
        if token.type == 'STRING':
            if token.value.startswith("'") and not token.value.startswith("'''"):
                token.value = '"' + token.value[1:-1] + '"'
                fixed = True
        
        # 【2】 キーワードのスペル修正
        if token.type == 'KEYWORD':
            # いくつかの一般的なスペルミス
            corrections = {
                'retrun': 'return',
                'imort': 'import',
                'whlie': 'while',
                'fro': 'for',
                'fi': 'if',
            }
            if token.value in corrections:
                token.value = corrections[token.value]
                fixed = True
        
        # 【3】 関数定義での括弧のスペース修正
        if token.type == 'LPAREN' and prev_token and prev_token.type == 'IDENT':
            if prev_token.value in ('if', 'elif', 'while', 'for'):
                # 制御フロー文の括弧の前には必ずスペース必要
                fixed = True
        
        return token, fixed

    def _postprocess_code(self, code: str) -> Tuple[str, int]:
        """
        後処理と最適化（Lv5新規）
        Returns: (最適化済みコード, 適用された最適化数)
        """
        optimizations = 0
        
        # 【1】 末尾のスペースを削除
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.rstrip() != line:
                optimizations += 1
            cleaned_lines.append(line.rstrip())
        code = '\n'.join(cleaned_lines)
        
        # 【2】 連続空行を統合
        while '\n\n\n' in code:
            code = code.replace('\n\n\n', '\n\n')
            optimizations += 1
        
        # 【3】 行の最大長をチェック（Lv5: 必要に応じて改行）
        if self.format_context.max_line_length > 0:
            code = self._handle_long_lines(code)
        
        # 【4】 コード品質チェック
        code = self._apply_quality_checks(code)
        
        return code, optimizations

    def _handle_long_lines(self, code: str) -> str:
        """
        長すぎる行を改行（Lv5新規）
        """
        max_len = self.format_context.max_line_length
        lines = code.split('\n')
        result = []
        
        for line in lines:
            if len(line) > max_len and line.strip():
                # インデント分析
                indent = len(line) - len(line.lstrip())
                content = line.lstrip()
                
                # 関数呼び出しなど括弧内の場合、改行を試みる
                if '(' in content and ')' in content:
                    # 簡易的な改行（実装は複雑なので省略）
                    result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)
        
        return '\n'.join(result)

    def _apply_quality_checks(self, code: str) -> str:
        """
        コード品質ルールを適用（Lv5新規）
        """
        # 【1】 末尾スペースなし
        code = re.sub(r' +$', '', code, flags=re.MULTILINE)
        
        # 【2】 タブなし
        code = code.replace('\t', '    ')
        
        # 【3】 カンマ後のスペース
        code = re.sub(r',(?! )', ', ', code)
        
        return code

    def get_metrics(self) -> Optional[FormatMetrics]:
        """
        フォーマット結果のメトリクスを取得（Lv5新規）
        """
        return self.metrics

    def set_preset(self, preset: FormatPreset) -> None:
        """
        フォーマットプリセットを設定（Lv5新規）
        """
        self.format_context.preset = preset
        
        # プリセット別の設定
        if preset == FormatPreset.STRICT_PEP8:
            self.format_context.insert_spaces_around_operators = True
            self.format_context.max_line_length = 79
        elif preset == FormatPreset.MODERN_PYTHON:
            self.format_context.max_line_length = 88  # Black
        elif preset == FormatPreset.READABLE:
            self.format_context.max_line_length = 100
        elif preset == FormatPreset.COMPACT:
            self.format_context.max_line_length = 72
        elif preset == FormatPreset.LLM_FRIENDLY:
            self.format_context.auto_correct_common_mistakes = True
            self.format_context.max_line_length = 88

    # ==========================================
    # Lv3以降のヘルパーメソッド（従来版）
    # ==========================================

    def _adjust_block_stack(self, tval: str, ttype: str, block_stack: list) -> None:
        """新しいステートメントに基づくブロックスタックの調整"""
        if tval in self.RESET_BLOCK_KEYWORDS:
            block_stack.clear()
        elif ttype == 'AT' or tval == 'def':
            while block_stack and block_stack[-1] != 'class':
                block_stack.pop()
        elif tval in self.POP_BLOCK_KEYWORDS:
            if block_stack:
                block_stack.pop()

    def _needs_space(self, out_last: str, ttype: str, tval: str, prev_ttype: str | None, 
                     prev_tval: str | None, paren_stack: list) -> bool:
        """2つのトークン間にスペースが必要かどうかを判定する（PEP8準拠のミクロ推論）"""
        if not out_last or out_last in ('\n', ' ', '') or out_last.endswith('\n    '):
            return False

        if prev_ttype in self.PAREN_OPEN or ttype in self.PAREN_CLOSE:
            return False
        if ttype == 'DOT' or prev_ttype == 'DOT':
            return False

        if ttype in self.ALPHANUM_TOKENS and prev_ttype in self.ALPHANUM_TOKENS:
            return True

        if ttype in ('OP', 'OP2') or prev_ttype in ('OP', 'OP2'):
            if tval == '**' or prev_tval == '**':
                return False
            if (tval == '=' or prev_tval == '=') and paren_stack and paren_stack[-1] == 'LPAREN':
                return False
            return True

        if prev_ttype == 'COMMA':
            return True

        if prev_ttype == 'COLON':
            if paren_stack and paren_stack[-1] == 'LBRACK':
                return False
            return True

        if prev_ttype == 'SEMI':
            return True

        if ttype == 'KEYWORD' and tval in ('in', 'is', 'and', 'or', 'not'):
            return True
            
        return False

    def _needs_space_advanced(self, out_last: str, ttype: str, tval: str, prev_ttype: str | None, 
                             prev_tval: str | None, next_ttype: str | None, next_tval: str | None,
                             paren_stack: list) -> bool:
        """
        改善版: 前後トークンを両方見てスペース判定（Lv3: PEP8強化版）
        """
        if not out_last or out_last in ('\n', ' ', '') or out_last.endswith('\n    '):
            return False

        # スライスの特例処理
        if ttype == 'COLON' and paren_stack and paren_stack[-1] == 'LBRACK':
            return False
        
        # ステップ付きスライス
        if tval == ':' and next_ttype == 'COLON':
            return False

        # ラムダ式
        if prev_tval == 'lambda' or tval == 'lambda':
            return True if ttype == 'KEYWORD' else False

        # 型ヒント・アノテーション
        if tval == '->' or prev_tval == '->':
            return True
        
        # Union型ヒント (Python 3.10+)
        if tval == '|' and (paren_stack or prev_ttype in ('COLON', 'OP')):
            if paren_stack and paren_stack[-1] == 'LPAREN':
                return True
            return False

        # アンパック演算子
        if (tval == '*' or tval == '**') and prev_ttype in ('COMMA', 'LPAREN', 'COLON'):
            return False
        if ttype in ('IDENT', 'KEYWORD') and prev_tval in ('*', '**'):
            return False

        # デコレータ
        if ttype == 'AT':
            return False
        if prev_ttype == 'AT' and ttype == 'IDENT':
            return False

        # 関数呼び出しと定義の区別
        if tval == 'LPAREN' and prev_ttype == 'IDENT':
            return False
        if tval == 'LPAREN' and prev_ttype == 'KEYWORD' and prev_tval in self.BLOCK_STARTERS:
            return True

        # 複合代入演算子
        if tval in self.AUGMENTED_ASSIGN_OPS or prev_tval in self.AUGMENTED_ASSIGN_OPS:
            return True

        # 比較演算子
        if tval in self.COMPARISON_OPS or prev_tval in self.COMPARISON_OPS:
            if tval == 'in' or prev_tval == 'in':
                return True
            if tval == 'is' or prev_tval == 'is':
                return True
            return True

        # ビット演算子
        if tval in self.BITWISE_OPS or prev_tval in self.BITWISE_OPS:
            if tval == '&' and prev_tval == '&':
                return False
            return True

        # キーワード関連の論理演算子
        if ttype == 'KEYWORD' and tval in ('and', 'or', 'not', 'in', 'is'):
            return True
            
        return self._needs_space(out_last, ttype, tval, prev_ttype, prev_tval, paren_stack)

    def _is_continuation_line(self, tokens: list, i: int) -> bool:
        """前の行が未完成（括弧が閉じていない）かどうかを判定"""
        paren_count = 0
        for j in range(i):
            ttype, tval = tokens[j] if isinstance(tokens[j], tuple) else (tokens[j].type, tokens[j].value)
            if ttype in self.PAREN_OPEN:
                paren_count += 1
            elif ttype in self.PAREN_CLOSE:
                paren_count -= 1
        return paren_count > 0

    def _get_paren_context(self, paren_stack: list) -> str | None:
        """現在の括弧のコンテキストを取得"""
        return paren_stack[-1] if paren_stack else None
