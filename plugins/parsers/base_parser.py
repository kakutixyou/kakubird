#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
base_parser.py
==============

すべてのコードParserが継承する基底クラス。

役割:
    - Parser共通インターフェースの定義
    - 絶対パス入力の統一
    - ファイル読み込みの共通化
    - 解析結果フォーマットの統一
    - エラー形式の統一
    - Symbol情報生成Utilityの提供
    - Parser統計情報の生成

想定する子クラス:
    - PythonParser
    - JavaScriptParser
    - JavaParser
    - TypeScriptParser
    - CSSParser
    - HTMLParser

設計方針:
    Parser:
        「コードに何が書かれているか」を解析する。

    Analyzer:
        「そのコードが何を意味するか」
        「問題があるか」
        「依存関係はどうか」
        などを解析する。

    BaseParserは言語固有のAST処理を持たない。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging


logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    すべてのコードParserが継承する基底クラス。

    子クラスは最低限、

        language
        supported_extensions
        parse()

    を実装する。

    Example:

        class PythonParser(BaseParser):

            language = "python"
            supported_extensions = {".py"}

            def parse(self, file_path):
                ...
    """

    # ---------------------------------------------------------
    # Parser基本情報
    # ---------------------------------------------------------

    language: str = "unknown"

    parser_version: str = "1.0"

    supported_extensions: set[str] = set()

    def __init__(self) -> None:

        self.errors: List[Dict[str, Any]] = []

    # =========================================================
    # 必須実装
    # =========================================================

    @abstractmethod
    def parse_file(
        self,
        file_path: str | Path,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    def parse_code(
        self,
        code: str,
        *,
        source_name: str = "<chat>",
    ) -> Dict[str, Any]:
        ...
    @abstractmethod
    def parse(
        self,
        file_path: str | Path,
    ) -> Dict[str, Any]:
        """
        絶対パスで指定されたソースコードを解析する。

        Parameters
        ----------
        file_path:
            解析対象ファイルの絶対パス。

        Returns
        -------
        Dict[str, Any]

        共通形式:

            {
                "ok": True,

                "language": "python",

                "parser": {
                    "name": "PythonParser",
                    "version": "1.0"
                },

                "classes": [],
                "functions": [],
                "methods": [],
                "variables": [],
                "imports": [],
                "exports": [],
                "interfaces": [],
                "dependencies": [],
                "calls": [],

                "metadata": {},

                "stats": {},

                "errors": []
            }
        """

        raise NotImplementedError(
            "parse() must be implemented by subclass."
        )

    # =========================================================
    # ファイル入力
    # =========================================================

    def validate_file_path(
        self,
        file_path: str | Path,
    ) -> Optional[Path]:
        """
        解析対象ファイルを検証する。

        方針:
            - 絶対パスのみ許可
            - 存在確認
            - 通常ファイルのみ許可
            - supported_extensions が設定されていれば拡張子確認

        成功:
            resolve済みPathを返す。

        失敗:
            errorsに追加してNoneを返す。
        """

        if file_path is None:
            self.add_error(
                "ファイルパスが指定されていません。",
                error_type="invalid_path",
            )
            return None

        try:

            path = Path(file_path)

        except (TypeError, ValueError) as exc:

            self.add_error(
                "ファイルパスをPathへ変換できません。",
                error_type="invalid_path",
                details={
                    "value": str(file_path),
                    "exception": str(exc),
                },
            )

            return None

        # -----------------------------------------------------
        # 絶対パスのみ許可
        # -----------------------------------------------------

        if not path.is_absolute():

            self.add_error(
                f"絶対パスを指定してください: {file_path}",
                error_type="relative_path_not_allowed",
            )

            return None

        # -----------------------------------------------------
        # 存在確認
        # -----------------------------------------------------

        if not path.exists():

            self.add_error(
                f"ファイルが存在しません: {path}",
                error_type="file_not_found",
            )

            return None

        # -----------------------------------------------------
        # ファイル確認
        # -----------------------------------------------------

        if not path.is_file():

            self.add_error(
                f"指定されたパスはファイルではありません: {path}",
                error_type="not_file",
            )

            return None

        # -----------------------------------------------------
        # 拡張子
        # -----------------------------------------------------

        suffix = path.suffix.lower()

        if (
            self.supported_extensions
            and suffix not in self.supported_extensions
        ):

            self.add_error(
                f"未対応の拡張子です: {suffix}",
                error_type="unsupported_extension",
                details={
                    "supported_extensions": sorted(
                        self.supported_extensions
                    )
                },
            )

            return None

        try:

            return path.resolve()

        except OSError as exc:

            self.add_error(
                f"ファイルパスを解決できません: {path}",
                error_type="path_resolution_error",
                details={
                    "exception": str(exc),
                },
            )

            return None

    # =========================================================
    # ファイル読み込み
    # =========================================================

    def read_text(
        self,
        file_path: str | Path,
        *,
        encoding: str = "utf-8",
    ) -> Optional[str]:
        """
        ファイルをテキストとして読み込む。

        Pythonのcoding宣言など特殊な文字コード処理が必要な場合は、
        PythonParser側でoverrideしてよい。
        """

        path = Path(file_path)

        try:

            return path.read_text(
                encoding=encoding
            )

        except UnicodeDecodeError as exc:

            # UTF-8 BOMをフォールバックとして試す
            try:

                return path.read_text(
                    encoding="utf-8-sig"
                )

            except (UnicodeDecodeError, OSError) as second_exc:

                self.add_error(
                    f"文字コードを解釈できません: {path}",
                    error_type="decode_error",
                    details={
                        "encoding": encoding,
                        "exception": str(exc),
                        "fallback_exception": str(
                            second_exc
                        ),
                    },
                )

                return None

        except OSError as exc:

            self.add_error(
                f"ファイルを読み込めません: {path}",
                error_type="read_error",
                details={
                    "exception": str(exc),
                },
            )

            return None

    # =========================================================
    # 旧コード文字列入力用チェック
    # =========================================================

    def validate_code(
        self,
        code: str,
    ) -> bool:
        """
        文字列として渡されたコードの最低限チェック。

        通常のparse()は絶対パス入力だが、
        将来的な parse_code() やテスト用途でも利用できるよう残している。
        """

        if code is None:

            self.add_error(
                "コードが指定されていません。",
                error_type="invalid_input",
            )

            return False

        if not isinstance(
            code,
            str,
        ):

            self.add_error(
                "コードは文字列で指定する必要があります。",
                error_type="invalid_input",
            )

            return False

        if not code.strip():

            self.add_error(
                "コードが空です。",
                error_type="empty_code",
            )

            return False

        return True

    # =========================================================
    # 共通結果フォーマット
    # =========================================================

    def create_result(
        self,
        *,
        classes: Optional[
            List[Dict[str, Any]]
        ] = None,

        functions: Optional[
            List[Dict[str, Any]]
        ] = None,

        methods: Optional[
            List[Dict[str, Any]]
        ] = None,

        variables: Optional[
            List[Dict[str, Any]]
        ] = None,

        imports: Optional[
            List[Dict[str, Any]]
        ] = None,

        exports: Optional[
            List[Dict[str, Any]]
        ] = None,

        interfaces: Optional[
            List[Dict[str, Any]]
        ] = None,

        dependencies: Optional[
            List[Dict[str, Any]]
        ] = None,

        calls: Optional[
            List[Dict[str, Any]]
        ] = None,

        metadata: Optional[
            Dict[str, Any]
        ] = None,

    ) -> Dict[str, Any]:
        """
        ParserHandler / Analyzerへ返す共通形式を生成する。

        言語ごとに結果構造がバラバラになることを防ぐ。
        """

        classes = classes or []
        functions = functions or []
        methods = methods or []
        variables = variables or []
        imports = imports or []
        exports = exports or []
        interfaces = interfaces or []
        dependencies = dependencies or []
        calls = calls or []
        metadata = metadata or {}

        return {

            "ok": len(
                self.errors
            ) == 0,

            "language": self.language,

            "parser": {
                "name": self.__class__.__name__,
                "version": self.parser_version,
            },

            "classes": classes,

            "functions": functions,

            "methods": methods,

            "variables": variables,

            "imports": imports,

            "exports": exports,

            "interfaces": interfaces,

            "dependencies": dependencies,

            "calls": calls,

            "metadata": metadata,

            "stats": {

                "classes": len(
                    classes
                ),

                "functions": len(
                    functions
                ),

                "methods": len(
                    methods
                ),

                "variables": len(
                    variables
                ),

                "imports": len(
                    imports
                ),

                "exports": len(
                    exports
                ),

                "interfaces": len(
                    interfaces
                ),

                "dependencies": len(
                    dependencies
                ),

                "calls": len(
                    calls
                ),

                "errors": len(
                    self.errors
                ),
            },

            "errors": list(
                self.errors
            ),
        }

    # =========================================================
    # Metadata
    # =========================================================

    def create_file_metadata(
        self,
        path: Path,
        code: str,
        *,
        extra: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        ファイル共通Metadataを生成する。
        """

        metadata: Dict[str, Any] = {

            "file_path": str(
                path.resolve()
            ),

            "file_name": path.name,

            "extension": path.suffix.lower(),

            "line_count": self.count_lines(
                code
            ),

            "size_bytes": len(
                code.encode(
                    "utf-8"
                )
            ),
        }

        if extra:

            metadata.update(
                extra
            )

        return metadata

    # =========================================================
    # エラー管理
    # =========================================================

    def add_error(
        self,
        message: str,
        *,
        error_type: str = "parse_error",
        line: Optional[int] = None,
        column: Optional[int] = None,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
        severity: str = "error",
        details: Optional[
            Dict[str, Any]
        ] = None,
    ) -> None:
        """
        Parser内部で発生したエラーを統一形式で保存する。
        """

        error: Dict[str, Any] = {

            "type": error_type,

            "message": message,

            "severity": severity,
        }

        if line is not None:
            error["line"] = line

        if column is not None:
            error["column"] = column

        if end_line is not None:
            error["end_line"] = end_line

        if end_column is not None:
            error["end_column"] = end_column

        if details:
            error["details"] = details

        self.errors.append(
            error
        )

    def add_warning(
        self,
        message: str,
        *,
        warning_type: str = "parser_warning",
        line: Optional[int] = None,
        column: Optional[int] = None,
        details: Optional[
            Dict[str, Any]
        ] = None,
    ) -> None:
        """
        warningを追加する簡易Utility。
        """

        self.add_error(
            message,
            error_type=warning_type,
            line=line,
            column=column,
            severity="warning",
            details=details,
        )

    def clear_errors(
        self,
    ) -> None:
        """
        前回解析時のエラーを削除する。

        Parserインスタンスを使い回す場合、
        parse()開始時に呼び出す。
        """

        self.errors.clear()

    def has_errors(
        self,
    ) -> bool:
        """
        severity=error が存在するか確認する。
        """

        return any(

            error.get(
                "severity"
            ) == "error"

            for error in self.errors
        )

    # =========================================================
    # コードUtility
    # =========================================================

    def normalize_code(
        self,
        code: str,
    ) -> str:
        """
        最低限のコード正規化。

        意味を変えるような処理は行わない。

        注意:
            AST解析用の元コードでは、
            最後のstrip()によって位置情報がずれる可能性がある。

            そのためParser本体では、
            必要がない限り元コードをそのまま使う方が安全。
        """

        if not isinstance(
            code,
            str,
        ):
            return ""

        return (
            code
            .replace(
                "\r\n",
                "\n"
            )
            .replace(
                "\r",
                "\n"
            )
        )

    def get_line(
        self,
        code: str,
        line_number: int,
    ) -> Optional[str]:
        """
        指定行を取得する。

        line_numberは1始まり。
        """

        if line_number < 1:
            return None

        lines = code.splitlines()

        index = (
            line_number - 1
        )

        if index >= len(
            lines
        ):
            return None

        return lines[index]

    def count_lines(
        self,
        code: str,
    ) -> int:
        """
        コード行数を返す。
        """

        if not code:
            return 0

        return len(
            code.splitlines()
        )

    # =========================================================
    # Source Location
    # =========================================================

    def create_location(
        self,
        *,
        start_line: Optional[int] = None,
        start_column: Optional[int] = None,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
    ) -> Dict[str, Optional[int]]:
        """
        コード上の位置を共通形式で生成する。

        行番号:
            1始まり推奨

        column:
            Parserごとに0始まり/1始まりが違う可能性があるため、
            子Parserで1始まりへ統一して渡すことを推奨。
        """

        return {

            "start_line": start_line,

            "start_column": start_column,

            "end_line": end_line,

            "end_column": end_column,
        }

    # =========================================================
    # Symbol Utility
    # =========================================================

    def create_variable(
        self,
        *,
        name: str,

        var_type: Optional[
            str
        ] = None,

        value: Optional[
            Any
        ] = None,

        scope: Optional[
            str
        ] = None,

        access: Optional[
            str
        ] = None,

        line: Optional[
            int
        ] = None,

        location: Optional[
            Dict[str, Any]
        ] = None,

        modifiers: Optional[
            List[str]
        ] = None,

        annotation: Optional[
            str
        ] = None,

    ) -> Dict[str, Any]:
        """
        変数情報を共通形式で生成する。
        """

        return {

            "name": name,

            "type": var_type,

            "value": value,

            "scope": scope,

            "access": access,

            "line": line,

            "location": location,

            "modifiers": modifiers or [],

            "annotation": annotation,
        }

    def create_parameter(
        self,
        *,
        name: str,

        param_type: Optional[
            str
        ] = None,

        default: Optional[
            Any
        ] = None,

        kind: Optional[
            str
        ] = None,

        annotation: Optional[
            str
        ] = None,

    ) -> Dict[str, Any]:
        """
        引数情報を共通形式で生成する。

        kind例:
            positional
            positional_only
            keyword_only
            vararg
            kwarg
            rest
        """

        return {

            "name": name,

            "type": param_type,

            "default": default,

            "kind": kind,

            "annotation": annotation,
        }

    def create_method(
        self,
        *,
        name: str,

        return_type: Optional[
            str
        ] = None,

        parameters: Optional[
            List[Dict[str, Any]]
        ] = None,

        access: Optional[
            str
        ] = None,

        line: Optional[
            int
        ] = None,

        location: Optional[
            Dict[str, Any]
        ] = None,

        modifiers: Optional[
            List[str]
        ] = None,

        decorators: Optional[
            List[str]
        ] = None,

        reads: Optional[
            List[str]
        ] = None,

        writes: Optional[
            List[str]
        ] = None,

        calls: Optional[
            List[str]
        ] = None,

        awaits: Optional[
            List[str]
        ] = None,

        raises: Optional[
            List[str]
        ] = None,

        docstring: Optional[
            str
        ] = None,

        is_async: bool = False,

        is_static: bool = False,

        is_abstract: bool = False,

        raw: Optional[
            str
        ] = None,

    ) -> Dict[str, Any]:
        """
        メソッド情報を共通形式で生成する。
        """

        return {

            "name": name,

            "return_type": return_type,

            "parameters": parameters or [],

            "access": access,

            "line": line,

            "location": location,

            "modifiers": modifiers or [],

            "decorators": decorators or [],

            "reads": reads or [],

            "writes": writes or [],

            "calls": calls or [],

            "awaits": awaits or [],

            "raises": raises or [],

            "docstring": docstring,

            "is_async": is_async,

            "is_static": is_static,

            "is_abstract": is_abstract,

            "raw": raw,
        }

    def create_function(
        self,
        *,
        name: str,

        return_type: Optional[
            str
        ] = None,

        parameters: Optional[
            List[Dict[str, Any]]
        ] = None,

        line: Optional[
            int
        ] = None,

        location: Optional[
            Dict[str, Any]
        ] = None,

        modifiers: Optional[
            List[str]
        ] = None,

        decorators: Optional[
            List[str]
        ] = None,

        calls: Optional[
            List[str]
        ] = None,

        awaits: Optional[
            List[str]
        ] = None,

        raises: Optional[
            List[str]
        ] = None,

        returns: Optional[
            List[Any]
        ] = None,

        docstring: Optional[
            str
        ] = None,

        is_async: bool = False,

        is_generator: bool = False,

        is_exported: bool = False,

        raw: Optional[
            str
        ] = None,

    ) -> Dict[str, Any]:
        """
        モジュール / ファイル直下の関数情報を生成する。

        Python:
            def foo()

        JavaScript:
            function foo()
            const foo = () => {}
        """

        return {

            "name": name,

            "return_type": return_type,

            "parameters": parameters or [],

            "line": line,

            "location": location,

            "modifiers": modifiers or [],

            "decorators": decorators or [],

            "calls": calls or [],

            "awaits": awaits or [],

            "raises": raises or [],

            "returns": returns or [],

            "docstring": docstring,

            "is_async": is_async,

            "is_generator": is_generator,

            "is_exported": is_exported,

            "raw": raw,
        }

    def create_class(
        self,
        *,
        name: str,

        access: Optional[
            str
        ] = None,

        line: Optional[
            int
        ] = None,

        location: Optional[
            Dict[str, Any]
        ] = None,

        extends: Optional[
            str
        ] = None,

        bases: Optional[
            List[str]
        ] = None,

        implements: Optional[
            List[str]
        ] = None,

        modifiers: Optional[
            List[str]
        ] = None,

        decorators: Optional[
            List[str]
        ] = None,

        methods: Optional[
            List[Dict[str, Any]]
        ] = None,

        variables: Optional[
            List[Dict[str, Any]]
        ] = None,

        docstring: Optional[
            str
        ] = None,

        is_exported: bool = False,

    ) -> Dict[str, Any]:
        """
        クラス情報を共通形式で生成する。

        extends:
            Java / JavaScript向け単一継承

        bases:
            Pythonの複数継承などに使用

        implements:
            Java / TypeScript等
        """

        return {

            "name": name,

            "access": access,

            "line": line,

            "location": location,

            "extends": extends,

            "bases": bases or [],

            "implements": implements or [],

            "modifiers": modifiers or [],

            "decorators": decorators or [],

            "methods": methods or [],

            "variables": variables or [],

            "docstring": docstring,

            "is_exported": is_exported,
        }

    def create_import(
        self,
        *,
        module: Optional[
            str
        ] = None,

        names: Optional[
            List[str]
        ] = None,

        aliases: Optional[
            Dict[str, str]
        ] = None,

        source: Optional[
            str
        ] = None,

        level: int = 0,

        line: Optional[
            int
        ] = None,

        location: Optional[
            Dict[str, Any]
        ] = None,

        raw: Optional[
            str
        ] = None,

    ) -> Dict[str, Any]:
        """
        import情報を共通形式で生成する。

        Python:
            from pathlib import Path

        JavaScript:
            import React from "react"

        module:
            Python向け

        source:
            JavaScript等のimport元向け
        """

        return {

            "module": module,

            "source": source,

            "names": names or [],

            "aliases": aliases or {},

            "level": level,

            "line": line,

            "location": location,

            "raw": raw,
        }

    def create_export(
        self,
        *,
        names: Optional[
            List[str]
        ] = None,

        default: bool = False,

        source: Optional[
            str
        ] = None,

        line: Optional[
            int
        ] = None,

        location: Optional[
            Dict[str, Any]
        ] = None,

        raw: Optional[
            str
        ] = None,

    ) -> Dict[str, Any]:
        """
        export情報を共通形式で生成する。
        """

        return {

            "names": names or [],

            "default": default,

            "source": source,

            "line": line,

            "location": location,

            "raw": raw,
        }

    def create_call(
        self,
        *,
        name: str,

        line: Optional[
            int
        ] = None,

        location: Optional[
            Dict[str, Any]
        ] = None,

        arguments: Optional[
            List[Any]
        ] = None,

        scope: Optional[
            str
        ] = None,

    ) -> Dict[str, Any]:
        """
        関数・メソッド呼び出し情報を生成する。
        """

        return {

            "name": name,

            "line": line,

            "location": location,

            "arguments": arguments or [],

            "scope": scope,
        }

    def create_dependency(
        self,
        *,
        name: str,

        dependency_type: str,

        source: Optional[
            str
        ] = None,

        line: Optional[
            int
        ] = None,

        metadata: Optional[
            Dict[str, Any]
        ] = None,

    ) -> Dict[str, Any]:
        """
        AnalyzerやKnowledgeSearchで扱える
        共通Dependency情報を生成する。

        dependency_type例:
            import
            inheritance
            function_call
            module
            package
        """

        return {

            "name": name,

            "type": dependency_type,

            "source": source,

            "line": line,

            "metadata": metadata or {},
        }

    # =========================================================
    # Parser情報
    # =========================================================

    def get_language(
        self,
    ) -> str:

        return self.language

    def get_parser_info(
        self,
    ) -> Dict[str, Any]:
        """
        デバッグやParserHandler側の確認用。
        """

        return {

            "language": self.language,

            "parser": self.__class__.__name__,

            "version": self.parser_version,

            "supported_extensions": sorted(
                self.supported_extensions
            ),
        }