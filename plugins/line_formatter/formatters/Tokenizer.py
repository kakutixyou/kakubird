# Tokenizer.py
import re
from typing import List, Tuple, Dict, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any
# ==== 型定義 ====

class TokenContext(Enum):
    """トークンのコンテキスト分類"""
    NORMAL = "normal"
    IN_FUNCTION = "in_function"
    IN_CLASS = "in_class"
    IN_DECORATOR = "in_decorator"
    IN_FSTRING = "in_fstring"
    IN_COMMENT = "in_comment"
    IN_DOCSTRING = "in_docstring"


@dataclass
class Token:
    """拡張トークン情報（Lv3: 位置情報とコンテキスト付き）"""
    type: str
    value: str
    line: int
    col: int
    context: TokenContext = TokenContext.NORMAL
    nesting_level: int = 0  # 括弧のネストレベル
    is_continuation: bool = False  # 行継続フラグ


@dataclass
class TokenMetrics:
    """トークン複雑度分析結果"""
    total_tokens: int
    unique_token_types: int
    max_nesting_level: int
    f_string_count: int
    decorator_count: int
    function_count: int
    class_count: int
    comment_ratio: float
    syntax_errors: List[str]
    longest_line_tokens: int


class CodeTokenizer:
    """
    インデントが壊れたPythonコードでもパースできる、強化版字句解析器。
    新しい構文やリテラル、複合演算子に対応し、PythonFormatterが高度な推論を行える基盤を提供します。
    
    Lv3改善: 位置情報、コンテキスト追跡、複雑度分析、エラーリカバリー機能を追加
    """

    # --- 定数・正規表現の事前コンパイル（クラスレベル） ---
    _PREPROCESS_RE = re.compile(
        r'(#.+?)\s+(?=(?:async |def |class |if |import |from |@[a-zA-Z_]|[A-Z_0-9]+\s*=))'
    )

    # === Lv3: 三重引用符と f文字列の拡張対応 ===
    _TRIPLE_QUOTED_STR_RE = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')')
    _FSTRING_PATTERN = re.compile(r'[fF]r?[\'\"]')

    _TOKEN_SPECIFICATION = [
        # === Lv3: 三重引用符の追加対応 ===
        ('DOCSTRING', r'(?:"""(?:\\.|[^\\])*?"""|\'\'\'(?:\\.|[^\\])*?\'\'\')'),
        
        ('STRING',    r'(?:[fFrRbBuU]*"(?:\\.|[^"\\])*"|[fFrRbBuU]*\'(?:\\.|[^\'\\])*\')'),
        ('COMMENT',   r'#.*'),
        ('KEYWORD',   r'\b(?:def|class|if|elif|else|for|while|try|except|finally|with|return|yield|import|from|pass|break|continue|and|or|not|is|in|as|assert|del|global|nonlocal|lambda|async|await|match|case)\b'),
        ('LITERAL',   r'\b(?:True|False|None)\b'),
        ('NUMBER',    r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?:j|J)?\b'),
        ('IDENT',     r'[a-zA-Z_]\w*'),
        
        # === Lv3: 複合演算子と Walrus演算子（:=）の正式対応 ===
        ('OP2',       r'==|!=|<=|>=|:=|\+=|-=|\*=|/=|//=|%=|&=|\|=|\^=|<<=|>>=|\*\*|//|<<|>>|->|\.\.\.'),
        ('OP',        r'[+\-*/%=<>&|^~!]'),
        
        ('COLON',     r':'),
        ('LPAREN',    r'\('),
        ('RPAREN',    r'\)'),
        ('LBRACK',    r'\['),
        ('RBRACK',    r'\]'),
        ('LBRACE',    r'\{'),
        ('RBRACE',    r'\}'),
        ('COMMA',     r','),
        ('DOT',       r'\.'),
        ('SEMI',      r';'),
        ('AT',        r'@'),
        ('SPACE',     r'[ \t]+'),
        ('NEWLINE',   r'\n'),
        ('MISC',      r'.'),
    ]

    # トークン解析用の正規表現を一度だけ結合・コンパイルする
    _TOKEN_REGEX = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in _TOKEN_SPECIFICATION))
    
    # 抽出から除外するトークンの種類
    _IGNORE_TOKENS = {'SPACE', 'NEWLINE'}

    # === Lv3: キーワード定義の拡張 ===
    _BLOCK_STARTING_KEYWORDS = {'def', 'class', 'if', 'elif', 'for', 'while', 'with', 'try'}
    _CONTEXT_STARTING_KEYWORDS = {'class', 'def', 'async'}
    _DECORATOR_KEYWORDS = {'property', 'staticmethod', 'classmethod'}

    def __init__(self):
        """初期化"""
        self.tokens: List[Token] = []
        self.errors: List[str] = []
        self.line_token_counts: Dict[int, int] = {}
        self.current_context: TokenContext = TokenContext.NORMAL

    def tokenize(self, code_string: str) -> List[Tuple[str, str]]:
        """
        元のシンプルなインターフェース（後方互換性を保つ）
        """
        tokens = self.tokenize_with_position(code_string)
        return [(token.type, token.value) for token in tokens]

    def tokenize_with_position(self, code_string: str) -> List[Token]:
        """
        拡張版: 位置情報・コンテキスト・ネストレベル付きトークンを返す（Lv3追加）
        """
        self.tokens = []
        self.errors = []
        self.line_token_counts = {}

        # 前処理: コメントが後続コードを飲み込まないよう処理
        code_string = self._PREPROCESS_RE.sub(r'\1\n', code_string)

        lines = code_string.split('\n')
        paren_stack = []
        nesting_level = 0
        current_context = TokenContext.NORMAL
        in_docstring = False

        for line_no, line in enumerate(lines, 1):
            col = 0
            line_tokens = 0

            # === Lv3: ドキュメンテーション文字列の検出 ===
            if '"""' in line or "'''" in line:
                docstring_matches = re.finditer(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', line)
                for match in docstring_matches:
                    in_docstring = not in_docstring

            for match in self._TOKEN_REGEX.finditer(line):
                token_type = match.lastgroup
                token_value = match.group(token_type) if token_type else ""

                if token_type not in self._IGNORE_TOKENS:
                    # === Lv3: ネストレベルの更新 ===
                    if token_type in ('LPAREN', 'LBRACK', 'LBRACE'):
                        paren_stack.append(token_type)
                        nesting_level += 1
                    elif token_type in ('RPAREN', 'RBRACK', 'RBRACE'):
                        if paren_stack:
                            paren_stack.pop()
                        nesting_level = max(0, nesting_level - 1)

                    # === Lv3: コンテキストの更新 ===
                    if token_type == 'KEYWORD' and token_value in self._CONTEXT_STARTING_KEYWORDS:
                        if token_value == 'class':
                            current_context = TokenContext.IN_CLASS
                        elif token_value == 'def':
                            current_context = TokenContext.IN_FUNCTION
                        elif token_value == 'async':
                            current_context = TokenContext.NORMAL

                    if token_type == 'AT':
                        current_context = TokenContext.IN_DECORATOR

                    # === Lv3: f文字列のコンテキスト ===
                    if token_type == 'STRING' and re.match(r'[fF]', token_value):
                        current_context = TokenContext.IN_FSTRING

                    if token_type == 'DOCSTRING':
                        current_context = TokenContext.IN_DOCSTRING

                    if token_type == 'COMMENT':
                        current_context = TokenContext.IN_COMMENT

                    # トークンオブジェクトを作成
                    token = Token(
                        type=token_type or '',
                        value=token_value,
                        line=line_no,
                        col=match.start(),
                        context=current_context,
                        nesting_level=nesting_level,
                        is_continuation=len(paren_stack) > 0
                    )

                    self.tokens.append(token)
                    line_tokens += 1

            self.line_token_counts[line_no] = line_tokens

        # === Lv3: 検証とエラー検出 ===
        self._validate_tokens()

        return self.tokens

    def tokenize_with_recovery(self, code_string: str) -> List[Token]:
        """
        エラーリカバリーモード: シンタックスエラーがあっても処理を続ける（Lv3追加）
        """
        tokens = self.tokenize_with_position(code_string)

        # 括弧のアンバランスを修正
        if self.errors:
            # エラーを記録するが、トークン化は継続
            pass

        return tokens

    def validate_tokens(self, tokens: Optional[List[Token]] = None) -> Tuple[bool, List[str]]:
        """
        トークン列の妥当性を検証する（Lv3追加）
        Returns: (is_valid, error_list)
        """
        if tokens is None:
            tokens = self.tokens

        errors = []
        paren_stack = []
        paren_pairs = {'LPAREN': 'RPAREN', 'LBRACK': 'RBRACK', 'LBRACE': 'RBRACE'}

        for token in tokens:
            if token.type in ('LPAREN', 'LBRACK', 'LBRACE'):
                paren_stack.append((token.type, token.line, token.col))

            elif token.type in ('RPAREN', 'RBRACK', 'RBRACE'):
                if not paren_stack:
                    errors.append(f"Line {token.line}: 対応する開き括弧がありません: {token.value}")
                else:
                    opening = paren_stack.pop()
                    expected_close = paren_pairs[opening[0]]
                    if paren_pairs.get(opening[0]) != f"R{opening[0][1:]}":
                        errors.append(f"Line {token.line}: 括弧の型が一致しません")

        # 閉じられていない括弧
        for opening, line, col in paren_stack:
            errors.append(f"Line {line}, Col {col}: 閉じられていない括弧: {opening}")

        self.errors = errors
        return len(errors) == 0, errors

    def analyze_complexity(self) -> TokenMetrics:
        """
        コード複雑度を分析する（Lv3追加）
        """
        if not self.tokens:
            return TokenMetrics(0, 0, 0, 0, 0, 0, 0, 0.0, [], 0)

        # 基本統計
        total_tokens = len(self.tokens)
        unique_types = len(set(t.type for t in self.tokens))
        max_nesting = max((t.nesting_level for t in self.tokens), default=0)

        # 特定トークンのカウント
        f_string_count = sum(1 for t in self.tokens if t.type == 'STRING' and re.match(r'[fF]', t.value))
        decorator_count = sum(1 for t in self.tokens if t.type == 'AT')
        function_count = sum(1 for t in self.tokens if t.type == 'KEYWORD' and t.value == 'def')
        class_count = sum(1 for t in self.tokens if t.type == 'KEYWORD' and t.value == 'class')

        # コメント比率
        comment_tokens = sum(1 for t in self.tokens if t.type == 'COMMENT')
        comment_ratio = comment_tokens / total_tokens if total_tokens > 0 else 0.0

        # 最長行のトークン数
        longest_line_tokens = max(self.line_token_counts.values(), default=0)

        metrics = TokenMetrics(
            total_tokens=total_tokens,
            unique_token_types=unique_types,
            max_nesting_level=max_nesting,
            f_string_count=f_string_count,
            decorator_count=decorator_count,
            function_count=function_count,
            class_count=class_count,
            comment_ratio=comment_ratio,
            syntax_errors=self.errors,
            longest_line_tokens=longest_line_tokens
        )

        return metrics

    def _validate_tokens(self) -> None:
        """内部メソッド: トークン列の検証"""
        paren_stack = []
        paren_pairs = {'LPAREN': 'RPAREN', 'LBRACK': 'RBRACK', 'LBRACE': 'RBRACE'}

        for token in self.tokens:
            if token.type in ('LPAREN', 'LBRACK', 'LBRACE'):
                paren_stack.append((token.type, token.line, token.col))

            elif token.type in ('RPAREN', 'RBRACK', 'RBRACE'):
                if not paren_stack:
                    self.errors.append(f"Line {token.line}, Col {token.col}: 対応する開き括弧がありません ({token.value})")
                else:
                    opening_type, _, _ = paren_stack.pop()
                    expected_close_type = paren_pairs[opening_type]
                    close_map = {'RPAREN': 'LPAREN', 'RBRACK': 'LBRACK', 'RBRACE': 'LBRACE'}

                    if close_map.get(token.type) != opening_type:
                        self.errors.append(f"Line {token.line}, Col {token.col}: 括弧の型が一致しません")

        # 閉じられていない括弧
        for opening_type, line, col in paren_stack:
            bracket_char = {'LPAREN': '(', 'LBRACK': '[', 'LBRACE': '{'}[opening_type]
            self.errors.append(f"Line {line}, Col {col}: 閉じられていない括弧 ({bracket_char})")

    def get_token_at_position(self, line: int, col: int) -> Optional[Token]:
        """
        指定行・列のトークンを取得（Lv3追加）
        """
        for token in self.tokens:
            if token.line == line and token.col <= col < token.col + len(token.value):
                return token
        return None

    def get_tokens_by_type(self, token_type: str) -> List[Token]:
        """
        特定の型のトークンをすべて取得（Lv3追加）
        """
        return [t for t in self.tokens if t.type == token_type]

    def get_tokens_by_context(self, context: TokenContext) -> List[Token]:
        """
        特定のコンテキストのトークンをすべて取得（Lv3追加）
        """
        return [t for t in self.tokens if t.context == context]

    def print_token_tree(self) -> str:
        """
        トークンツリーを可視化（デバッグ用、Lv3追加）
        """
        lines = []
        current_line = -1

        for token in self.tokens:
            if token.line != current_line:
                lines.append(f"\n--- Line {token.line} ---")
                current_line = token.line

            indent = "  " * token.nesting_level
            context_str = f"[{token.context.value}]" if token.context != TokenContext.NORMAL else ""
            continuation = "[cont]" if token.is_continuation else ""

            lines.append(f"{indent}{token.type:10} | {repr(token.value):20} | col={token.col:3} {context_str} {continuation}")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """
        トークン統計情報を取得（Lv3追加）
        """
        if not self.tokens:
            return {}

        type_counts = {}
        for token in self.tokens:
            type_counts[token.type] = type_counts.get(token.type, 0) + 1

        return {
            'total_tokens': len(self.tokens),
            'unique_types': len(type_counts),
            'type_distribution': type_counts,
            'total_lines': max((t.line for t in self.tokens), default=0),
            'avg_tokens_per_line': len(self.tokens) / max((t.line for t in self.tokens), default=1),
            'max_nesting_level': max((t.nesting_level for t in self.tokens), default=0),
            'syntax_errors': len(self.errors),
            'has_fstrings': any(t.type == 'STRING' and re.match(r'[fF]', t.value) for t in self.tokens),
            'has_docstrings': any(t.type == 'DOCSTRING' for t in self.tokens),
        }
