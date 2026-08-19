# plugins/java_parser.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import traceback

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Iterable,
)


# ============================================================
# TODO:
# 実際の絶対パス・パッケージ構成に合わせて変更してください。
# ============================================================

from parsers.base_parser import BaseParser
from engine.java_knowledge import JavaKnowledgeLoader


class JavaParser(BaseParser):
    """
    Javaソースコード解析用Parser。

    ============================================================
    役割
    ============================================================

    JavaParser自身は、

    ・Javaコードを読み取る
    ・コメントを除去する
    ・構造を解析する
    ・変数 / クラス / メソッド等の関係を調べる

    ことに集中する。

    Javaについての知識、

    ・キーワード
    ・modifier
    ・primitive type
    ・基本Regex
    ・意味情報

    などは knowledge/parsers/java/*.json
    および JavaKnowledgeLoader に委譲する。

    ============================================================
    想定Knowledge
    ============================================================

    knowledge/
    └── parsers/
        └── java/
            ├── java_keywords.json
            ├── java_modifiers.json
            ├── java_types.json
            ├── java_patterns.json
            └── java_semantics.json

    ============================================================
    解析対象
    ============================================================

    ・package
    ・import
    ・class
    ・interface
    ・enum
    ・record
    ・extends
    ・implements
    ・annotation
    ・field
    ・method
    ・constructor
    ・parameter
    ・return
    ・throws
    ・method call
    ・field read / write
    ・local variable
    ・dependency

    ============================================================
    注意
    ============================================================

    Javaコンパイラではない。

    完全な構文検証ではなく、
    AIによるコード説明の前段に置く
    「軽量静的解析器」を目的とする。
    """

    language = "java"

    # ========================================================
    # 初期化
    # ========================================================

    def __init__(self, knowledge_dir: str) -> None:
        super().__init__()

        # ----------------------------------------------------
        # Knowledgeロード
        # ----------------------------------------------------

        loader = JavaKnowledgeLoader(knowledge_dir)

        self.knowledge_loader = loader
        self.knowledge = loader.data

        # ----------------------------------------------------
        # JSON → Setへ変換
        # ----------------------------------------------------

        self.control_keywords: Set[str] = set(
            self.knowledge.keywords.get(
                "control_keywords",
                []
            )
        )

        self.language_keywords: Set[str] = set(
            self.knowledge.keywords.get(
                "language_keywords",
                []
            )
        )

        self.java_keywords: Set[str] = (
            self.control_keywords
            | self.language_keywords
        )

        self.access_modifiers: Set[str] = set(
            self.knowledge.modifiers.get(
                "access_modifiers",
                []
            )
        )

        self.modifiers: Set[str] = set(
            self.knowledge.modifiers.get(
                "modifiers",
                []
            )
        )

        self.primitive_types: Set[str] = set(
            self.knowledge.types.get(
                "primitive_types",
                []
            )
        )

        self.common_types: Set[str] = set(
            self.knowledge.types.get(
                "common_types",
                []
            )
        )

        self.type_categories: Dict[str, List[str]] = (
            self.knowledge.types.get(
                "type_categories",
                {}
            )
        )

        # ----------------------------------------------------
        # 解析状態
        # ----------------------------------------------------

        self.current_class: Optional[str] = None

        self.known_fields: Set[str] = set()

        self.known_methods: Set[str] = set()

        self.known_classes: Set[str] = set()

    # ========================================================
    # メイン
    # ========================================================

    def parse(
        self,
        source_code: str
    ) -> Dict[str, Any]:
        """
        Javaコード全体を解析する。
        """

        self.clear_errors()
        self._reset_state()

        source_code = self.normalize_code(
            source_code
        )

        if not self.validate_code(
            source_code
        ):
            return self.create_result()

        try:

            # ------------------------------------------------
            # 1. コメント除去
            # ------------------------------------------------

            clean_code = (
                self._remove_comments_preserve_lines(
                    source_code
                )
            )

            # ------------------------------------------------
            # 2. package
            # ------------------------------------------------

            package_name = self._parse_package(
                clean_code
            )

            # ------------------------------------------------
            # 3. import
            # ------------------------------------------------

            imports = self._parse_imports(
                clean_code
            )

            # ------------------------------------------------
            # 4. class / interface / enum / record
            # ------------------------------------------------

            classes = self._parse_types(
                clean_code
            )

            self.known_classes = {
                item["name"]
                for item in classes
                if item.get("name")
            }

            if classes:
                self.current_class = (
                    classes[0].get("name")
                )

            # ------------------------------------------------
            # 5. field
            # ------------------------------------------------

            fields = self._parse_fields(
                clean_code,
                classes
            )

            self.known_fields = {
                item["name"]
                for item in fields
                if item.get("name")
            }

            # ------------------------------------------------
            # 6. method / constructor
            # ------------------------------------------------

            methods = self._parse_methods(
                clean_code,
                classes
            )

            self.known_methods = {
                item["name"]
                for item in methods
                if item.get("name")
            }

            # ------------------------------------------------
            # 7. dependency
            # ------------------------------------------------

            dependencies = (
                self._build_dependencies(
                    imports=imports,
                    classes=classes,
                    fields=fields,
                    methods=methods,
                )
            )

            # ------------------------------------------------
            # 8. metadata
            # ------------------------------------------------

            metadata = {
                "package": package_name,

                "line_count":
                    self.count_lines(source_code),

                "class_count":
                    len(classes),

                "field_count":
                    len(fields),

                "method_count":
                    len(methods),

                "import_count":
                    len(imports),

                "dependency_count":
                    len(dependencies),

                "parser":
                    self.__class__.__name__,

                "knowledge_based":
                    True,
            }

            # ------------------------------------------------
            # 9. 共通形式
            # ------------------------------------------------

            return self.create_result(
                classes=classes,
                methods=methods,
                variables=fields,
                imports=imports,

                interfaces=[
                    item
                    for item in classes
                    if item.get("kind")
                    == "interface"
                ],

                dependencies=dependencies,

                metadata=metadata,
            )

        except Exception as exc:

            traceback.print_exc()

            self.add_error(
                str(exc),
                error_type=(
                    "java_parser_exception"
                ),
                details={
                    "exception":
                        exc.__class__.__name__,
                },
            )

            return self.create_result(
                metadata={
                    "line_count":
                        self.count_lines(
                            source_code
                        ),

                    "parser":
                        self.__class__.__name__,

                    "knowledge_based":
                        True,
                }
            )

    # ========================================================
    # 状態リセット
    # ========================================================

    def _reset_state(self) -> None:

        self.current_class = None

        self.known_fields.clear()
        self.known_methods.clear()
        self.known_classes.clear()

    # ========================================================
    # Package
    # ========================================================

    def _parse_package(
        self,
        code: str
    ) -> Optional[str]:

        pattern = self._get_pattern(
            "package"
        )

        if pattern is None:
            self.add_error(
                "package解析用Patternがありません。",
                error_type=(
                    "knowledge_pattern_missing"
                ),
                severity="warning",
            )

            return None

        match = pattern.search(code)

        if not match:
            return None

        return match.group(1)

    # ========================================================
    # Import
    # ========================================================

    def _parse_imports(
        self,
        code: str
    ) -> List[Dict[str, Any]]:

        results: List[Dict[str, Any]] = []

        pattern = self._get_pattern(
            "import"
        )

        if pattern is None:

            self.add_error(
                "import解析用Patternがありません。",
                error_type=(
                    "knowledge_pattern_missing"
                ),
                severity="warning",
            )

            return results

        for match in pattern.finditer(code):

            try:
                static_group = (
                    match.group(1)
                )

                path_group = (
                    match.group(2)
                )

            except IndexError:
                continue

            if not path_group:
                continue

            results.append({
                "name": path_group,
                "path": path_group,

                "static":
                    bool(static_group),

                "wildcard":
                    path_group.endswith(".*"),

                "line":
                    self._line_number(
                        code,
                        match.start()
                    ),
            })

        return results

    # ========================================================
    # Type
    # class / interface / enum / record
    # ========================================================

    def _parse_types(
        self,
        code: str
    ) -> List[Dict[str, Any]]:

        results: List[Dict[str, Any]] = []

        #
        # この解析アルゴリズム自体はParser側に置く。
        #
        # modifier等の「何がmodifierか」は
        # Knowledgeから取得する。
        #

        type_pattern = re.compile(
            r"""
            (?P<header>
                (?:
                    @[\w$.]+
                    (?:\([^)]*\))?
                    \s*
                )*
                (?:
                    [A-Za-z_-]+
                    \s+
                )*
            )

            (?P<kind>
                class
                |
                interface
                |
                enum
                |
                record
            )

            \s+

            (?P<name>
                [A-Za-z_$]
                [\w$]*
            )

            (?P<generic>
                \s*
                <
                [^>{}]*
                >
            )?

            (?P<tail>
                [^{]*
            )

            \{
            """,
            flags=re.VERBOSE,
        )

        for match in type_pattern.finditer(
            code
        ):

            header = (
                match.group("header")
                or ""
            )

            kind = match.group("kind")
            name = match.group("name")

            generic = (
                match.group("generic")
                or ""
            ).strip()

            tail = (
                match.group("tail")
                or ""
            )

            modifiers = (
                self._extract_modifiers(
                    header
                )
            )

            annotations = (
                self._extract_annotations(
                    header
                )
            )

            access = (
                self._extract_access(
                    modifiers
                )
            )

            extends = (
                self._extract_extends(
                    tail
                )
            )

            implements = (
                self._extract_implements(
                    tail
                )
            )

            class_data = (
                self.create_class(
                    name=name,
                    access=access,
                    line=self._line_number(
                        code,
                        match.start()
                    ),
                    extends=extends,
                    implements=implements,
                    modifiers=modifiers,
                )
            )

            class_data.update({
                "kind":
                    kind,

                "generic":
                    generic or None,

                "annotations":
                    annotations,

                "semantic":
                    self._semantic(
                        "construct_meanings",
                        kind
                    ),
            })

            results.append(
                class_data
            )

        return results

    # ========================================================
    # Extends
    # ========================================================

    def _extract_extends(
        self,
        tail: str
    ) -> Optional[str]:

        match = re.search(
            r"""
            \bextends
            \s+
            (
                [A-Za-z_$]
                [\w$<>, ?.\[\]]*
            )
            (?=
                \s+implements
                |
                \s*$
            )
            """,
            tail,
            flags=re.VERBOSE,
        )

        if not match:
            return None

        return (
            match.group(1)
            .strip()
        )

    # ========================================================
    # Implements
    # ========================================================

    def _extract_implements(
        self,
        tail: str
    ) -> List[str]:

        match = re.search(
            r"\bimplements\s+(.+)$",
            tail
        )

        if not match:
            return []

        return [
            item.strip()

            for item in
            self._split_generic_safe(
                match.group(1),
                ","
            )

            if item.strip()
        ]

    # ========================================================
    # Field
    # ========================================================

    def _parse_fields(
        self,
        code: str,
        classes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        if not classes:
            return []

        fields: List[
            Dict[str, Any]
        ] = []

        lines = code.splitlines()

        brace_depth = 0

        for line_number, line in enumerate(
            lines,
            start=1
        ):

            stripped = line.strip()

            depth_before = (
                brace_depth
            )

            # --------------------------------------------
            # class body直下のみ対象
            # --------------------------------------------

            if (
                depth_before >= 1
                and stripped
                and not stripped.startswith(
                    (
                        "package ",
                        "import ",
                        "@"
                    )
                )
            ):

                if (
                    "(" not in stripped
                    and stripped.endswith(";")
                ):

                    parsed = (
                        self._parse_variable_declaration(
                            stripped,
                            line=line_number,
                            scope="class",
                        )
                    )

                    fields.extend(
                        parsed
                    )

            brace_depth += (
                self._count_real_char(
                    line,
                    "{"
                )
            )

            brace_depth -= (
                self._count_real_char(
                    line,
                    "}"
                )
            )

            brace_depth = max(
                0,
                brace_depth
            )

        return self._unique_dicts(
            fields,
            keys=("name", "line")
        )

    # ========================================================
    # Variable Declaration
    # ========================================================

    def _parse_variable_declaration(
        self,
        declaration: str,
        *,
        line: int,
        scope: str
    ) -> List[Dict[str, Any]]:

        declaration = (
            declaration
            .strip()
            .rstrip(";")
        )

        # annotation除去
        annotations = (
            self._extract_annotations(
                declaration
            )
        )

        declaration_without_annotations = (
            re.sub(
                r"@[\w$.]+"
                r"(?:\([^)]*\))?"
                r"\s*",
                "",
                declaration
            )
        )

        tokens = (
            declaration_without_annotations
            .split()
        )

        if len(tokens) < 2:
            return []

        # --------------------------------------------
        # modifier
        # --------------------------------------------

        modifiers = []

        while (
            tokens
            and tokens[0]
            in self.modifiers
        ):
            modifiers.append(
                tokens.pop(0)
            )

        if len(tokens) < 2:
            return []

        # --------------------------------------------
        # type
        # --------------------------------------------

        joined = " ".join(tokens)

        split_index = (
            self._find_type_variable_boundary(
                joined
            )
        )

        if split_index is None:
            return []

        var_type = (
            joined[:split_index]
            .strip()
        )

        variables_text = (
            joined[split_index:]
            .strip()
        )

        if not var_type:
            return []

        if not variables_text:
            return []

        # --------------------------------------------
        # Javaの予約語を型と誤認しない
        # --------------------------------------------

        if (
            var_type
            in self.control_keywords
        ):
            return []

        access = (
            self._extract_access(
                modifiers
            )
        )

        results = []

        variable_parts = (
            self._split_generic_safe(
                variables_text,
                ","
            )
        )

        for raw_variable in (
            variable_parts
        ):

            raw_variable = (
                raw_variable.strip()
            )

            if not raw_variable:
                continue

            name, value = (
                self._split_assignment(
                    raw_variable
                )
            )

            if not name:
                continue

            # array suffix
            actual_type = var_type

            while name.endswith("[]"):
                actual_type += "[]"
                name = name[:-2]

            if not self._is_identifier(
                name
            ):
                continue

            variable = (
                self.create_variable(
                    name=name,
                    var_type=actual_type,
                    value=value,
                    scope=scope,
                    access=access,
                    line=line,
                    modifiers=modifiers,
                )
            )

            variable.update({
                "annotations":
                    annotations,

                "type_info":
                    self._analyze_type(
                        actual_type
                    ),

                "semantic":
                    self._semantic_for_type(
                        actual_type
                    ),
            })

            results.append(
                variable
            )

        return results

    # ========================================================
    # Method / Constructor
    # ========================================================

    def _parse_methods(
        self,
        code: str,
        classes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        results: List[
            Dict[str, Any]
        ] = []

        class_names = {
            item["name"]
            for item in classes
            if item.get("name")
        }

        #
        # method signature候補。
        #
        # Java文法すべてをRegexに背負わせず、
        # 候補抽出後にPython側で判定する。
        #

        candidate_pattern = re.compile(
            r"""
            (?P<header>
                (?:
                    @[\w$.]+
                    (?:\([^)]*\))?
                    \s*
                )*
                [^{};()]*
            )

            (?P<name>
                [A-Za-z_$]
                [\w$]*
            )

            \s*

            \(
                (?P<parameters>
                    [^()]*
                )
            \)

            \s*

            (?:
                throws
                \s+
                (?P<throws>
                    [^{;]+
                )
            )?

            \s*

            (?P<ending>
                \{
                |
                ;
            )
            """,
            flags=(
                re.VERBOSE
                | re.MULTILINE
            ),
        )

        for match in (
            candidate_pattern.finditer(
                code
            )
        ):

            name = (
                match.group("name")
            )

            if (
                name
                in self.control_keywords
            ):
                continue

            header = (
                match.group("header")
                or ""
            ).strip()

            if self._looks_like_expression(
                header
            ):
                continue

            annotations = (
                self._extract_annotations(
                    header
                )
            )

            clean_header = (
                self._remove_annotations(
                    header
                )
            )

            modifiers = (
                self._extract_modifiers(
                    clean_header
                )
            )

            access = (
                self._extract_access(
                    modifiers
                )
            )

            # --------------------------------------------
            # header token解析
            # --------------------------------------------

            header_without_modifiers = (
                self._remove_known_modifiers(
                    clean_header
                )
            )

            header_without_modifiers = (
                header_without_modifiers
                .strip()
            )

            generic = None

            if (
                header_without_modifiers
                .startswith("<")
            ):

                generic, (
                    header_without_modifiers
                ) = (
                    self._consume_leading_generic(
                        header_without_modifiers
                    )
                )

            return_type = (
                header_without_modifiers
                .strip()
            )

            is_constructor = (
                name in class_names
                and not return_type
            )

            if (
                not is_constructor
                and not return_type
            ):
                continue

            # --------------------------------------------
            # parameters
            # --------------------------------------------

            parameters = (
                self._parse_parameters(
                    match.group(
                        "parameters"
                    )
                )
            )

            # --------------------------------------------
            # throws
            # --------------------------------------------

            throws_raw = (
                match.group("throws")
                or ""
            )

            throws = [
                item.strip()

                for item in
                self._split_generic_safe(
                    throws_raw,
                    ","
                )

                if item.strip()
            ]

            # --------------------------------------------
            # body
            # --------------------------------------------

            body = ""

            if (
                match.group("ending")
                == "{"
            ):

                brace_index = (
                    match.end() - 1
                )

                body, _ = (
                    self._extract_brace_body(
                        code,
                        brace_index
                    )
                )

            # --------------------------------------------
            # local variables
            # --------------------------------------------

            local_variables = (
                self._parse_local_variables(
                    body,
                    base_line=(
                        self._line_number(
                            code,
                            match.start()
                        )
                    )
                )
            )

            # --------------------------------------------
            # read / write
            # --------------------------------------------

            reads, writes = (
                self._analyze_variable_usage(
                    body,
                    parameters,
                    local_variables
                )
            )

            # --------------------------------------------
            # method calls
            # --------------------------------------------

            calls = (
                self._extract_method_calls(
                    body
                )
            )

            # --------------------------------------------
            # returns
            # --------------------------------------------

            returns = (
                self._extract_returns(
                    body
                )
            )

            method = (
                self.create_method(
                    name=name,

                    return_type=(
                        None
                        if is_constructor
                        else return_type
                    ),

                    parameters=
                        parameters,

                    access=access,

                    line=self._line_number(
                        code,
                        match.start()
                    ),

                    modifiers=
                        modifiers,

                    reads=
                        sorted(reads),

                    writes=
                        sorted(writes),

                    calls=
                        sorted(calls),
                )
            )

            method.update({
                "constructor":
                    is_constructor,

                "annotations":
                    annotations,

                "throws":
                    throws,

                "generic":
                    generic,

                "returns":
                    returns,

                "local_variables":
                    local_variables,

                "semantic":
                    self._semantic(
                        "construct_meanings",
                        (
                            "constructor"
                            if is_constructor
                            else "method"
                        )
                    ),
            })

            if return_type:
                method["return_type_info"] = (
                    self._analyze_type(
                        return_type
                    )
                )

            results.append(
                method
            )

        return self._unique_dicts(
            results,
            keys=(
                "name",
                "line"
            )
        )

    # ========================================================
    # Parameter
    # ========================================================

    def _parse_parameters(
        self,
        raw: str
    ) -> List[Dict[str, Any]]:

        if not raw.strip():
            return []

        results = []

        for part in (
            self._split_generic_safe(
                raw,
                ","
            )
        ):

            text = part.strip()

            if not text:
                continue

            annotations = (
                self._extract_annotations(
                    text
                )
            )

            text = (
                self._remove_annotations(
                    text
                )
            )

            # final除去
            tokens = text.split()

            modifiers = []

            while (
                tokens
                and tokens[0]
                in self.modifiers
            ):

                modifiers.append(
                    tokens.pop(0)
                )

            if len(tokens) < 2:
                continue

            name = tokens[-1]

            param_type = (
                " ".join(
                    tokens[:-1]
                )
            )

            # varargs
            varargs = (
                "..."
                in param_type
            )

            if not self._is_identifier(
                name
            ):
                continue

            parameter = (
                self.create_parameter(
                    name=name,
                    param_type=param_type,
                )
            )

            parameter.update({
                "annotations":
                    annotations,

                "modifiers":
                    modifiers,

                "varargs":
                    varargs,

                "type_info":
                    self._analyze_type(
                        param_type
                    ),
            })

            results.append(
                parameter
            )

        return results

    # ========================================================
    # Local Variable
    # ========================================================

    def _parse_local_variables(
        self,
        body: str,
        *,
        base_line: int
    ) -> List[Dict[str, Any]]:

        if not body:
            return []

        results = []

        for offset, line in enumerate(
            body.splitlines()
        ):

            stripped = line.strip()

            if not stripped:
                continue

            if not stripped.endswith(";"):
                continue

            if stripped.startswith(
                (
                    "return ",
                    "throw ",
                    "break",
                    "continue",
                    "import ",
                    "package "
                )
            ):
                continue

            if (
                "(" in stripped
                and "=" not in stripped
            ):
                continue

            variables = (
                self._parse_variable_declaration(
                    stripped,
                    line=(
                        base_line
                        + offset
                    ),
                    scope="local",
                )
            )

            results.extend(
                variables
            )

        return self._unique_dicts(
            results,
            keys=(
                "name",
                "line"
            )
        )

    # ========================================================
    # Return
    # ========================================================

    def _extract_returns(
        self,
        body: str
    ) -> List[str]:

        if not body:
            return []

        pattern = (
            self._get_pattern(
                "return_statement"
            )
        )

        # Knowledgeに定義がなければ、
        # return構造の解析アルゴリズムとして
        # 最低限の処理だけ行う。
        if pattern is None:
            pattern = re.compile(
                r"\breturn\s+([^;]+);"
            )

        results = []

        for match in pattern.finditer(
            body
        ):

            try:
                value = (
                    match.group(1)
                    .strip()
                )

            except IndexError:
                continue

            results.append(
                value
            )

        return results

    # ========================================================
    # Method Calls
    # ========================================================

    def _extract_method_calls(
        self,
        body: str
    ) -> Set[str]:

        results: Set[str] = set()

        if not body:
            return results

        pattern = re.compile(
            r"""
            (?P<call>
                (?:
                    [A-Za-z_$]
                    [\w$]*
                    \s*\.\s*
                )*

                [A-Za-z_$]
                [\w$]*
            )

            \s*
            \(
            """,
            flags=re.VERBOSE,
        )

        for match in (
            pattern.finditer(body)
        ):

            call = (
                match.group("call")
                .replace(" ", "")
            )

            final_name = (
                call.split(".")[-1]
            )

            if (
                final_name
                in self.control_keywords
            ):
                continue

            results.add(
                call
            )

        return results

    # ========================================================
    # Read / Write
    # ========================================================

    def _analyze_variable_usage(
        self,
        body: str,
        parameters: List[Dict[str, Any]],
        local_variables: List[Dict[str, Any]]
    ) -> Tuple[Set[str], Set[str]]:

        reads: Set[str] = set()
        writes: Set[str] = set()

        if not body:
            return reads, writes

        known_names = set(
            self.known_fields
        )

        known_names.update(
            item["name"]
            for item in parameters
            if item.get("name")
        )

        known_names.update(
            item["name"]
            for item in local_variables
            if item.get("name")
        )

        # --------------------------------------------
        # this.hp → hp として扱えるように
        # --------------------------------------------

        normalized_body = re.sub(
            r"\bthis\.",
            "",
            body
        )

        # --------------------------------------------
        # assignment
        # --------------------------------------------

        assignment_pattern = (
            re.compile(
                r"""
                \b
                (?P<name>
                    [A-Za-z_$]
                    [\w$]*
                )

                \s*

                (?P<operator>
                    \+=
                    |-=
                    |\*=
                    |/=
                    |%=
                    |&=
                    |\|=
                    |\^=
                    |>>=
                    |<<=
                    |\+\+
                    |--
                    |=(?!=)
                )
                """,
                flags=re.VERBOSE,
            )
        )

        for match in (
            assignment_pattern.finditer(
                normalized_body
            )
        ):

            name = (
                match.group("name")
            )

            operator = (
                match.group("operator")
            )

            if (
                known_names
                and name not in known_names
            ):
                continue

            writes.add(
                name
            )

            if operator != "=":
                reads.add(
                    name
                )

        # --------------------------------------------
        # references
        # --------------------------------------------

        for name in known_names:

            if re.search(
                rf"\b{re.escape(name)}\b",
                normalized_body
            ):
                reads.add(
                    name
                )

        return reads, writes

    # ========================================================
    # Dependency
    # ========================================================

    def _build_dependencies(
        self,
        *,
        imports: List[Dict[str, Any]],
        classes: List[Dict[str, Any]],
        fields: List[Dict[str, Any]],
        methods: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        dependencies: List[
            Dict[str, Any]
        ] = []

        seen: Set[
            Tuple[str, str, str]
        ] = set()

        # --------------------------------------------
        # imports
        # --------------------------------------------

        for item in imports:

            target = (
                item.get("path")
                or item.get("name")
            )

            if not target:
                continue

            self._append_dependency(
                dependencies,
                seen,
                dependency_type="import",
                target=target,
            )

        # --------------------------------------------
        # inheritance
        # --------------------------------------------

        for item in classes:

            source = item.get(
                "name"
            )

            extends = item.get(
                "extends"
            )

            if extends:

                self._append_dependency(
                    dependencies,
                    seen,
                    dependency_type="extends",
                    source=source,
                    target=extends,
                )

            for interface in (
                item.get(
                    "implements",
                    []
                )
            ):

                self._append_dependency(
                    dependencies,
                    seen,
                    dependency_type=(
                        "implements"
                    ),
                    source=source,
                    target=interface,
                )

        # --------------------------------------------
        # field type dependencies
        # --------------------------------------------

        for field in fields:

            field_type = field.get(
                "type"
            )

            for target in (
                self._extract_type_names(
                    field_type
                )
            ):

                if not self._is_dependency_type(
                    target
                ):
                    continue

                self._append_dependency(
                    dependencies,
                    seen,
                    dependency_type=(
                        "field_type"
                    ),
                    source=field.get(
                        "name"
                    ),
                    target=target,
                )

        # --------------------------------------------
        # method dependencies
        # --------------------------------------------

        for method in methods:

            method_name = (
                method.get("name")
            )

            return_type = (
                method.get(
                    "return_type"
                )
            )

            for target in (
                self._extract_type_names(
                    return_type
                )
            ):

                if self._is_dependency_type(
                    target
                ):

                    self._append_dependency(
                        dependencies,
                        seen,
                        dependency_type=(
                            "return_type"
                        ),
                        source=method_name,
                        target=target,
                    )

            for parameter in (
                method.get(
                    "parameters",
                    []
                )
            ):

                for target in (
                    self._extract_type_names(
                        parameter.get(
                            "type"
                        )
                    )
                ):

                    if (
                        self._is_dependency_type(
                            target
                        )
                    ):

                        self._append_dependency(
                            dependencies,
                            seen,
                            dependency_type=(
                                "parameter_type"
                            ),
                            source=method_name,
                            target=target,
                        )

        return dependencies

    def _append_dependency(
        self,
        output: List[Dict[str, Any]],
        seen: Set[Tuple[str, str, str]],
        *,
        dependency_type: str,
        target: str,
        source: Optional[str] = None
    ) -> None:

        key = (
            dependency_type,
            source or "",
            target,
        )

        if key in seen:
            return

        seen.add(key)

        item = {
            "type":
                dependency_type,

            "target":
                target,
        }

        if source:
            item["source"] = source

        output.append(
            item
        )

    # ========================================================
    # Java Type解析
    # ========================================================

    def _analyze_type(
        self,
        type_name: Optional[str]
    ) -> Dict[str, Any]:

        if not type_name:

            return {
                "raw": None,
                "base_type": None,
                "generic_types": [],
                "array": False,
                "varargs": False,
                "primitive": False,
                "category": None,
            }

        raw = type_name.strip()

        varargs = (
            "..."
            in raw
        )

        normalized = (
            raw.replace(
                "...",
                ""
            ).strip()
        )

        array = (
            "[]"
            in normalized
        )

        normalized = (
            normalized
            .replace("[]", "")
            .strip()
        )

        generic_types = []

        base_type = normalized

        generic_match = re.match(
            r"""
            ^
            (?P<base>
                [A-Za-z_$]
                [\w$.]*
            )

            \s*

            <
                (?P<generic>
                    .+
                )
            >
            $
            """,
            normalized,
            flags=re.VERBOSE,
        )

        if generic_match:

            base_type = (
                generic_match
                .group("base")
            )

            generic_raw = (
                generic_match
                .group("generic")
            )

            generic_types = [
                item.strip()

                for item in
                self._split_generic_safe(
                    generic_raw,
                    ","
                )

                if item.strip()
            ]

        short_base_type = (
            base_type.split(".")[-1]
        )

        primitive = (
            short_base_type
            in self.primitive_types
        )

        category = (
            self._find_type_category(
                short_base_type
            )
        )

        return {
            "raw":
                raw,

            "base_type":
                base_type,

            "generic_types":
                generic_types,

            "array":
                array,

            "varargs":
                varargs,

            "primitive":
                primitive,

            "known_common_type":
                (
                    short_base_type
                    in self.common_types
                ),

            "category":
                category,
        }

    def _find_type_category(
        self,
        type_name: str
    ) -> Optional[str]:

        for category, values in (
            self.type_categories.items()
        ):

            if type_name in values:
                return category

        return None

    # ========================================================
    # Type Names
    # ========================================================

    def _extract_type_names(
        self,
        type_name: Optional[str]
    ) -> Set[str]:

        if not type_name:
            return set()

        ignored = {
            "?",
            "extends",
            "super",
        }

        names = set(
            re.findall(
                r"\b[A-Za-z_$][\w$]*\b",
                type_name
            )
        )

        return {
            name
            for name in names
            if name not in ignored
        }

    def _is_dependency_type(
        self,
        type_name: str
    ) -> bool:

        if (
            type_name
            in self.primitive_types
        ):
            return False

        if (
            type_name
            in self.java_keywords
        ):
            return False

        return True

    # ========================================================
    # Annotation
    # ========================================================

    def _extract_annotations(
        self,
        text: str
    ) -> List[str]:

        return [
            match.group(1)

            for match in re.finditer(
                r"""
                @
                (
                    [A-Za-z_$]
                    [\w$.]*
                )

                (?:
                    \(
                        [^)]*
                    \)
                )?
                """,
                text,
                flags=re.VERBOSE,
            )
        ]

    def _remove_annotations(
        self,
        text: str
    ) -> str:

        return re.sub(
            r"""
            @
            [A-Za-z_$]
            [\w$.]*

            (?:
                \(
                    [^)]*
                \)
            )?

            \s*
            """,
            "",
            text,
            flags=re.VERBOSE,
        )

    # ========================================================
    # Modifier
    # ========================================================

    def _extract_modifiers(
        self,
        text: str
    ) -> List[str]:

        if not text:
            return []

        tokens = (
            re.findall(
                r"[A-Za-z_-]+",
                text
            )
        )

        return list(
            dict.fromkeys(
                token
                for token in tokens
                if token in self.modifiers
            )
        )

    def _remove_known_modifiers(
        self,
        text: str
    ) -> str:

        tokens = text.split()

        while (
            tokens
            and tokens[0]
            in self.modifiers
        ):
            tokens.pop(0)

        return " ".join(tokens)

    def _extract_access(
        self,
        modifiers: Iterable[str]
    ) -> str:

        for modifier in modifiers:

            if (
                modifier
                in self.access_modifiers
            ):
                return modifier

        return (
            self.knowledge.modifiers.get(
                "default_access",
                "package-private"
            )
        )

    # ========================================================
    # Semantic
    # ========================================================

    def _semantic(
        self,
        category: str,
        key: str
    ) -> str:

        try:

            return (
                self.knowledge_loader
                .get_semantic_meaning(
                    category,
                    key
                )
            )

        except Exception:
            return ""

    def _semantic_for_type(
        self,
        type_name: str
    ) -> str:

        info = (
            self._analyze_type(
                type_name
            )
        )

        base_type = (
            info.get(
                "base_type"
            )
        )

        if not base_type:
            return ""

        short_name = (
            base_type.split(".")[-1]
        )

        return self._semantic(
            "type_meanings",
            short_name
        )

    # ========================================================
    # Knowledge Pattern
    # ========================================================

    def _get_pattern(
        self,
        name: str
    ) -> Optional[re.Pattern]:

        try:
            return (
                self.knowledge_loader
                .get_pattern(name)
            )

        except Exception:
            return (
                self.knowledge
                .compiled_patterns
                .get(name)
            )

    # ========================================================
    # Comment Removal
    # ========================================================

    def _remove_comments_preserve_lines(
        self,
        code: str
    ) -> str:
        """
        Javaコメントを空白へ置換する。

        改行は残すため、
        元ソースコードの行番号を維持しやすい。

        String内の
        "//"
        "/*"
        はコメントとして扱わない。
        """

        chars = list(code)

        length = len(code)

        index = 0

        in_string = False
        in_char = False
        escaped = False

        while index < length:

            char = code[index]

            # --------------------------------------------
            # String
            # --------------------------------------------

            if in_string:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == '"':
                    in_string = False

                index += 1
                continue

            # --------------------------------------------
            # char literal
            # --------------------------------------------

            if in_char:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == "'":
                    in_char = False

                index += 1
                continue

            if char == '"':
                in_string = True
                index += 1
                continue

            if char == "'":
                in_char = True
                index += 1
                continue

            # --------------------------------------------
            # //
            # --------------------------------------------

            if (
                char == "/"
                and index + 1 < length
                and code[index + 1] == "/"
            ):

                end = (
                    code.find(
                        "\n",
                        index
                    )
                )

                if end == -1:
                    end = length

                for position in range(
                    index,
                    end
                ):
                    chars[position] = " "

                index = end
                continue

            # --------------------------------------------
            # /* */
            # --------------------------------------------

            if (
                char == "/"
                and index + 1 < length
                and code[index + 1] == "*"
            ):

                end = (
                    code.find(
                        "*/",
                        index + 2
                    )
                )

                if end == -1:

                    self.add_error(
                        "閉じられていないブロックコメントを検出しました。",
                        error_type=(
                            "unclosed_comment"
                        ),
                        line=self._line_number(
                            code,
                            index
                        ),
                        severity="warning",
                    )

                    end = length - 2

                for position in range(
                    index,
                    min(
                        end + 2,
                        length
                    )
                ):

                    if (
                        chars[position]
                        != "\n"
                    ):
                        chars[position] = " "

                index = end + 2
                continue

            index += 1

        return "".join(chars)

    # ========================================================
    # Brace Body
    # ========================================================

    def _extract_brace_body(
        self,
        code: str,
        open_brace_index: int
    ) -> Tuple[str, Optional[int]]:

        depth = 0

        in_string = False
        in_char = False
        escaped = False

        for index in range(
            open_brace_index,
            len(code)
        ):

            char = code[index]

            # --------------------------------------------
            # String
            # --------------------------------------------

            if in_string:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == '"':
                    in_string = False

                continue

            # --------------------------------------------
            # char
            # --------------------------------------------

            if in_char:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == "'":
                    in_char = False

                continue

            if char == '"':
                in_string = True
                continue

            if char == "'":
                in_char = True
                continue

            # --------------------------------------------
            # braces
            # --------------------------------------------

            if char == "{":
                depth += 1

            elif char == "}":

                depth -= 1

                if depth == 0:

                    return (
                        code[
                            open_brace_index
                            + 1:
                            index
                        ],

                        index
                    )

        self.add_error(
            "閉じられていない { } ブロックを検出しました。",
            error_type="unclosed_brace",
            line=self._line_number(
                code,
                open_brace_index
            ),
            severity="warning",
        )

        return (
            code[
                open_brace_index + 1:
            ],
            None
        )

    # ========================================================
    # Generic-safe Split
    # ========================================================

    def _split_generic_safe(
        self,
        text: str,
        separator: str
    ) -> List[str]:
        """
        例:

        Map<String, List<User>>,
        int count

        のような場合、

        <>内部のカンマを区切りと誤認しない。
        """

        results = []

        current = []

        angle_depth = 0
        paren_depth = 0
        bracket_depth = 0
        brace_depth = 0

        in_string = False
        in_char = False

        escaped = False

        for char in text:

            if in_string:

                current.append(char)

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == '"':
                    in_string = False

                continue

            if in_char:

                current.append(char)

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == "'":
                    in_char = False

                continue

            if char == '"':
                in_string = True
                current.append(char)
                continue

            if char == "'":
                in_char = True
                current.append(char)
                continue

            if char == "<":
                angle_depth += 1

            elif char == ">":
                angle_depth = max(
                    0,
                    angle_depth - 1
                )

            elif char == "(":
                paren_depth += 1

            elif char == ")":
                paren_depth = max(
                    0,
                    paren_depth - 1
                )

            elif char == "[":
                bracket_depth += 1

            elif char == "]":
                bracket_depth = max(
                    0,
                    bracket_depth - 1
                )

            elif char == "{":
                brace_depth += 1

            elif char == "}":
                brace_depth = max(
                    0,
                    brace_depth - 1
                )

            if (
                char == separator
                and angle_depth == 0
                and paren_depth == 0
                and bracket_depth == 0
                and brace_depth == 0
            ):

                results.append(
                    "".join(current)
                )

                current = []

                continue

            current.append(char)

        if current:

            results.append(
                "".join(current)
            )

        return results

    # ========================================================
    # Assignment Split
    # ========================================================

    def _split_assignment(
        self,
        text: str
    ) -> Tuple[str, Optional[str]]:

        angle = 0
        paren = 0
        bracket = 0
        brace = 0

        in_string = False
        in_char = False

        escaped = False

        for index, char in enumerate(
            text
        ):

            if in_string:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == '"':
                    in_string = False

                continue

            if in_char:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == "'":
                    in_char = False

                continue

            if char == '"':
                in_string = True
                continue

            if char == "'":
                in_char = True
                continue

            if char == "<":
                angle += 1

            elif char == ">":
                angle = max(
                    0,
                    angle - 1
                )

            elif char == "(":
                paren += 1

            elif char == ")":
                paren = max(
                    0,
                    paren - 1
                )

            elif char == "[":
                bracket += 1

            elif char == "]":
                bracket = max(
                    0,
                    bracket - 1
                )

            elif char == "{":
                brace += 1

            elif char == "}":
                brace = max(
                    0,
                    brace - 1
                )

            elif (
                char == "="
                and angle == 0
                and paren == 0
                and bracket == 0
                and brace == 0
            ):

                previous = (
                    text[index - 1]
                    if index > 0
                    else ""
                )

                following = (
                    text[index + 1]
                    if index + 1
                    < len(text)
                    else ""
                )

                # ==
                # >=
                # <=
                # !=
                # =>
                if (
                    previous
                    in "=!<>"
                    or following == "="
                    or following == ">"
                ):
                    continue

                return (
                    text[:index]
                    .strip(),

                    text[
                        index + 1:
                    ].strip()
                )

        return (
            text.strip(),
            None
        )

    # ========================================================
    # Type / Variable Boundary
    # ========================================================

    def _find_type_variable_boundary(
        self,
        text: str
    ) -> Optional[int]:
        """
        List<Map<String, User>> users

        から、

        List<Map<String, User>>
        と
        users

        の境界を探す。
        """

        angle_depth = 0
        bracket_depth = 0

        last_space = None

        for index, char in enumerate(
            text
        ):

            if char == "<":
                angle_depth += 1

            elif char == ">":
                angle_depth = max(
                    0,
                    angle_depth - 1
                )

            elif char == "[":
                bracket_depth += 1

            elif char == "]":
                bracket_depth = max(
                    0,
                    bracket_depth - 1
                )

            elif (
                char.isspace()
                and angle_depth == 0
                and bracket_depth == 0
            ):
                last_space = index

                remainder = (
                    text[
                        index + 1:
                    ].strip()
                )

                if remainder:

                    candidate = (
                        remainder
                        .split(
                            "=",
                            1
                        )[0]
                        .split(
                            ",",
                            1
                        )[0]
                        .strip()
                    )

                    candidate = (
                        candidate
                        .replace(
                            "[]",
                            ""
                        )
                    )

                    if self._is_identifier(
                        candidate
                    ):
                        return index

        return last_space

    # ========================================================
    # Leading Generic
    # ========================================================

    def _consume_leading_generic(
        self,
        text: str
    ) -> Tuple[
        Optional[str],
        str
    ]:

        if not text.startswith("<"):
            return None, text

        depth = 0

        for index, char in enumerate(
            text
        ):

            if char == "<":
                depth += 1

            elif char == ">":

                depth -= 1

                if depth == 0:

                    return (
                        text[
                            :index + 1
                        ].strip(),

                        text[
                            index + 1:
                        ].strip()
                    )

        return None, text

    # ========================================================
    # Helpers
    # ========================================================

    def _line_number(
        self,
        code: str,
        index: int
    ) -> int:

        return (
            code.count(
                "\n",
                0,
                index
            )
            + 1
        )

    def _is_identifier(
        self,
        value: str
    ) -> bool:

        if not value:
            return False

        pattern = (
            self._get_pattern(
                "identifier"
            )
        )

        if pattern is not None:

            return bool(
                pattern.fullmatch(
                    value
                )
            )

        return bool(
            re.fullmatch(
                r"[A-Za-z_$][\w$]*",
                value
            )
        )

    def _looks_like_expression(
        self,
        header: str
    ) -> bool:

        stripped = (
            header.strip()
        )

        if not stripped:
            return False

        suspicious = (
            "=",
            "return ",
            "throw ",
            "new ",
            ".",
        )

        return any(
            marker in stripped
            for marker in suspicious
        )

    def _count_real_char(
        self,
        text: str,
        target: str
    ) -> int:

        count = 0

        in_string = False
        in_char = False
        escaped = False

        for char in text:

            if in_string:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == '"':
                    in_string = False

                continue

            if in_char:

                if escaped:
                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == "'":
                    in_char = False

                continue

            if char == '"':
                in_string = True
                continue

            if char == "'":
                in_char = True
                continue

            if char == target:
                count += 1

        return count

    def _unique_dicts(
        self,
        items: List[Dict[str, Any]],
        *,
        keys: Tuple[str, ...]
    ) -> List[Dict[str, Any]]:

        seen = set()

        result = []

        for item in items:

            identity = tuple(
                item.get(key)
                for key in keys
            )

            if identity in seen:
                continue

            seen.add(identity)

            result.append(item)

        return result


# ============================================================
# テスト
# ============================================================

if __name__ == "__main__":

    SAMPLE_CODE = r'''
package com.example.game;

import java.util.List;
import java.util.ArrayList;
import java.util.Optional;

public class Player {

    private String name;
    private int hp = 100;

    private List<String> items =
        new ArrayList<>();

    public Player(String name) {
        this.name = name;
    }

    public void damage(int amount) {

        int oldHp = hp;

        hp -= amount;

        System.out.println(
            "HP: " + hp
        );
    }

    public boolean isDead() {
        return hp <= 0;
    }

    public Optional<String> findItem(
        String itemName
    ) {
        return items.stream()
            .filter(item ->
                item.equals(itemName)
            )
            .findFirst();
    }
}
'''

    # --------------------------------------------------------
    # TODO:
    # 実際の絶対パスへ変更してください
    # --------------------------------------------------------

    KNOWLEDGE_DIR = (
        "./knowledge/parsers/java"
    )

    parser = JavaParser(
        knowledge_dir=KNOWLEDGE_DIR
    )

    result = parser.parse(
        SAMPLE_CODE
    )

    import json

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )