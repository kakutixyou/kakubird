#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
javascript_parser.py
====================

JavaScript / JSX ソースコードをAST解析し、
BaseParserの共通形式へ変換するParser。

対応:
    .js
    .mjs
    .cjs
    .jsx

取得対象:
    - import
    - export / export default
    - CommonJS require
    - module.exports / exports.xxx
    - function declaration
    - async function
    - generator function
    - arrow function
    - function expression
    - class
    - class method
    - constructor
    - static method
    - class field
    - variable
    - function / method call
    - await
    - return
    - throw
    - class inheritance
    - JSX
    - source location
    - syntax error
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
    pip install tree-sitter tree-sitter-javascript
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tree_sitter import Language, Parser

try:
    import tree_sitter_javascript as ts_javascript
except ImportError as exc:
    raise ImportError(
        "tree-sitter-javascript がインストールされていません。\n"
        "pip install tree-sitter tree-sitter-javascript"
    ) from exc


# ------------------------------------------------------------
# BaseParser import
#
# 配置に合わせて必要なら変更してください。
#
# 同じpackage内:
#     from .base_parser import BaseParser
#
# 直接実行:
#     from base_parser import BaseParser
# ------------------------------------------------------------

from .base_parser import BaseParser


logger = logging.getLogger(__name__)


class JavaScriptParser(BaseParser):
    """
    JavaScript / JSX AST Parser。
    """

    language = "javascript"

    parser_version = "1.0"

    supported_extensions = {
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
    }

    def __init__(self) -> None:
        super().__init__()

        language = Language(
            ts_javascript.language()
        )

        # tree-sitterのバージョン差を吸収
        try:
            self._parser = Parser(language)

        except TypeError:
            self._parser = Parser()
            self._parser.set_language(language)

    # ========================================================
    # Public API
    # ========================================================

    def parse(
        self,
        file_path: str | Path,
    ) -> Dict[str, Any]:
        """
        JavaScript / JSXファイルを解析する。

        Parameters
        ----------
        file_path:
            解析対象ファイルの絶対パス。

        Returns
        -------
        BaseParser.create_result()形式のdict。
        """

        # ----------------------------------------------------
        # 前回エラーを削除
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
        # ----------------------------------------------------

        source = self.read_text(
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

        source_bytes = source.encode(
            "utf-8"
        )

        metadata = self.create_file_metadata(
            path,
            source,
        )

        # ----------------------------------------------------
        # AST Parse
        # ----------------------------------------------------

        try:

            tree = self._parser.parse(
                source_bytes
            )

        except Exception as exc:

            logger.exception(
                "JavaScript AST parse error: %s",
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

        root = tree.root_node

        # ----------------------------------------------------
        # Collections
        # ----------------------------------------------------

        imports: List[
            Dict[str, Any]
        ] = []

        exports: List[
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

        calls: List[
            Dict[str, Any]
        ] = []

        dependencies: List[
            Dict[str, Any]
        ] = []

        # ----------------------------------------------------
        # Syntax errors
        # ----------------------------------------------------

        self._collect_syntax_errors(
            root,
            source_bytes,
        )

        # ----------------------------------------------------
        # Top-level解析
        # ----------------------------------------------------

        for node in root.named_children:

            # =================================================
            # import
            # =================================================

            if node.type == "import_statement":

                import_info = self._parse_import(
                    node,
                    source_bytes,
                )

                if import_info:

                    imports.append(
                        import_info
                    )

                    dependency_name = (
                        import_info.get("source")
                        or import_info.get("module")
                    )

                    if dependency_name:

                        dependencies.append(
                            self.create_dependency(
                                name=dependency_name,
                                dependency_type="import",
                                source=dependency_name,
                                line=self._node_line(
                                    node
                                ),
                            )
                        )

            # =================================================
            # export
            # =================================================

            elif node.type == "export_statement":

                export_info = self._parse_export(
                    node,
                    source_bytes,
                )

                exports.append(
                    export_info
                )

                # export function/class/variable
                self._parse_exported_declaration(
                    node,
                    source_bytes,
                    functions,
                    classes,
                    methods,
                    variables,
                )

            # =================================================
            # function foo() {}
            # =================================================

            elif node.type in {
                "function_declaration",
                "generator_function_declaration",
            }:

                functions.append(
                    self._parse_function(
                        node,
                        source_bytes,
                        kind="function",
                    )
                )

            # =================================================
            # class Foo {}
            # =================================================

            elif node.type == "class_declaration":

                class_info, class_methods = (
                    self._parse_class(
                        node,
                        source_bytes,
                    )
                )

                classes.append(
                    class_info
                )

                methods.extend(
                    class_methods
                )

                extends = class_info.get(
                    "extends"
                )

                if extends:

                    dependencies.append(
                        self.create_dependency(
                            name=extends,
                            dependency_type="inheritance",
                            source=class_info.get(
                                "name"
                            ),
                            line=self._node_line(
                                node
                            ),
                        )
                    )

            # =================================================
            # const / let / var
            # =================================================

            elif node.type in {
                "lexical_declaration",
                "variable_declaration",
            }:

                (
                    parsed_variables,
                    parsed_functions,
                ) = self._parse_variable_declaration(
                    node,
                    source_bytes,
                )

                variables.extend(
                    parsed_variables
                )

                functions.extend(
                    parsed_functions
                )

            # =================================================
            # expression
            #
            # require(...)
            # module.exports = ...
            # exports.foo = ...
            # =================================================

            elif node.type == "expression_statement":

                commonjs_exports = (
                    self._parse_commonjs_export(
                        node,
                        source_bytes,
                    )
                )

                exports.extend(
                    commonjs_exports
                )

        # ----------------------------------------------------
        # module-level calls
        # ----------------------------------------------------

        calls.extend(
            self._collect_module_calls(
                root,
                source_bytes,
            )
        )

        # ----------------------------------------------------
        # require() imports
        # ----------------------------------------------------

        require_imports = (
            self._collect_require_imports(
                root,
                source_bytes,
            )
        )

        imports.extend(
            require_imports
        )

        for item in require_imports:

            dependency_name = (
                item.get("source")
            )

            if dependency_name:

                dependencies.append(
                    self.create_dependency(
                        name=dependency_name,
                        dependency_type="require",
                        source=dependency_name,
                        line=item.get(
                            "line"
                        ),
                    )
                )

        # ----------------------------------------------------
        # module call dependencies
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
        # export flag反映
        # ----------------------------------------------------

        self._mark_exported_symbols(
            functions,
            classes,
            exports,
        )

        # ----------------------------------------------------
        # Metadata
        # ----------------------------------------------------

        metadata.update(
            {
                "tree_sitter": True,
                "has_syntax_error": (
                    root.has_error
                ),
                "contains_jsx": (
                    self._contains_node_type(
                        root,
                        {
                            "jsx_element",
                            "jsx_self_closing_element",
                            "jsx_fragment",
                        },
                    )
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
            imports=self._deduplicate_dicts(
                imports,
                keys=(
                    "module",
                    "source",
                    "line",
                ),
            ),
            exports=self._deduplicate_dicts(
                exports,
                keys=(
                    "source",
                    "line",
                    "default",
                    "names",
                ),
            ),
            dependencies=self._deduplicate_dicts(
                dependencies,
                keys=(
                    "name",
                    "type",
                    "source",
                    "line",
                ),
            ),
            calls=calls,
            metadata=metadata,
        )

        logger.info(
            (
                "JavaScript parse complete: %s "
                "(classes=%d functions=%d "
                "methods=%d imports=%d exports=%d)"
            ),
            path,
            len(classes),
            len(functions),
            len(methods),
            len(imports),
            len(exports),
        )

        return result

    # ========================================================
    # Import
    # ========================================================

    def _parse_import(
        self,
        node,
        source: bytes,
    ) -> Optional[Dict[str, Any]]:
        """
        import React from "react"

        import {
            useState,
            useEffect as effect
        } from "react"

        import * as Utils from "./utils.js"

        import "./style.css"
        """

        raw = self._text(
            node,
            source,
        )

        source_node = (
            node.child_by_field_name(
                "source"
            )
        )

        module_source = ""

        if source_node:

            module_source = (
                self._strip_quotes(
                    self._text(
                        source_node,
                        source,
                    )
                )
            )

        names: List[str] = []
        aliases: Dict[str, str] = {}

        self._collect_import_names(
            node,
            source,
            names,
            aliases,
        )

        return self.create_import(
            module=module_source,
            source=module_source,
            names=self._deduplicate_strings(
                names
            ),
            aliases=aliases,
            line=self._node_line(
                node
            ),
            location=self._location(
                node
            ),
            raw=raw,
        )

    def _collect_import_names(
        self,
        node,
        source: bytes,
        names: List[str],
        aliases: Dict[str, str],
    ) -> None:
        """
        import構文内のsymbol名を抽出する。
        """

        node_type = node.type

        # import React from ...
        if node_type == "identifier":

            text = self._text(
                node,
                source,
            )

            if text:
                names.append(
                    text
                )

        # import { x as y }
        elif node_type == "import_specifier":

            name_node = (
                node.child_by_field_name(
                    "name"
                )
            )

            alias_node = (
                node.child_by_field_name(
                    "alias"
                )
            )

            original = (
                self._text(
                    name_node,
                    source,
                )
                if name_node
                else ""
            )

            alias_name = (
                self._text(
                    alias_node,
                    source,
                )
                if alias_node
                else ""
            )

            if original:

                names.append(
                    original
                )

            if (
                original
                and alias_name
            ):

                aliases[
                    alias_name
                ] = original

            return

        # import * as Utils
        elif node_type == "namespace_import":

            identifiers = [
                self._text(
                    child,
                    source,
                )
                for child
                in node.named_children
                if child.type
                == "identifier"
            ]

            for identifier in identifiers:

                if identifier:
                    names.append(
                        identifier
                    )

            return

        for child in node.named_children:

            # source stringはsymbolではない
            if child.type in {
                "string",
                "string_fragment",
            }:
                continue

            self._collect_import_names(
                child,
                source,
                names,
                aliases,
            )

    # ========================================================
    # CommonJS require
    # ========================================================

    def _collect_require_imports(
        self,
        root,
        source: bytes,
    ) -> List[Dict[str, Any]]:
        """
        require("module") をimport相当として取得する。
        """

        result: List[
            Dict[str, Any]
        ] = []

        def walk(node) -> None:

            if node.type == "call_expression":

                function_node = (
                    node.child_by_field_name(
                        "function"
                    )
                )

                function_name = (
                    self._text(
                        function_node,
                        source,
                    )
                    if function_node
                    else ""
                )

                if function_name == "require":

                    arguments = (
                        node.child_by_field_name(
                            "arguments"
                        )
                    )

                    module_name = ""

                    if arguments:

                        for child in arguments.named_children:

                            if child.type == "string":

                                module_name = (
                                    self._strip_quotes(
                                        self._text(
                                            child,
                                            source,
                                        )
                                    )
                                )

                                break

                    if module_name:

                        result.append(
                            self.create_import(
                                module=module_name,
                                source=module_name,
                                names=[],
                                line=self._node_line(
                                    node
                                ),
                                location=self._location(
                                    node
                                ),
                                raw=self._text(
                                    node,
                                    source,
                                ),
                            )
                        )

            for child in node.named_children:

                walk(
                    child
                )

        walk(
            root
        )

        return result

    # ========================================================
    # Export
    # ========================================================

    def _parse_export(
        self,
        node,
        source: bytes,
    ) -> Dict[str, Any]:
        """
        export構文を解析する。
        """

        raw = self._text(
            node,
            source,
        )

        names: List[str] = []

        export_source: Optional[
            str
        ] = None

        default_export = False

        for child in node.children:

            child_text = self._text(
                child,
                source,
            )

            if child_text == "default":

                default_export = True

        source_node = (
            node.child_by_field_name(
                "source"
            )
        )

        if source_node:

            export_source = (
                self._strip_quotes(
                    self._text(
                        source_node,
                        source,
                    )
                )
            )

        self._collect_export_names(
            node,
            source,
            names,
        )

        return self.create_export(
            names=self._deduplicate_strings(
                names
            ),
            default=default_export,
            source=export_source,
            line=self._node_line(
                node
            ),
            location=self._location(
                node
            ),
            raw=raw,
        )

    def _collect_export_names(
        self,
        node,
        source: bytes,
        names: List[str],
    ) -> None:
        """
        exportされる名前を抽出。
        """

        if node.type in {
            "function_declaration",
            "generator_function_declaration",
            "class_declaration",
        }:

            name_node = (
                node.child_by_field_name(
                    "name"
                )
            )

            if name_node:

                name = self._text(
                    name_node,
                    source,
                )

                if name:
                    names.append(
                        name
                    )

                return

        elif node.type == "export_specifier":

            name_node = (
                node.child_by_field_name(
                    "name"
                )
            )

            if name_node:

                name = self._text(
                    name_node,
                    source,
                )

                if name:
                    names.append(
                        name
                    )

            return

        elif node.type == "variable_declarator":

            name_node = (
                node.child_by_field_name(
                    "name"
                )
            )

            if name_node:

                names.extend(
                    self._extract_pattern_names(
                        name_node,
                        source,
                    )
                )

            return

        for child in node.named_children:

            self._collect_export_names(
                child,
                source,
                names,
            )

    # ========================================================
    # Exported declaration
    # ========================================================

    def _parse_exported_declaration(
        self,
        export_node,
        source: bytes,
        functions: List[Dict[str, Any]],
        classes: List[Dict[str, Any]],
        methods: List[Dict[str, Any]],
        variables: List[Dict[str, Any]],
    ) -> None:
        """
        export function foo() {}
        export class Foo {}
        export const foo = () => {}
        を通常symbolにも追加する。
        """

        for child in export_node.named_children:

            if child.type in {
                "function_declaration",
                "generator_function_declaration",
            }:

                function = (
                    self._parse_function(
                        child,
                        source,
                        kind="function",
                    )
                )

                function[
                    "is_exported"
                ] = True

                functions.append(
                    function
                )

            elif child.type == "class_declaration":

                (
                    class_info,
                    class_methods,
                ) = self._parse_class(
                    child,
                    source,
                )

                class_info[
                    "is_exported"
                ] = True

                classes.append(
                    class_info
                )

                methods.extend(
                    class_methods
                )

            elif child.type in {
                "lexical_declaration",
                "variable_declaration",
            }:

                (
                    parsed_variables,
                    parsed_functions,
                ) = (
                    self._parse_variable_declaration(
                        child,
                        source,
                    )
                )

                for function in parsed_functions:

                    function[
                        "is_exported"
                    ] = True

                variables.extend(
                    parsed_variables
                )

                functions.extend(
                    parsed_functions
                )

    # ========================================================
    # CommonJS Export
    # ========================================================

    def _parse_commonjs_export(
        self,
        node,
        source: bytes,
    ) -> List[Dict[str, Any]]:
        """
        module.exports = Foo
        exports.foo = foo
        module.exports.foo = foo
        """

        result: List[
            Dict[str, Any]
        ] = []

        raw = self._text(
            node,
            source,
        )

        for child in node.named_children:

            if child.type != "assignment_expression":
                continue

            left = (
                child.child_by_field_name(
                    "left"
                )
            )

            right = (
                child.child_by_field_name(
                    "right"
                )
            )

            if not left:
                continue

            left_text = self._text(
                left,
                source,
            )

            right_text = (
                self._text(
                    right,
                    source,
                )
                if right
                else ""
            )

            # module.exports = Foo
            if left_text == "module.exports":

                names = (
                    [right_text]
                    if right_text
                    else []
                )

                result.append(
                    self.create_export(
                        names=names,
                        default=True,
                        line=self._node_line(
                            child
                        ),
                        location=self._location(
                            child
                        ),
                        raw=raw,
                    )
                )

            # exports.foo = foo
            elif left_text.startswith(
                "exports."
            ):

                export_name = (
                    left_text.split(
                        ".",
                        1,
                    )[1]
                )

                result.append(
                    self.create_export(
                        names=[
                            export_name
                        ],
                        default=False,
                        line=self._node_line(
                            child
                        ),
                        location=self._location(
                            child
                        ),
                        raw=raw,
                    )
                )

            # module.exports.foo = foo
            elif left_text.startswith(
                "module.exports."
            ):

                export_name = (
                    left_text[
                        len(
                            "module.exports."
                        ):
                    ]
                )

                result.append(
                    self.create_export(
                        names=[
                            export_name
                        ],
                        default=False,
                        line=self._node_line(
                            child
                        ),
                        location=self._location(
                            child
                        ),
                        raw=raw,
                    )
                )

        return result

    # ========================================================
    # Function
    # ========================================================

    def _parse_function(
        self,
        node,
        source: bytes,
        *,
        kind: str,
        forced_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        function / arrow function / function expressionを解析する。
        """

        name_node = (
            node.child_by_field_name(
                "name"
            )
        )

        if forced_name:

            name = forced_name

        elif name_node:

            name = self._text(
                name_node,
                source,
            )

        else:

            name = "<anonymous>"

        parameters = (
            self._parse_parameters(
                node,
                source,
            )
        )

        calls = (
            self._collect_calls_inside(
                node,
                source,
            )
        )

        awaits = (
            self._collect_awaits(
                node,
                source,
            )
        )

        throws = (
            self._collect_throws(
                node,
                source,
            )
        )

        returns = (
            self._collect_returns(
                node,
                source,
            )
        )

        is_async = self._has_token(
            node,
            source,
            "async",
        )

        raw = self._text(
            node,
            source,
        )

        is_generator = (
            node.type
            in {
                "generator_function",
                "generator_function_declaration",
            }
            or self._has_direct_token(
                node,
                source,
                "*",
            )
        )

        return self.create_function(
            name=name,

            parameters=parameters,

            line=self._node_line(
                node
            ),

            location=self._location(
                node
            ),

            modifiers=self._function_modifiers(
                is_async=is_async,
                is_generator=is_generator,
            ),

            calls=calls,

            awaits=awaits,

            raises=throws,

            returns=returns,

            is_async=is_async,

            is_generator=is_generator,

            raw=raw,
        )

    # ========================================================
    # Variable declaration
    # ========================================================

    def _parse_variable_declaration(
        self,
        node,
        source: bytes,
    ) -> tuple[
        List[Dict[str, Any]],
        List[Dict[str, Any]],
    ]:
        """
        const foo = 1
        let bar = 2
        var baz = 3

        const load = async () => {}
        const fn = function() {}
        """

        variables: List[
            Dict[str, Any]
        ] = []

        functions: List[
            Dict[str, Any]
        ] = []

        declaration_kind = (
            self._variable_kind(
                node,
                source,
            )
        )

        for child in node.named_children:

            if child.type != "variable_declarator":
                continue

            name_node = (
                child.child_by_field_name(
                    "name"
                )
            )

            value_node = (
                child.child_by_field_name(
                    "value"
                )
            )

            if not name_node:
                continue

            names = self._extract_pattern_names(
                name_node,
                source,
            )

            value = (
                self._text(
                    value_node,
                    source,
                )
                if value_node
                else None
            )

            value_type = (
                value_node.type
                if value_node
                else None
            )

            for name in names:

                variables.append(
                    self.create_variable(
                        name=name,

                        var_type=value_type,

                        value=value,

                        scope="module",

                        access="public",

                        line=self._node_line(
                            child
                        ),

                        location=self._location(
                            child
                        ),

                        modifiers=(
                            [declaration_kind]
                            if declaration_kind
                            else []
                        ),
                    )
                )

            if not value_node:
                continue

            function_name = (
                names[0]
                if names
                else "<anonymous>"
            )

            # ---------------------------------------------
            # const foo = () => {}
            # ---------------------------------------------

            if value_node.type == "arrow_function":

                functions.append(
                    self._parse_function(
                        value_node,
                        source,
                        kind="arrow",
                        forced_name=function_name,
                    )
                )

            # ---------------------------------------------
            # const foo = function() {}
            # ---------------------------------------------

            elif value_node.type in {
                "function_expression",
                "generator_function",
            }:

                functions.append(
                    self._parse_function(
                        value_node,
                        source,
                        kind="function_expression",
                        forced_name=function_name,
                    )
                )

        return (
            variables,
            functions,
        )

    # ========================================================
    # Pattern names
    # ========================================================

    def _extract_pattern_names(
        self,
        node,
        source: bytes,
    ) -> List[str]:
        """
        JavaScript変数patternから名前を取得。

        const a = ...
        const { a, b } = ...
        const [a, b] = ...
        """

        if node is None:
            return []

        if node.type in {
            "identifier",
            "shorthand_property_identifier_pattern",
        }:

            text = self._text(
                node,
                source,
            )

            return (
                [text]
                if text
                else []
            )

        result: List[str] = []

        for child in node.named_children:

            result.extend(
                self._extract_pattern_names(
                    child,
                    source,
                )
            )

        return self._deduplicate_strings(
            result
        )

    # ========================================================
    # Class
    # ========================================================

    def _parse_class(
        self,
        node,
        source: bytes,
    ) -> tuple[
        Dict[str, Any],
        List[Dict[str, Any]],
    ]:
        """
        JavaScript classを解析する。
        """

        name_node = (
            node.child_by_field_name(
                "name"
            )
        )

        name = (
            self._text(
                name_node,
                source,
            )
            if name_node
            else "<anonymous>"
        )

        superclass_node = (
            node.child_by_field_name(
                "superclass"
            )
        )

        extends = (
            self._text(
                superclass_node,
                source,
            )
            if superclass_node
            else None
        )

        methods: List[
            Dict[str, Any]
        ] = []

        class_variables: List[
            Dict[str, Any]
        ] = []

        body_node = (
            node.child_by_field_name(
                "body"
            )
        )

        if body_node:

            for child in body_node.named_children:

                # -----------------------------------------
                # method
                # -----------------------------------------

                if child.type == "method_definition":

                    methods.append(
                        self._parse_method(
                            child,
                            source,
                            class_name=name,
                        )
                    )

                # -----------------------------------------
                # class field
                # -----------------------------------------

                elif child.type in {
                    "field_definition",
                    "public_field_definition",
                }:

                    field = self._parse_class_field(
                        child,
                        source,
                        class_name=name,
                    )

                    if field:
                        class_variables.append(
                            field
                        )

        return (
            self.create_class(
                name=name,

                line=self._node_line(
                    node
                ),

                location=self._location(
                    node
                ),

                extends=extends,

                bases=(
                    [extends]
                    if extends
                    else []
                ),

                methods=methods,

                variables=class_variables,
            ),
            methods,
        )

    # ========================================================
    # Method
    # ========================================================

    def _parse_method(
        self,
        node,
        source: bytes,
        *,
        class_name: str,
    ) -> Dict[str, Any]:
        """
        class methodを解析する。
        """

        name_node = (
            node.child_by_field_name(
                "name"
            )
        )

        name = (
            self._text(
                name_node,
                source,
            )
            if name_node
            else "<anonymous>"
        )

        is_async = self._has_token(
            node,
            source,
            "async",
        )

        is_static = self._has_token(
            node,
            source,
            "static",
        )

        modifiers: List[str] = []

        if is_async:
            modifiers.append(
                "async"
            )

        if is_static:
            modifiers.append(
                "static"
            )

        kind_node = (
            node.child_by_field_name(
                "kind"
            )
        )

        if kind_node:

            kind_text = self._text(
                kind_node,
                source,
            )

            if kind_text:

                modifiers.append(
                    kind_text
                )

        return self.create_method(
            name=name,

            parameters=self._parse_parameters(
                node,
                source,
            ),

            access=self._infer_js_access(
                name
            ),

            line=self._node_line(
                node
            ),

            location=self._location(
                node
            ),

            modifiers=self._deduplicate_strings(
                modifiers
            ),

            calls=self._collect_calls_inside(
                node,
                source,
            ),

            awaits=self._collect_awaits(
                node,
                source,
            ),

            raises=self._collect_throws(
                node,
                source,
            ),

            is_async=is_async,

            is_static=is_static,

            raw=self._text(
                node,
                source,
            ),
        )

    # ========================================================
    # Class field
    # ========================================================

    def _parse_class_field(
        self,
        node,
        source: bytes,
        *,
        class_name: str,
    ) -> Optional[Dict[str, Any]]:

        name_node = (
            node.child_by_field_name(
                "property"
            )
            or node.child_by_field_name(
                "name"
            )
        )

        value_node = (
            node.child_by_field_name(
                "value"
            )
        )

        if not name_node:

            if node.named_children:

                name_node = (
                    node.named_children[0]
                )

        if not name_node:
            return None

        name = self._text(
            name_node,
            source,
        )

        if not name:
            return None

        return self.create_variable(
            name=name,

            value=(
                self._text(
                    value_node,
                    source,
                )
                if value_node
                else None
            ),

            scope=f"class:{class_name}",

            access=self._infer_js_access(
                name
            ),

            line=self._node_line(
                node
            ),

            location=self._location(
                node
            ),
        )

    # ========================================================
    # Parameters
    # ========================================================

    def _parse_parameters(
        self,
        node,
        source: bytes,
    ) -> List[Dict[str, Any]]:
        """
        function parameterを取得する。
        """

        parameters_node = (
            node.child_by_field_name(
                "parameters"
            )
        )

        # arrow function:
        # x => x + 1
        if parameters_node is None:

            parameter_node = (
                node.child_by_field_name(
                    "parameter"
                )
            )

            if parameter_node:

                return [
                    self.create_parameter(
                        name=self._text(
                            parameter_node,
                            source,
                        ),
                        kind="positional",
                    )
                ]

            return []

        result: List[
            Dict[str, Any]
        ] = []

        for child in parameters_node.named_children:

            # ---------------------------------------------
            # normal parameter
            # ---------------------------------------------

            if child.type == "identifier":

                result.append(
                    self.create_parameter(
                        name=self._text(
                            child,
                            source,
                        ),
                        kind="positional",
                    )
                )

            # ---------------------------------------------
            # default parameter
            #
            # foo = 10
            # ---------------------------------------------

            elif child.type == "assignment_pattern":

                left = (
                    child.child_by_field_name(
                        "left"
                    )
                )

                right = (
                    child.child_by_field_name(
                        "right"
                    )
                )

                result.append(
                    self.create_parameter(
                        name=(
                            self._text(
                                left,
                                source,
                            )
                            if left
                            else self._text(
                                child,
                                source,
                            )
                        ),
                        default=(
                            self._text(
                                right,
                                source,
                            )
                            if right
                            else None
                        ),
                        kind="positional",
                    )
                )

            # ---------------------------------------------
            # ...args
            # ---------------------------------------------

            elif child.type == "rest_pattern":

                argument_node = (
                    child.named_children[0]
                    if child.named_children
                    else None
                )

                name = (
                    self._text(
                        argument_node,
                        source,
                    )
                    if argument_node
                    else self._text(
                        child,
                        source,
                    ).lstrip(".")
                )

                result.append(
                    self.create_parameter(
                        name=name,
                        kind="rest",
                    )
                )

            # ---------------------------------------------
            # destructuring
            #
            # function f({name, age}) {}
            # ---------------------------------------------

            elif child.type in {
                "object_pattern",
                "array_pattern",
            }:

                result.append(
                    self.create_parameter(
                        name=self._text(
                            child,
                            source,
                        ),
                        kind="destructuring",
                    )
                )

            else:

                text = self._text(
                    child,
                    source,
                )

                if text:

                    result.append(
                        self.create_parameter(
                            name=text,
                            kind="unknown",
                        )
                    )

        return result

    # ========================================================
    # Calls
    # ========================================================

    def _collect_calls_inside(
        self,
        root,
        source: bytes,
    ) -> List[str]:
        """
        function/method内部のcallを取得。

        nested function/classには入らない。
        """

        result: List[str] = []

        def walk(node) -> None:

            # root以外のnested functionをスキップ
            if (
                node is not root
                and node.type
                in {
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                    "generator_function",
                    "generator_function_declaration",
                    "class_declaration",
                    "class",
                }
            ):
                return

            if node.type == "call_expression":

                name = self._extract_call_name(
                    node,
                    source,
                )

                if name:

                    result.append(
                        name
                    )

            for child in node.named_children:

                walk(
                    child
                )

        walk(
            root
        )

        return self._deduplicate_strings(
            result
        )

    def _collect_module_calls(
        self,
        root,
        source: bytes,
    ) -> List[Dict[str, Any]]:
        """
        module直下で実行されるcallを取得。

        function / class内部は除外する。
        """

        result: List[
            Dict[str, Any]
        ] = []

        def walk(node) -> None:

            if node.type in {
                "function_declaration",
                "function_expression",
                "arrow_function",
                "generator_function",
                "generator_function_declaration",
                "class_declaration",
                "class",
            }:
                return

            if node.type == "call_expression":

                name = self._extract_call_name(
                    node,
                    source,
                )

                if name:

                    arguments = (
                        self._extract_call_arguments(
                            node,
                            source,
                        )
                    )

                    result.append(
                        self.create_call(
                            name=name,

                            line=self._node_line(
                                node
                            ),

                            location=self._location(
                                node
                            ),

                            arguments=arguments,

                            scope="module",
                        )
                    )

            for child in node.named_children:

                walk(
                    child
                )

        for child in root.named_children:

            walk(
                child
            )

        return result

    def _extract_call_name(
        self,
        node,
        source: bytes,
    ) -> str:

        function_node = (
            node.child_by_field_name(
                "function"
            )
        )

        if not function_node:
            return ""

        return self._text(
            function_node,
            source,
        )

    def _extract_call_arguments(
        self,
        node,
        source: bytes,
    ) -> List[str]:

        arguments_node = (
            node.child_by_field_name(
                "arguments"
            )
        )

        if not arguments_node:
            return []

        return [
            self._text(
                child,
                source,
            )
            for child
            in arguments_node.named_children
        ]

    # ========================================================
    # Await
    # ========================================================

    def _collect_awaits(
        self,
        root,
        source: bytes,
    ) -> List[str]:

        result: List[str] = []

        def walk(node) -> None:

            if (
                node is not root
                and node.type
                in {
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                    "generator_function",
                    "class_declaration",
                }
            ):
                return

            if node.type == "await_expression":

                text = self._text(
                    node,
                    source,
                )

                if text.startswith(
                    "await "
                ):

                    text = text[
                        len("await "):
                    ]

                if text:

                    result.append(
                        text
                    )

            for child in node.named_children:

                walk(
                    child
                )

        walk(
            root
        )

        return self._deduplicate_strings(
            result
        )

    # ========================================================
    # Throw
    # ========================================================

    def _collect_throws(
        self,
        root,
        source: bytes,
    ) -> List[str]:

        result: List[str] = []

        def walk(node) -> None:

            if (
                node is not root
                and node.type
                in {
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                    "generator_function",
                    "class_declaration",
                }
            ):
                return

            if node.type == "throw_statement":

                raw = self._text(
                    node,
                    source,
                )

                value = raw.strip()

                if value.startswith(
                    "throw"
                ):

                    value = value[
                        len("throw"):
                    ].strip()

                value = value.rstrip(
                    ";"
                ).strip()

                if value:

                    result.append(
                        value
                    )

            for child in node.named_children:

                walk(
                    child
                )

        walk(
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
        root,
        source: bytes,
    ) -> List[Any]:

        result: List[Any] = []

        def walk(node) -> None:

            if (
                node is not root
                and node.type
                in {
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                    "generator_function",
                    "class_declaration",
                }
            ):
                return

            if node.type == "return_statement":

                raw = self._text(
                    node,
                    source,
                ).strip()

                if raw.startswith(
                    "return"
                ):

                    value = raw[
                        len("return"):
                    ].strip()

                    value = value.rstrip(
                        ";"
                    ).strip()

                    result.append(
                        value or None
                    )

            for child in node.named_children:

                walk(
                    child
                )

        walk(
            root
        )

        return result

    # ========================================================
    # Syntax Error
    # ========================================================

    def _collect_syntax_errors(
        self,
        root,
        source: bytes,
    ) -> None:
        """
        tree-sitter ERROR / missing nodeを取得する。
        """

        def walk(node) -> None:

            if node.type == "ERROR":

                self.add_error(
                    "JavaScript syntax error",
                    error_type="syntax_error",
                    line=(
                        node.start_point[0]
                        + 1
                    ),
                    column=(
                        node.start_point[1]
                        + 1
                    ),
                    end_line=(
                        node.end_point[0]
                        + 1
                    ),
                    end_column=(
                        node.end_point[1]
                        + 1
                    ),
                    details={
                        "raw": self._text(
                            node,
                            source,
                        )
                    },
                )

            if getattr(
                node,
                "is_missing",
                False,
            ):

                self.add_error(
                    (
                        "JavaScript syntax node "
                        f"is missing: {node.type}"
                    ),
                    error_type="missing_syntax",
                    line=(
                        node.start_point[0]
                        + 1
                    ),
                    column=(
                        node.start_point[1]
                        + 1
                    ),
                )

            for child in node.children:

                walk(
                    child
                )

        walk(
            root
        )

    # ========================================================
    # Export Flag
    # ========================================================

    def _mark_exported_symbols(
        self,
        functions: List[Dict[str, Any]],
        classes: List[Dict[str, Any]],
        exports: List[Dict[str, Any]],
    ) -> None:

        exported_names: set[str] = set()

        for export in exports:

            for name in export.get(
                "names",
                [],
            ):

                if name:

                    exported_names.add(
                        name
                    )

        for function in functions:

            if function.get(
                "name"
            ) in exported_names:

                function[
                    "is_exported"
                ] = True

        for class_info in classes:

            if class_info.get(
                "name"
            ) in exported_names:

                class_info[
                    "is_exported"
                ] = True

    # ========================================================
    # Access
    # ========================================================

    def _infer_js_access(
        self,
        name: str,
    ) -> str:
        """
        JavaScript private field #foo を判定。
        """

        if name.startswith(
            "#"
        ):
            return "private"

        return "public"

    # ========================================================
    # Variable Kind
    # ========================================================

    def _variable_kind(
        self,
        node,
        source: bytes,
    ) -> str:

        raw = self._text(
            node,
            source,
        ).lstrip()

        for keyword in (
            "const",
            "let",
            "var",
        ):

            if raw.startswith(
                keyword
            ):

                return keyword

        return ""

    # ========================================================
    # Function modifiers
    # ========================================================

    def _function_modifiers(
        self,
        *,
        is_async: bool,
        is_generator: bool,
    ) -> List[str]:

        result: List[str] = []

        if is_async:
            result.append(
                "async"
            )

        if is_generator:
            result.append(
                "generator"
            )

        return result

    # ========================================================
    # Tree utilities
    # ========================================================

    def _contains_node_type(
        self,
        root,
        target_types: set[str],
    ) -> bool:

        found = False

        def walk(node) -> None:

            nonlocal found

            if found:
                return

            if node.type in target_types:

                found = True
                return

            for child in node.named_children:

                walk(
                    child
                )

        walk(
            root
        )

        return found

    def _has_token(
        self,
        node,
        source: bytes,
        token: str,
    ) -> bool:
        """
        直接child tokenに指定文字列が存在するか。
        """

        for child in node.children:

            if self._text(
                child,
                source,
            ) == token:

                return True

        return False

    def _has_direct_token(
        self,
        node,
        source: bytes,
        token: str,
    ) -> bool:

        return self._has_token(
            node,
            source,
            token,
        )

    # ========================================================
    # Location
    # ========================================================

    def _location(
        self,
        node,
    ) -> Dict[str, Optional[int]]:

        return self.create_location(
            start_line=(
                node.start_point[0]
                + 1
            ),
            start_column=(
                node.start_point[1]
                + 1
            ),
            end_line=(
                node.end_point[0]
                + 1
            ),
            end_column=(
                node.end_point[1]
                + 1
            ),
        )

    def _node_line(
        self,
        node,
    ) -> Optional[int]:

        if node is None:
            return None

        return (
            node.start_point[0]
            + 1
        )

    # ========================================================
    # Text
    # ========================================================

    def _text(
        self,
        node,
        source: bytes,
    ) -> str:

        if node is None:
            return ""

        return source[
            node.start_byte:
            node.end_byte
        ].decode(
            "utf-8",
            errors="replace",
        )

    @staticmethod
    def _strip_quotes(
        value: str,
    ) -> str:

        value = value.strip()

        if (
            len(value) >= 2
            and value[0]
            == value[-1]
            and value[0]
            in {
                "'",
                '"',
                "`",
            }
        ):

            return value[
                1:-1
            ]

        return value

    # ========================================================
    # Deduplication
    # ========================================================

    @staticmethod
    def _deduplicate_strings(
        values: List[str],
    ) -> List[str]:

        result: List[str] = []

        seen: set[str] = set()

        for value in values:

            if not value:
                continue

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
    def _freeze_value(
        value: Any,
    ) -> Any:
        """
        list/dictをset比較可能な値へ変換する。
        """

        if isinstance(
            value,
            dict,
        ):

            return tuple(
                sorted(
                    (
                        key,
                        JavaScriptParser._freeze_value(
                            child
                        ),
                    )
                    for key, child
                    in value.items()
                )
            )

        if isinstance(
            value,
            list,
        ):

            return tuple(
                JavaScriptParser._freeze_value(
                    child
                )
                for child in value
            )

        if isinstance(
            value,
            set,
        ):

            return tuple(
                sorted(
                    JavaScriptParser._freeze_value(
                        child
                    )
                    for child in value
                )
            )

        return value

    @classmethod
    def _deduplicate_dicts(
        cls,
        values: List[Dict[str, Any]],
        *,
        keys: tuple[str, ...],
    ) -> List[Dict[str, Any]]:

        result: List[
            Dict[str, Any]
        ] = []

        seen: set[
            tuple[Any, ...]
        ] = set()

        for value in values:

            key = tuple(
                cls._freeze_value(
                    value.get(
                        name
                    )
                )
                for name in keys
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
            "JavaScript / JSX AST Parser"
        )
    )

    cli.add_argument(
        "file",
        help=(
            "解析対象JavaScript/JSXファイルの"
            "絶対パス"
        ),
    )

    args = cli.parse_args()

    parser = JavaScriptParser()

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