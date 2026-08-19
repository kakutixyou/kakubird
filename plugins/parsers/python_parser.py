#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
python_parser.py
================

PythonソースコードをAST解析し、
BaseParserの共通形式へ変換するParser。

対応:
    .py
    .pyw

取得対象:
    - import / from import
    - module-level function
    - async function
    - nested function情報
    - class
    - method
    - class variable
    - module variable
    - function parameter
    - type annotation
    - decorator
    - return
    - await
    - raise
    - function / method call
    - inheritance
    - __all__
    - module docstring
    - syntax error
    - source location
    - dependency

設計:
    Parser:
        「コードに何が書かれているか」を抽出する。

    Analyzer:
        「そのコードが何をしているか」
        「設計上どういう意味があるか」
        「問題があるか」
        などを判断する。

入力:
    絶対パスのみ。

依存:
    Python標準ライブラリのみ。
"""

from __future__ import annotations

import ast
import logging
import tokenize
from pathlib import Path
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------
# BaseParser import
#
# 配置に合わせて必要なら変更してください。
#
# 例:
#   from .base_parser import BaseParser
#   from engine.parsers.base_parser import BaseParser
# ------------------------------------------------------------

from .base_parser import BaseParser


logger = logging.getLogger(__name__)


class PythonParser(BaseParser):
    """
    Python AST Parser。
    """

    language = "python"

    parser_version = "1.0"

    supported_extensions = {
        ".py",
        ".pyw",
    }

    # ========================================================
    # Public API
    # ========================================================

    def parse(
        self,
        file_path: str | Path,
    ) -> Dict[str, Any]:
        """
        Pythonファイルを解析する。

        Parameters
        ----------
        file_path:
            解析対象Pythonファイルの絶対パス。

        Returns
        -------
        BaseParser.create_result() 形式のdict。
        """

        # ----------------------------------------------------
        # 前回の解析エラーを消す
        # ----------------------------------------------------

        self.clear_errors()

        # ----------------------------------------------------
        # Path Validation
        # ----------------------------------------------------

        path = self.validate_file_path(
            file_path
        )

        if path is None:

            return self.create_result()

        # ----------------------------------------------------
        # Source Read
        #
        # Pythonは # -*- coding: ... -*- を持てるため
        # tokenize.open() を利用する。
        # ----------------------------------------------------

        source = self._read_python_source(
            path
        )

        if source is None:

            return self.create_result(
                metadata={
                    "file_path": str(path),
                    "file_name": path.name,
                    "extension": path.suffix.lower(),
                }
            )

        # ----------------------------------------------------
        # Metadata
        # ----------------------------------------------------

        metadata = self.create_file_metadata(
            path,
            source,
        )

        # ----------------------------------------------------
        # AST Parse
        # ----------------------------------------------------

        try:

            tree = ast.parse(
                source,
                filename=str(path),
                type_comments=True,
            )

        except SyntaxError as exc:

            self.add_error(
                exc.msg or "Python syntax error",
                error_type="syntax_error",
                line=exc.lineno,
                column=exc.offset,
                end_line=getattr(
                    exc,
                    "end_lineno",
                    None,
                ),
                end_column=getattr(
                    exc,
                    "end_offset",
                    None,
                ),
                details={
                    "text": (
                        exc.text.rstrip()
                        if exc.text
                        else None
                    )
                },
            )

            return self.create_result(
                metadata=metadata,
            )

        except Exception as exc:

            logger.exception(
                "Python AST parse error: %s",
                path,
            )

            self.add_error(
                str(exc),
                error_type="ast_parse_error",
                details={
                    "exception": (
                        exc.__class__.__name__
                    )
                },
            )

            return self.create_result(
                metadata=metadata,
            )

        # ----------------------------------------------------
        # Module information
        # ----------------------------------------------------

        module_docstring = ast.get_docstring(
            tree,
            clean=True,
        )

        metadata["module_docstring"] = (
            module_docstring
        )

        # ----------------------------------------------------
        # Collections
        # ----------------------------------------------------

        imports: List[
            Dict[str, Any]
        ] = []

        functions: List[
            Dict[str, Any]
        ] = []

        classes: List[
            Dict[str, Any]
        ] = []

        methods: List[
            Dict[str, Any]
        ] = []

        variables: List[
            Dict[str, Any]
        ] = []

        exports: List[
            Dict[str, Any]
        ] = []

        dependencies: List[
            Dict[str, Any]
        ] = []

        calls: List[
            Dict[str, Any]
        ] = []

        # ----------------------------------------------------
        # Module-level AST
        # ----------------------------------------------------

        for node in tree.body:

            # =================================================
            # import xxx
            # =================================================

            if isinstance(
                node,
                ast.Import,
            ):

                parsed_imports = (
                    self._parse_import(node)
                )

                imports.extend(
                    parsed_imports
                )

                for item in parsed_imports:

                    for name in item.get(
                        "names",
                        [],
                    ):

                        dependencies.append(
                            self.create_dependency(
                                name=name,
                                dependency_type="import",
                                source=name,
                                line=self._node_line(
                                    node
                                ),
                            )
                        )

            # =================================================
            # from xxx import yyy
            # =================================================

            elif isinstance(
                node,
                ast.ImportFrom,
            ):

                import_item = (
                    self._parse_import_from(
                        node
                    )
                )

                imports.append(
                    import_item
                )

                module_name = (
                    import_item.get(
                        "module"
                    )
                    or ""
                )

                if module_name:

                    dependencies.append(
                        self.create_dependency(
                            name=module_name,
                            dependency_type="import",
                            source=module_name,
                            line=self._node_line(
                                node
                            ),
                        )
                    )

            # =================================================
            # function
            # =================================================

            elif isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                function = (
                    self._parse_function(
                        node,
                        source,
                    )
                )

                functions.append(
                    function
                )

            # =================================================
            # class
            # =================================================

            elif isinstance(
                node,
                ast.ClassDef,
            ):

                class_info, class_methods = (
                    self._parse_class(
                        node,
                        source,
                    )
                )

                classes.append(
                    class_info
                )

                # methodsをトップレベルにも置く。
                #
                # class内にもmethodsは保存されるが、
                # SearchEngineが全methodを検索しやすいよう
                # 共通resultsにもflattenしている。
                methods.extend(
                    class_methods
                )

                # inheritance dependency
                for base in class_info.get(
                    "bases",
                    [],
                ):

                    dependencies.append(
                        self.create_dependency(
                            name=base,
                            dependency_type="inheritance",
                            source=node.name,
                            line=self._node_line(
                                node
                            ),
                        )
                    )

            # =================================================
            # module variables
            # =================================================

            elif isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                ),
            ):

                parsed_variables = (
                    self._parse_assignment(
                        node,
                        scope="module",
                    )
                )

                variables.extend(
                    parsed_variables
                )

                # ---------------------------------------------
                # Pythonの疑似export:
                #
                # __all__ = [
                #     "Foo",
                #     "bar",
                # ]
                # ---------------------------------------------

                exported = (
                    self._parse_dunder_all(
                        node
                    )
                )

                if exported:

                    exports.append(
                        self.create_export(
                            names=exported,
                            line=self._node_line(
                                node
                            ),
                            location=self._location(
                                node
                            ),
                            raw=self._source_segment(
                                source,
                                node,
                            ),
                        )
                    )

        # ----------------------------------------------------
        # Module-level Call
        # ----------------------------------------------------

        calls.extend(
            self._collect_module_calls(
                tree
            )
        )

        # ----------------------------------------------------
        # dependency: calls
        #
        # 呼び出しをdependencyとしても持たせる。
        # Analyzer側で必要なければ無視できる。
        # ----------------------------------------------------

        for call in calls:

            name = call.get(
                "name"
            )

            if name:

                dependencies.append(
                    self.create_dependency(
                        name=name,
                        dependency_type="function_call",
                        source="module",
                        line=call.get(
                            "line"
                        ),
                    )
                )

        # ----------------------------------------------------
        # Metadata extras
        # ----------------------------------------------------

        metadata.update(
            {
                "python_ast": True,
                "has_module_docstring": bool(
                    module_docstring
                ),
            }
        )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        result = self.create_result(
            classes=classes,
            functions=functions,
            methods=methods,
            variables=variables,
            imports=imports,
            exports=exports,
            dependencies=self._deduplicate_dicts(
                dependencies
            ),
            calls=calls,
            metadata=metadata,
        )

        logger.info(
            (
                "Python parse complete: %s "
                "(classes=%d functions=%d "
                "methods=%d imports=%d)"
            ),
            path,
            len(classes),
            len(functions),
            len(methods),
            len(imports),
        )

        return result

    # ========================================================
    # File Reader
    # ========================================================

    def _read_python_source(
        self,
        path: Path,
    ) -> Optional[str]:
        """
        Pythonのencoding declarationに対応して読み込む。

        tokenize.open() は、

            # -*- coding: shift_jis -*-

        のような宣言を認識できる。
        """

        try:

            with tokenize.open(
                str(path)
            ) as file:

                return file.read()

        except SyntaxError as exc:

            self.add_error(
                str(exc),
                error_type="encoding_error",
                details={
                    "file_path": str(
                        path
                    )
                },
            )

        except UnicodeDecodeError as exc:

            self.add_error(
                str(exc),
                error_type="decode_error",
                details={
                    "file_path": str(
                        path
                    )
                },
            )

        except OSError as exc:

            self.add_error(
                str(exc),
                error_type="read_error",
                details={
                    "file_path": str(
                        path
                    )
                },
            )

        return None

    # ========================================================
    # Import
    # ========================================================

    def _parse_import(
        self,
        node: ast.Import,
    ) -> List[Dict[str, Any]]:
        """
        import os
        import json as js

        を解析する。
        """

        result: List[
            Dict[str, Any]
        ] = []

        for alias in node.names:

            aliases: Dict[
                str,
                str
            ] = {}

            if alias.asname:

                aliases[
                    alias.asname
                ] = alias.name

            result.append(
                self.create_import(
                    module=alias.name,
                    names=[
                        alias.name
                    ],
                    aliases=aliases,
                    source=alias.name,
                    line=self._node_line(
                        node
                    ),
                    location=self._location(
                        node
                    ),
                )
            )

        return result

    def _parse_import_from(
        self,
        node: ast.ImportFrom,
    ) -> Dict[str, Any]:
        """
        from pathlib import Path
        from ..engine import Router
        """

        names: List[str] = []

        aliases: Dict[
            str,
            str
        ] = {}

        for alias in node.names:

            names.append(
                alias.name
            )

            if alias.asname:

                aliases[
                    alias.asname
                ] = alias.name

        module = (
            node.module or ""
        )

        # relative import
        if node.level:

            module = (
                "." * node.level
                + module
            )

        return self.create_import(
            module=module,
            names=names,
            aliases=aliases,
            source=module,
            level=node.level,
            line=self._node_line(
                node
            ),
            location=self._location(
                node
            ),
        )

    # ========================================================
    # Function
    # ========================================================

    def _parse_function(
        self,
        node: ast.FunctionDef
        | ast.AsyncFunctionDef,
        source: str,
    ) -> Dict[str, Any]:
        """
        モジュールレベル関数を解析する。
        """

        parameters = (
            self._parse_arguments(
                node.args
            )
        )

        decorators = [
            self._unparse(
                decorator
            )
            for decorator
            in node.decorator_list
        ]

        decorators = [
            item
            for item in decorators
            if item
        ]

        calls = (
            self._collect_calls_inside(
                node
            )
        )

        awaits = (
            self._collect_awaits(
                node
            )
        )

        raises = (
            self._collect_raises(
                node
            )
        )

        returns = (
            self._collect_returns(
                node
            )
        )

        generator = (
            self._contains_yield(
                node
            )
        )

        return self.create_function(
            name=node.name,

            return_type=self._unparse(
                node.returns
            ),

            parameters=parameters,

            line=self._node_line(
                node
            ),

            location=self._location(
                node
            ),

            decorators=decorators,

            calls=calls,

            awaits=awaits,

            raises=raises,

            returns=returns,

            docstring=ast.get_docstring(
                node,
                clean=True,
            ),

            is_async=isinstance(
                node,
                ast.AsyncFunctionDef,
            ),

            is_generator=generator,

            raw=self._source_segment(
                source,
                node,
            ),
        )

    # ========================================================
    # Class
    # ========================================================

    def _parse_class(
        self,
        node: ast.ClassDef,
        source: str,
    ) -> tuple[
        Dict[str, Any],
        List[Dict[str, Any]],
    ]:
        """
        classを解析する。
        """

        methods: List[
            Dict[str, Any]
        ] = []

        variables: List[
            Dict[str, Any]
        ] = []

        for child in node.body:

            # ------------------------------------------------
            # method
            # ------------------------------------------------

            if isinstance(
                child,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                method = (
                    self._parse_method(
                        child,
                        source,
                        class_name=node.name,
                    )
                )

                methods.append(
                    method
                )

            # ------------------------------------------------
            # class variable
            # ------------------------------------------------

            elif isinstance(
                child,
                (
                    ast.Assign,
                    ast.AnnAssign,
                ),
            ):

                variables.extend(
                    self._parse_assignment(
                        child,
                        scope=(
                            f"class:{node.name}"
                        ),
                    )
                )

        bases = [
            value
            for base in node.bases
            if (
                value := self._unparse(
                    base
                )
            )
        ]

        decorators = [
            value
            for decorator
            in node.decorator_list
            if (
                value := self._unparse(
                    decorator
                )
            )
        ]

        extends = (
            bases[0]
            if bases
            else None
        )

        class_info = (
            self.create_class(
                name=node.name,

                line=self._node_line(
                    node
                ),

                location=self._location(
                    node
                ),

                extends=extends,

                bases=bases,

                decorators=decorators,

                methods=methods,

                variables=variables,

                docstring=ast.get_docstring(
                    node,
                    clean=True,
                ),
            )
        )

        return (
            class_info,
            methods,
        )

    # ========================================================
    # Method
    # ========================================================

    def _parse_method(
        self,
        node: ast.FunctionDef
        | ast.AsyncFunctionDef,
        source: str,
        *,
        class_name: str,
    ) -> Dict[str, Any]:
        """
        class methodを解析する。
        """

        decorators = [
            value
            for decorator
            in node.decorator_list
            if (
                value := self._unparse(
                    decorator
                )
            )
        ]

        is_static = (
            "staticmethod"
            in decorators
        )

        is_abstract = any(
            (
                decorator
                == "abstractmethod"
                or decorator.endswith(
                    ".abstractmethod"
                )
            )
            for decorator
            in decorators
        )

        modifiers: List[str] = []

        if isinstance(
            node,
            ast.AsyncFunctionDef,
        ):
            modifiers.append(
                "async"
            )

        if is_static:
            modifiers.append(
                "static"
            )

        if "classmethod" in decorators:
            modifiers.append(
                "classmethod"
            )

        if is_abstract:
            modifiers.append(
                "abstract"
            )

        return self.create_method(
            name=node.name,

            return_type=self._unparse(
                node.returns
            ),

            parameters=self._parse_arguments(
                node.args
            ),

            access=self._infer_access(
                node.name
            ),

            line=self._node_line(
                node
            ),

            location=self._location(
                node
            ),

            modifiers=modifiers,

            decorators=decorators,

            calls=self._collect_calls_inside(
                node
            ),

            awaits=self._collect_awaits(
                node
            ),

            raises=self._collect_raises(
                node
            ),

            docstring=ast.get_docstring(
                node,
                clean=True,
            ),

            is_async=isinstance(
                node,
                ast.AsyncFunctionDef,
            ),

            is_static=is_static,

            is_abstract=is_abstract,

            raw=self._source_segment(
                source,
                node,
            ),
        )

    # ========================================================
    # Arguments
    # ========================================================

    def _parse_arguments(
        self,
        arguments: ast.arguments,
    ) -> List[Dict[str, Any]]:
        """
        Python関数引数を共通形式へ変換する。

        対応:
            def f(a, b=1, /, c=2, *, d, **kwargs)
        """

        result: List[
            Dict[str, Any]
        ] = []

        positional = (
            list(
                arguments.posonlyargs
            )
            + list(
                arguments.args
            )
        )

        defaults = list(
            arguments.defaults
        )

        default_start = (
            len(positional)
            - len(defaults)
        )

        posonly_count = len(
            arguments.posonlyargs
        )

        # ----------------------------------------------------
        # positional
        # ----------------------------------------------------

        for index, arg in enumerate(
            positional
        ):

            default_value = None

            if index >= default_start:

                default_node = defaults[
                    index
                    - default_start
                ]

                default_value = (
                    self._unparse(
                        default_node
                    )
                )

            if index < posonly_count:

                kind = (
                    "positional_only"
                )

            else:

                kind = "positional"

            annotation = (
                self._unparse(
                    arg.annotation
                )
            )

            result.append(
                self.create_parameter(
                    name=arg.arg,
                    param_type=annotation,
                    annotation=annotation,
                    default=default_value,
                    kind=kind,
                )
            )

        # ----------------------------------------------------
        # *args
        # ----------------------------------------------------

        if arguments.vararg:

            annotation = (
                self._unparse(
                    arguments.vararg.annotation
                )
            )

            result.append(
                self.create_parameter(
                    name=arguments.vararg.arg,
                    param_type=annotation,
                    annotation=annotation,
                    kind="vararg",
                )
            )

        # ----------------------------------------------------
        # keyword-only
        # ----------------------------------------------------

        for (
            arg,
            default_node,
        ) in zip(
            arguments.kwonlyargs,
            arguments.kw_defaults,
        ):

            annotation = (
                self._unparse(
                    arg.annotation
                )
            )

            default_value = (
                self._unparse(
                    default_node
                )
                if default_node
                else None
            )

            result.append(
                self.create_parameter(
                    name=arg.arg,
                    param_type=annotation,
                    annotation=annotation,
                    default=default_value,
                    kind="keyword_only",
                )
            )

        # ----------------------------------------------------
        # **kwargs
        # ----------------------------------------------------

        if arguments.kwarg:

            annotation = (
                self._unparse(
                    arguments.kwarg.annotation
                )
            )

            result.append(
                self.create_parameter(
                    name=arguments.kwarg.arg,
                    param_type=annotation,
                    annotation=annotation,
                    kind="kwarg",
                )
            )

        return result

    # ========================================================
    # Variable
    # ========================================================

    def _parse_assignment(
        self,
        node: ast.Assign
        | ast.AnnAssign,
        *,
        scope: str,
    ) -> List[Dict[str, Any]]:
        """
        Python代入式を解析する。
        """

        result: List[
            Dict[str, Any]
        ] = []

        # ----------------------------------------------------
        # a = 10
        # a, b = 1, 2
        # ----------------------------------------------------

        if isinstance(
            node,
            ast.Assign,
        ):

            value = self._unparse(
                node.value
            )

            for target in node.targets:

                names = (
                    self._extract_target_names(
                        target
                    )
                )

                for name in names:

                    result.append(
                        self.create_variable(
                            name=name,

                            value=value,

                            scope=scope,

                            access=self._infer_access(
                                name
                            ),

                            line=self._node_line(
                                node
                            ),

                            location=self._location(
                                node
                            ),
                        )
                    )

        # ----------------------------------------------------
        # count: int = 0
        # ----------------------------------------------------

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            annotation = (
                self._unparse(
                    node.annotation
                )
            )

            value = (
                self._unparse(
                    node.value
                )
            )

            names = (
                self._extract_target_names(
                    node.target
                )
            )

            for name in names:

                result.append(
                    self.create_variable(
                        name=name,

                        var_type=annotation,

                        annotation=annotation,

                        value=value,

                        scope=scope,

                        access=self._infer_access(
                            name
                        ),

                        line=self._node_line(
                            node
                        ),

                        location=self._location(
                            node
                        ),
                    )
                )

        return result

    def _extract_target_names(
        self,
        node: ast.AST,
    ) -> List[str]:
        """
        代入targetから名前を取得する。

        対応例:
            a = 1
            self.value = 1
            a, b = ...
            [a, b] = ...
        """

        if isinstance(
            node,
            ast.Name,
        ):

            return [
                node.id
            ]

        if isinstance(
            node,
            ast.Attribute,
        ):

            name = (
                self._callable_name(
                    node
                )
            )

            return [
                name
            ] if name else []

        if isinstance(
            node,
            (
                ast.Tuple,
                ast.List,
            ),
        ):

            result: List[
                str
            ] = []

            for element in node.elts:

                result.extend(
                    self._extract_target_names(
                        element
                    )
                )

            return result

        if isinstance(
            node,
            ast.Starred,
        ):

            return self._extract_target_names(
                node.value
            )

        return []

    # ========================================================
    # Calls
    # ========================================================

    def _collect_calls_inside(
        self,
        root: ast.AST,
    ) -> List[str]:
        """
        function/method内部のcallを取得する。

        ネストされた別function/class内部には入り込まない。
        """

        result: List[str] = []

        parser = self

        class CallVisitor(
            ast.NodeVisitor
        ):

            def visit_Call(
                visitor_self,
                node: ast.Call,
            ) -> None:

                name = (
                    parser._callable_name(
                        node.func
                    )
                )

                if name:

                    result.append(
                        name
                    )

                visitor_self.generic_visit(
                    node
                )

            def visit_FunctionDef(
                visitor_self,
                node: ast.FunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

            def visit_AsyncFunctionDef(
                visitor_self,
                node: ast.AsyncFunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

            def visit_Lambda(
                visitor_self,
                node: ast.Lambda,
            ) -> None:

                # lambdaはroot内コードなので解析する。
                visitor_self.generic_visit(
                    node
                )

            def visit_ClassDef(
                visitor_self,
                node: ast.ClassDef,
            ) -> None:

                # nested class内部には入らない
                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

        visitor = CallVisitor()

        visitor.visit(
            root
        )

        return self._deduplicate_strings(
            result
        )

    def _collect_module_calls(
        self,
        tree: ast.Module,
    ) -> List[Dict[str, Any]]:
        """
        モジュール直下で実行されるcallを取得する。

        function / class内部は除外する。
        """

        result: List[
            Dict[str, Any]
        ] = []

        parser = self

        class ModuleCallVisitor(
            ast.NodeVisitor
        ):

            def visit_FunctionDef(
                visitor_self,
                node: ast.FunctionDef,
            ) -> None:

                return

            def visit_AsyncFunctionDef(
                visitor_self,
                node: ast.AsyncFunctionDef,
            ) -> None:

                return

            def visit_ClassDef(
                visitor_self,
                node: ast.ClassDef,
            ) -> None:

                return

            def visit_Call(
                visitor_self,
                node: ast.Call,
            ) -> None:

                name = (
                    parser._callable_name(
                        node.func
                    )
                )

                if name:

                    arguments = [
                        value
                        for arg in node.args
                        if (
                            value := parser._unparse(
                                arg
                            )
                        )
                    ]

                    result.append(
                        parser.create_call(
                            name=name,

                            line=parser._node_line(
                                node
                            ),

                            location=parser._location(
                                node
                            ),

                            arguments=arguments,

                            scope="module",
                        )
                    )

                visitor_self.generic_visit(
                    node
                )

        visitor = (
            ModuleCallVisitor()
        )

        for node in tree.body:

            visitor.visit(
                node
            )

        return result

    # ========================================================
    # Await
    # ========================================================

    def _collect_awaits(
        self,
        root: ast.AST,
    ) -> List[str]:
        """
        await expressionを取得する。
        """

        result: List[str] = []

        parser = self

        class AwaitVisitor(
            ast.NodeVisitor
        ):

            def visit_Await(
                visitor_self,
                node: ast.Await,
            ) -> None:

                value = parser._unparse(
                    node.value
                )

                if value:

                    result.append(
                        value
                    )

                visitor_self.generic_visit(
                    node
                )

            def visit_FunctionDef(
                visitor_self,
                node: ast.FunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

            def visit_AsyncFunctionDef(
                visitor_self,
                node: ast.AsyncFunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

        AwaitVisitor().visit(
            root
        )

        return self._deduplicate_strings(
            result
        )

    # ========================================================
    # Raise
    # ========================================================

    def _collect_raises(
        self,
        root: ast.AST,
    ) -> List[str]:
        """
        raise expressionを取得する。
        """

        result: List[str] = []

        parser = self

        class RaiseVisitor(
            ast.NodeVisitor
        ):

            def visit_Raise(
                visitor_self,
                node: ast.Raise,
            ) -> None:

                value = parser._unparse(
                    node.exc
                )

                if value:

                    result.append(
                        value
                    )

            def visit_FunctionDef(
                visitor_self,
                node: ast.FunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

            def visit_AsyncFunctionDef(
                visitor_self,
                node: ast.AsyncFunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

        RaiseVisitor().visit(
            root
        )

        return self._deduplicate_strings(
            result
        )

    # ========================================================
    # Return
    # ========================================================

    def _collect_returns(
        self,
        root: ast.AST,
    ) -> List[Any]:
        """
        return式を取得する。
        """

        result: List[
            Any
        ] = []

        parser = self

        class ReturnVisitor(
            ast.NodeVisitor
        ):

            def visit_Return(
                visitor_self,
                node: ast.Return,
            ) -> None:

                result.append(
                    parser._unparse(
                        node.value
                    )
                )

            def visit_FunctionDef(
                visitor_self,
                node: ast.FunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

            def visit_AsyncFunctionDef(
                visitor_self,
                node: ast.AsyncFunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

        ReturnVisitor().visit(
            root
        )

        return result

    # ========================================================
    # Generator
    # ========================================================

    def _contains_yield(
        self,
        root: ast.AST,
    ) -> bool:
        """
        yield / yield from の存在確認。
        """

        found = False

        class YieldVisitor(
            ast.NodeVisitor
        ):

            def visit_Yield(
                visitor_self,
                node: ast.Yield,
            ) -> None:

                nonlocal found

                found = True

            def visit_YieldFrom(
                visitor_self,
                node: ast.YieldFrom,
            ) -> None:

                nonlocal found

                found = True

            def visit_FunctionDef(
                visitor_self,
                node: ast.FunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

            def visit_AsyncFunctionDef(
                visitor_self,
                node: ast.AsyncFunctionDef,
            ) -> None:

                if node is root:

                    visitor_self.generic_visit(
                        node
                    )

        YieldVisitor().visit(
            root
        )

        return found

    # ========================================================
    # __all__
    # ========================================================

    def _parse_dunder_all(
        self,
        node: ast.Assign
        | ast.AnnAssign,
    ) -> List[str]:
        """
        __all__ をexport情報として解釈する。

        Example:

            __all__ = [
                "KnowledgeRouter",
                "RouteResult",
            ]
        """

        target: Optional[
            ast.AST
        ] = None

        value: Optional[
            ast.AST
        ] = None

        if isinstance(
            node,
            ast.Assign,
        ):

            if len(
                node.targets
            ) != 1:

                return []

            target = (
                node.targets[0]
            )

            value = node.value

        elif isinstance(
            node,
            ast.AnnAssign,
        ):

            target = node.target

            value = node.value

        if not isinstance(
            target,
            ast.Name,
        ):

            return []

        if target.id != "__all__":

            return []

        if not isinstance(
            value,
            (
                ast.List,
                ast.Tuple,
                ast.Set,
            ),
        ):

            return []

        result: List[str] = []

        for element in value.elts:

            if isinstance(
                element,
                ast.Constant,
            ) and isinstance(
                element.value,
                str,
            ):

                result.append(
                    element.value
                )

        return result

    # ========================================================
    # Access
    # ========================================================

    def _infer_access(
        self,
        name: str,
    ) -> str:
        """
        Python命名規則からaccessを推定する。

        __foo:
            private

        _foo:
            protected

        foo:
            public

        __init__などdunderはpublic扱い。
        """

        if (
            name.startswith("__")
            and name.endswith("__")
        ):

            return "public"

        if name.startswith("__"):

            return "private"

        if name.startswith("_"):

            return "protected"

        return "public"

    # ========================================================
    # Callable name
    # ========================================================

    def _callable_name(
        self,
        node: Optional[
            ast.AST
        ],
    ) -> str:
        """
        call targetを文字列へ変換する。

        Examples:

            print

            self.manager.search

            module.Class.method
        """

        if node is None:

            return ""

        if isinstance(
            node,
            ast.Name,
        ):

            return node.id

        if isinstance(
            node,
            ast.Attribute,
        ):

            parent = (
                self._callable_name(
                    node.value
                )
            )

            if parent:

                return (
                    f"{parent}.{node.attr}"
                )

            return node.attr

        if isinstance(
            node,
            ast.Call,
        ):

            return self._callable_name(
                node.func
            )

        try:

            value = ast.unparse(
                node
            )

            return value

        except Exception:

            return ""

    # ========================================================
    # Location
    # ========================================================

    def _location(
        self,
        node: ast.AST,
    ) -> Dict[str, Optional[int]]:
        """
        Python AST位置をBaseParser形式へ変換する。

        BaseParser側は1始まりを推奨しているため、
        columnも+1する。
        """

        start_line = getattr(
            node,
            "lineno",
            None,
        )

        start_column = getattr(
            node,
            "col_offset",
            None,
        )

        end_line = getattr(
            node,
            "end_lineno",
            start_line,
        )

        end_column = getattr(
            node,
            "end_col_offset",
            start_column,
        )

        if start_column is not None:

            start_column += 1

        if end_column is not None:

            end_column += 1

        return self.create_location(
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
        )

    def _node_line(
        self,
        node: ast.AST,
    ) -> Optional[int]:
        """
        Node開始行。
        """

        return getattr(
            node,
            "lineno",
            None,
        )

    # ========================================================
    # Source
    # ========================================================

    def _source_segment(
        self,
        source: str,
        node: ast.AST,
    ) -> str:
        """
        AST Nodeに対応する元コードを取得。
        """

        try:

            value = (
                ast.get_source_segment(
                    source,
                    node,
                )
            )

            return value or ""

        except Exception:

            return ""

    def _unparse(
        self,
        node: Optional[
            ast.AST
        ],
    ) -> Optional[str]:
        """
        AST nodeをコード文字列へ戻す。
        """

        if node is None:

            return None

        try:

            return ast.unparse(
                node
            )

        except Exception:

            return None

    # ========================================================
    # Deduplication
    # ========================================================

    @staticmethod
    def _deduplicate_strings(
        values: List[str],
    ) -> List[str]:
        """
        文字列リストを順序維持で重複除去。
        """

        result: List[str] = []

        seen: set[str] = set()

        for value in values:

            if value in seen:
                continue

            seen.add(
                value
            )

            result.append(
                value
            )

        return result

    @staticmethod
    def _deduplicate_dicts(
        values: List[
            Dict[str, Any]
        ],
    ) -> List[
        Dict[str, Any]
    ]:
        """
        dependency等のdictリストを
        name/type/source/line基準で重複除去。
        """

        result: List[
            Dict[str, Any]
        ] = []

        seen: set[
            tuple[Any, ...]
        ] = set()

        for value in values:

            key = (
                value.get(
                    "name"
                ),
                value.get(
                    "type"
                ),
                value.get(
                    "source"
                ),
                value.get(
                    "line"
                ),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                value
            )

        return result


# ============================================================
# Standalone Test
# ============================================================

if __name__ == "__main__":

    import argparse
    import json

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(levelname)s: "
            "%(message)s"
        ),
    )

    cli = argparse.ArgumentParser(
        description=(
            "Python AST Parser"
        )
    )

    cli.add_argument(
        "file",
        help=(
            "解析対象Pythonファイルの"
            "絶対パス"
        ),
    )

    args = cli.parse_args()

    parser = PythonParser()

    result = parser.parse(
        args.file
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )