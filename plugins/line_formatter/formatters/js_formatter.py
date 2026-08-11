import re
import time
from typing import List, Dict, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
from .base_formatter import BaseFormatter


class JsFormatPreset(Enum):
    """JavaScriptフォーマットプリセット（Lv5追加）"""
    STRICT_ESLINT = "strict_eslint"      # ESLint標準準拠
    PRETTIER_COMPAT = "prettier_compat"  # Prettier互換
    MODERN_ES6 = "modern_es6"            # ES6+機能活用
    REACT_JSX = "react_jsx"              # React/JSX最適化
    NODEJS_STYLE = "nodejs_style"        # Node.js慣例
    LLM_FRIENDLY = "llm_friendly"        # LLM出力向け


@dataclass
class JsFormatContext:
    """JavaScriptフォーマットコンテキスト（Lv5追加）"""
    preset: JsFormatPreset = JsFormatPreset.PRETTIER_COMPAT
    max_line_length: int = 80
    indent_size: int = 2
    use_semicolons: bool = True
    prefer_single_quotes: bool = False
    arrow_parens: str = "always"  # "always" or "avoid"
    preserve_blank_lines: bool = False
    auto_correct_common_mistakes: bool = True
    format_jsdoc: bool = True
    optimize_imports: bool = False
    add_type_hints: bool = False  # TypeScript対応


@dataclass
class JsFormatMetrics:
    """JavaScriptフォーマット結果の統計（Lv5追加）"""
    lines_before: int
    lines_after: int
    corrections_made: int
    optimizations_applied: int
    issues_fixed: List[str]
    jsx_components_found: int
    arrow_functions_found: int
    async_awaits_found: int
    template_literals_found: int
    performance_ms: float


@dataclass
class JsToken:
    """JavaScriptトークン情報（Lv5追加）"""
    type: str
    value: str
    line: int
    col: int
    nesting_level: int = 0
    is_jsx: bool = False
    context: str = "normal"


class JsFormatter(BaseFormatter):
    name = "js_like"

    # --- 定数定義（Lv5拡張） ---
    BLOCK_STARTERS = {
        'function', 'if', 'else', 'for', 'while', 'do', 'switch', 'try', 
        'catch', 'finally', 'class', 'async', 'await'
    }
    
    CONTROL_KEYWORDS = {
        'if', 'else', 'else if', 'for', 'while', 'do', 'switch', 'case', 
        'default', 'return', 'break', 'continue', 'throw', 'try', 'catch', 
        'finally', 'async', 'await', 'class', 'extends', 'static', 'const',
        'let', 'var', 'function', 'import', 'export', 'from', 'as'
    }
    
    COMPARISON_OPS = {'==', '!=', '===', '!==', '<=', '>=', '<', '>'}
    ARITHMETIC_OPS = {'+', '-', '*', '/', '%', '**'}
    ASSIGNMENT_OPS = {'=', '+=', '-=', '*=', '/=', '%=', '**=', '&&=', '||=', '??=', '=>'}
    LOGICAL_OPS = {'&&', '||', '??', '!'}
    BITWISE_OPS = {'&', '|', '^', '~', '<<', '>>', '>>>'}
    
    SPREAD_OPERATOR = '...'
    TEMPLATE_LITERAL = '`'
    ARROW_FUNCTION = '=>'
    
    JSX_TAGS_PATTERN = r'<[A-Z][a-zA-Z0-9]*|<\/[a-zA-Z]+'
    
    DESTRUCTURING_KEYWORDS = {'const', 'let', 'var'}
    ASYNC_KEYWORDS = {'async', 'await'}
    CLASS_KEYWORDS = {'class', 'extends', 'static', 'constructor'}
    
    # 改行が不要な特殊トークン
    NO_NEWLINE_AFTER = {'.', ',', '(', '[', '{'}
    NO_NEWLINE_BEFORE = {'.', ',', ')', ']', '}', ';', ':', '?'}

    # === Lv5: LLMの一般的なミス ==========
    COMMON_LLM_MISTAKES = {
        # スペース不足
        r'if\(': 'if (',
        r'for\(': 'for (',
        r'while\(': 'while (',
        r'switch\(': 'switch (',
        r'catch\(': 'catch (',
        # 関数定義
        r'function\s+(\w+)\s*\(': r'function \1(',
        r'const\s+(\w+)\s*=\s*\(': r'const \1 = (',
        # 矢印関数のスペース
        r'(\w+)\s*=>\s*': r'\1 => ',
        # セミコロン
        r'(?<!\{)$': ';',  # 行末にセミコロン追加
        # 括弧のバランス
        r'\(\s+\(': '((',
        r'\)\s+\)': '))',
    }

    # === Lv5: JSDoc/コメント形式 ==========
    JSDOC_PATTERN = r'/\*\*[\s\S]*?\*/'

    def __init__(self, context: Optional[JsFormatContext] = None):
        super().__init__()
        self.format_context = context or JsFormatContext()
        self.metrics: Optional[JsFormatMetrics] = None
        self.tokens: List[JsToken] = []

    async def calculate_score(self, message: str) -> int:
        score = 0
        
        # 基本的な構文検出
        if "{" in message and "}" in message:
            score += 40
        if ";" in message:
            score += 30
        
        # JavaScript キーワード
        if any(k in message for k in ["function", "=>", "const ", "let ", "var "]):
            score += 30
        
        # === Lv3+: 追加の検出ロジック ===
        if "=>" in message:
            score += 20
        if "`" in message:
            score += 15
        if "..." in message:
            score += 15
        if "async" in message or "await" in message:
            score += 20
        if "class " in message:
            score += 25
        if "[" in message and "]" in message:
            score += 10
        if ":" in message:
            score += 10
        
        if re.search(self.JSX_TAGS_PATTERN, message):
            score += 25
        
        return min(score, 100)

    async def format(self, message: str, context: Optional[JsFormatContext] = None) -> str:
        """
        メインのフォーマット処理（Lv5: 自動修正・最適化対応）
        """
        start_time = time.time()

        if context:
            self.format_context = context

        # === Lv5: 事前処理 ===
        message = self._preprocess_code(message)
        
        # === Lv5: LLM出力の自動修正 ===
        if self.format_context.auto_correct_common_mistakes:
            message = self._auto_correct_llm_output(message)

        result = []
        indent = 0
        buf = ""
        in_string = None
        in_template = False
        in_regex = False
        in_comment = False
        in_jsdoc = False
        
        paren_stack = []
        jsx_tag_stack = []
        
        # === Lv5: 修正追跡 ===
        corrections_made = 0
        jsx_count = 0
        arrow_func_count = 0
        async_await_count = 0
        template_count = 0
        issues_fixed = []

        def flush():
            nonlocal buf
            s = buf.strip()
            if s:
                result.append("  " * indent + s)
            buf = ""

        def should_add_newline(prev_ch: str, curr_ch: str) -> bool:
            """現在の文字の前に改行を入れるべきか判定（Lv5改善版）"""
            if prev_ch in self.NO_NEWLINE_AFTER:
                return False
            if curr_ch in self.NO_NEWLINE_BEFORE:
                return False
            if paren_stack:
                return False
            return True

        def is_jsx_tag(text: str) -> bool:
            """JSXタグか判定（Lv5改善）"""
            return bool(re.match(r'^<[A-Z]', text.strip()))

        def is_arrow_function(text: str) -> bool:
            """アロー関数か判定（Lv5追加）"""
            return '=>' in text

        # === Lv5: トークン化と分析 ===
        i = 0
        while i < len(message):
            ch = message[i]

            # ========== JSDoc コメント処理（Lv5追加） ==========
            if ch == '/' and i + 1 < len(message) and message[i+1] == '*':
                if i + 2 < len(message) and message[i+2] == '*':
                    # JSDoc開始
                    in_jsdoc = True
                    j = i + 3
                    while j < len(message) - 1:
                        if message[j] == '*' and message[j+1] == '/':
                            j += 2
                            break
                        j += 1
                    buf += message[i:j]
                    i = j
                    continue

            # ========== テンプレートリテラル処理 =========
            if in_template:
                buf += ch
                if ch == '`' and (i == 0 or message[i-1] != '\\'):
                    in_template = False
                    template_count += 1
                i += 1
                continue

            # ========== 文字列処理 =========
            if in_string:
                buf += ch
                if ch == in_string and (i == 0 or message[i-1] != '\\'):
                    in_string = None
                i += 1
                continue

            if ch in ('"', "'"):
                in_string = ch
                buf += ch
                i += 1
                continue

            if ch == '`':
                in_template = True
                buf += ch
                i += 1
                continue

            # ========== 正規表現処理（Lv5改善） =========
            if ch == '/' and i + 1 < len(message):
                if i > 0 and message[i-1] in '=([,;:!&|?':
                    j = i + 1
                    while j < len(message) and message[j] != '/':
                        if message[j] == '\\':
                            j += 2
                        else:
                            j += 1
                    if j < len(message):
                        buf += message[i:j+1]
                        i = j + 1
                        continue

            # ========== 括弧スタック管理（Lv5改善） =========
            if ch == '(':
                paren_stack.append('(')
                buf += ch
                i += 1
                continue
            elif ch == '[':
                paren_stack.append('[')
                buf += ch
                i += 1
                continue
            elif ch == '{':
                paren_stack.append('{')
                buf += ch
                
                # JSX タグ内の式判定
                if jsx_tag_stack and buf.count('{') - buf.count('}') > 0:
                    pass
                
                flush()
                indent += 1
                i += 1
                continue

            elif ch == ')':
                if paren_stack and paren_stack[-1] == '(':
                    paren_stack.pop()
                buf += ch
                i += 1
                continue
            elif ch == ']':
                if paren_stack and paren_stack[-1] == '[':
                    paren_stack.pop()
                buf += ch
                i += 1
                continue
            elif ch == '}':
                if paren_stack and paren_stack[-1] == '{':
                    paren_stack.pop()
                
                flush()
                indent = max(0, indent - 1)
                buf += ch
                flush()
                i += 1
                continue

            # ========== セミコロン処理（Lv5改善） =========
            elif ch == ';':
                buf += ch
                flush()
                i += 1
                continue

            # ========== コンマ処理（Lv5追加） =========
            elif ch == ',':
                buf += ch
                if i + 1 < len(message) and message[i+1] != '\n':
                    buf += ' '
                i += 1
                continue

            # ========== JSX タグ処理（Lv5改善） =========
            elif ch == '<' and i + 1 < len(message):
                if re.match(r'[A-Z]|\/[a-z]', message[i+1]):
                    # 閉じタグ
                    if message[i+1] == '/':
                        match_tag = re.match(r'<\/([a-zA-Z]+)>', message[i:])
                        if match_tag:
                            tag_content = match_tag.group(0)
                            buf += tag_content
                            if jsx_tag_stack and jsx_tag_stack[-1] == match_tag.group(1):
                                jsx_tag_stack.pop()
                            issues_fixed.append(f"Line {len(result)}: JSX閉じタグ認識")
                            i += len(tag_content)
                            continue
                    # 開きタグ
                    else:
                        match_tag = re.match(r'<([A-Z][a-zA-Z0-9]*)[^>]*>', message[i:])
                        if match_tag:
                            tag_content = match_tag.group(0)
                            buf += tag_content
                            jsx_tag_stack.append(match_tag.group(1))
                            jsx_count += 1
                            if tag_content.endswith('/>'):
                                jsx_tag_stack.pop()
                            issues_fixed.append(f"Line {len(result)}: JSX開きタグ認識")
                            i += len(tag_content)
                            continue

            # ========== アロー関数検出（Lv5追加） =========
            elif ch == '=' and i + 1 < len(message) and message[i+1] == '>':
                buf += '=>'
                arrow_func_count += 1
                i += 2
                continue

            # ========== async/await検出（Lv5追加） =========
            elif ch.isalpha():
                # キーワード検出
                j = i
                while j < len(message) and (message[j].isalnum() or message[j] == '_'):
                    j += 1
                word = message[i:j]
                
                if word == 'async' or word == 'await':
                    async_await_count += 1
                    buf += word
                    i = j
                    continue
                else:
                    buf += ch
                    i += 1
                    continue

            # ========== デフォルト処理 =========
            else:
                buf += ch
                i += 1
                continue

        flush()
        result_text = "\n".join(result)
        
        # === Lv5: 後処理と最適化 ===
        result_text, optimizations = self._postprocess_code(result_text)
        
        # === Lv5: 引用符の統一 ===
        if not self.format_context.prefer_single_quotes:
            result_text = self._normalize_quotes(result_text)
        
        # === Lv5: セミコロンの処理 ===
        if self.format_context.use_semicolons:
            result_text = self._ensure_semicolons(result_text)
        
        # === Lv5: メトリクス計算 ===
        elapsed_ms = (time.time() - start_time) * 1000
        self.metrics = JsFormatMetrics(
            lines_before=len(message.split('\n')),
            lines_after=len(result_text.split('\n')),
            corrections_made=corrections_made,
            optimizations_applied=optimizations,
            issues_fixed=issues_fixed,
            jsx_components_found=jsx_count,
            arrow_functions_found=arrow_func_count,
            async_awaits_found=async_await_count,
            template_literals_found=template_count,
            performance_ms=elapsed_ms
        )

        return result_text.strip()

    # ==========================================
    # Lv5: 新規メソッド（自動修正・最適化）
    # ==========================================

    def _preprocess_code(self, code: str) -> str:
        """事前処理: 明らかな問題を先に修正（Lv5新規）"""
        # Windowsの改行を正規化
        code = code.replace('\r\n', '\n')
        
        # タブをスペースに統一
        code = code.replace('\t', '  ' * self.format_context.indent_size // 2)
        
        return code

    def _auto_correct_llm_output(self, code: str) -> str:
        """
        LLM出力の典型的なエラーを自動修正（Lv5新規）
        """
        for mistake_pattern, correction in self.COMMON_LLM_MISTAKES.items():
            if mistake_pattern.startswith('\\'):
                try:
                    code = re.sub(mistake_pattern, correction, code, flags=re.MULTILINE)
                except:
                    pass
            else:
                code = code.replace(mistake_pattern, correction)
        
        return code

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
        
        # 【3】 演算子周辺のスペース調整
        code = self._normalize_operator_spacing(code)
        
        # 【4】 行の最大長をチェック
        if self.format_context.max_line_length > 0:
            code = self._handle_long_lines(code)
        
        return code, optimizations

    def _normalize_operator_spacing(self, text: str) -> str:
        """演算子周辺のスペースを正規化（Lv5新規）"""
        
        # 二項演算子にスペースを確保
        for op in ['===', '!==', '==', '!=', '<=', '>=']:
            text = re.sub(rf'\s*{re.escape(op)}\s*', f' {op} ', text)
        
        # 論理演算子
        for op in ['&&', '||', '??']:
            text = re.sub(rf'\s*{re.escape(op)}\s*', f' {op} ', text)
        
        # 算術演算子（単項との区別に注意）
        text = re.sub(r'(\w|\))\s*\+\s*(\w|\()', r'\1 + \2', text)
        text = re.sub(r'(\w|\))\s*-\s*(\w|\()', r'\1 - \2', text)
        text = re.sub(r'(\w|\))\s*\*\s*(\w|\()', r'\1 * \2', text)
        text = re.sub(r'(\w|\))\s*/\s*(\w|\()', r'\1 / \2', text)
        
        # 代入演算子
        text = re.sub(r'\s*([+\-*/]?=)\s*', r' \1 ', text)
        
        # アロー関数
        text = re.sub(r'\s*=>\s*', ' => ', text)
        
        return text

    def _normalize_quotes(self, code: str) -> str:
        """引用符を統一（Lv5新規）"""
        # シングルクォートをダブルクォートに統一
        # ただし、テンプレートリテラル内は除外
        lines = []
        for line in code.split('\n'):
            if '`' not in line:
                # 簡易的な置換（実装を簡素化）
                if self.format_context.prefer_single_quotes:
                    line = line.replace('"', "'")
                else:
                    line = line.replace("'", '"')
            lines.append(line)
        return '\n'.join(lines)

    def _ensure_semicolons(self, code: str) -> str:
        """セミコロンを確保（Lv5新規）"""
        lines = code.split('\n')
        result = []
        
        for line in lines:
            stripped = line.rstrip()
            
            # セミコロンが必要な行か判定
            if stripped and not stripped.endswith((';', '{', '}', ')', ',', '//')):
                # 制御フロー文の後はセミコロン不要
                if not any(stripped.strip().endswith(kw) for kw in ('if', 'else', 'for', 'while', 'do', 'try', 'catch', 'finally')):
                    if self.format_context.use_semicolons:
                        stripped += ';'
            
            result.append(stripped)
        
        return '\n'.join(result)

    def _handle_long_lines(self, code: str) -> str:
        """
        長すぎる行を処理（Lv5新規）
        """
        max_len = self.format_context.max_line_length
        lines = code.split('\n')
        result = []
        
        for line in lines:
            if len(line) > max_len and line.strip():
                # 簡易的な改行（実装は複雑）
                result.append(line)
            else:
                result.append(line)
        
        return '\n'.join(result)

    def _cleanup_formatting(self, text: str) -> str:
        """後処理: 余分なスペースや改行を整理（Lv5改善）"""
        
        # 連続空行を1行に統一
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 末尾の不要なスペース削除
        text = re.sub(r' +\n', '\n', text)
        
        # 行頭の不要なスペース削除（インデント済みなので）
        text = re.sub(r'\n {5,}', '\n', text)
        
        return text

    def _detect_jsx_component(self, text: str) -> bool:
        """JSX コンポーネントかどうかを判定（Lv5追加）"""
        return bool(re.search(self.JSX_TAGS_PATTERN, text))

    def _count_braces(self, text: str) -> Tuple[int, int]:
        """テキスト内の開き括弧と閉じ括弧をカウント（Lv5追加）"""
        open_count = text.count('{')
        close_count = text.count('}')
        return open_count, close_count

    def _is_valid_indent_level(self, indent: int) -> bool:
        """インデントレベルが妥当か判定（Lv5追加）"""
        return indent >= 0

    def _extract_jsx_attributes(self, tag_text: str) -> Dict[str, str]:
        """
        JSX タグから属性を抽出（Lv5追加）
        例: <Component className="foo" onClick={handleClick} />
        """
        attributes = {}
        
        # 属性パターン: name="value" または name={expression}
        attr_pattern = r'(\w+)=(?:"([^"]*)"|{([^}]*)})'
        matches = re.findall(attr_pattern, tag_text)
        
        for name, string_value, expr_value in matches:
            attributes[name] = string_value if string_value else f"{{{expr_value}}}"
        
        return attributes

    def _is_arrow_function_line(self, line: str) -> bool:
        """行がアロー関数定義か判定（Lv5追加）"""
        return '=>' in line and not line.strip().startswith('//')

    def _should_preserve_formatting(self, line: str) -> bool:
        """このような行はフォーマットを保持すべきか判定（Lv5追加）"""
        # コメント行
        if line.strip().startswith('//') or line.strip().startswith('/*'):
            return True
        # 文字列リテラル行
        if line.count('"') % 2 == 1 or line.count("'") % 2 == 1:
            return True
        return False

    def get_metrics(self) -> Optional[JsFormatMetrics]:
        """
        フォーマット結果のメトリクスを取得（Lv5新規）
        """
        return self.metrics

    def set_preset(self, preset: JsFormatPreset) -> None:
        """
        フォーマットプリセットを設定（Lv5新規）
        """
        self.format_context.preset = preset
        
        # プリセット別の設定
        if preset == JsFormatPreset.STRICT_ESLINT:
            self.format_context.use_semicolons = True
            self.format_context.indent_size = 2
            self.format_context.max_line_length = 80
        
        elif preset == JsFormatPreset.PRETTIER_COMPAT:
            self.format_context.use_semicolons = False
            self.format_context.indent_size = 2
            self.format_context.max_line_length = 80
        
        elif preset == JsFormatPreset.MODERN_ES6:
            self.format_context.arrow_parens = "avoid"
            self.format_context.max_line_length = 88
        
        elif preset == JsFormatPreset.REACT_JSX:
            self.format_context.format_jsdoc = True
            self.format_context.indent_size = 2
            self.format_context.max_line_length = 100
        
        elif preset == JsFormatPreset.NODEJS_STYLE:
            self.format_context.use_semicolons = True
            self.format_context.prefer_single_quotes = True
            self.format_context.indent_size = 2
        
        elif preset == JsFormatPreset.LLM_FRIENDLY:
            self.format_context.auto_correct_common_mistakes = True
            self.format_context.use_semicolons = True
            self.format_context.max_line_length = 88

    def get_statistics(self) -> Dict[str, any]:
        """
        フォーマット統計情報を取得（Lv5追加）
        """
        if not self.metrics:
            return {}
        
        return {
            'total_lines': self.metrics.lines_after,
            'jsx_components': self.metrics.jsx_components_found,
            'arrow_functions': self.metrics.arrow_functions_found,
            'async_awaits': self.metrics.async_awaits_found,
            'template_literals': self.metrics.template_literals_found,
            'corrections': self.metrics.corrections_made,
            'optimizations': self.metrics.optimizations_applied,
            'processing_time_ms': self.metrics.performance_ms,
            'line_reduction': self.metrics.lines_before - self.metrics.lines_after
        }

    def validate_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """
        JavaScriptの基本的な構文検証（Lv5追加）
        """
        errors = []
        
        # 括弧のバランスチェック
        paren_count = code.count('(') - code.count(')')
        brack_count = code.count('[') - code.count(']')
        brace_count = code.count('{') - code.count('}')
        
        if paren_count != 0:
            errors.append(f"括弧のバランスが取れていません: {paren_count}")
        if brack_count != 0:
            errors.append(f"角括弧のバランスが取れていません: {brack_count}")
        if brace_count != 0:
            errors.append(f"中括弧のバランスが取れていません: {brace_count}")
        
        # 文字列のバランスチェック
        if code.count('"') % 2 != 0:
            errors.append("ダブルクォートのバランスが取れていません")
        if code.count("'") % 2 != 0:
            errors.append("シングルクォートのバランスが取れていません")
        if code.count('`') % 2 != 0:
            errors.append("バックティックのバランスが取れていません")
        
        return len(errors) == 0, errors
