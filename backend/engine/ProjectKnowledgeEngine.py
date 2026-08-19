# To(と)/backend/engine/ProjectKnowledgeEngine.py
"""
ProjectKnowledgeEngine v2
=
変更点（v1 からの差分）:

  1. can_handle フォールバック検出を追加
     -> calculate_score が無いハンドラーは can_handle(msg) -> bool を
        持つ場合があり、実際の orchestrator.py はこれを 0/100点に変換している。

  2. 100点満点ショートカットの検出
     -> top["score"] == 100 の場合、2位との競合チェックを飛ばして即実行する
        ルールが実装に存在するのに、旧エンジンの routing_flow には無かった。

  3. plugins/ 配下からインポートされるハンドラーへの対応
     -> from plugins.project_builder.DeploymentHandler import DeploymentHandler
        のような「ハンドラーディレクトリ外」からの import を dependency_graph
        に正しく記録する。

  4. TypeScript (.ts) ハンドラーの検出（正規表現ベース）
     -> Python の ast が使えないため、クラス定義とメソッド定義を正規表現で
        検出する。将来 ts-morph 等に差し替え可能なように関数を分離している。

  5. JSON 倉庫のマニフェスト化 (scan_json_warehouse)
     -> knowledge.json 以外に増え続ける JSON 群を "何がどこにあり、
        トップレベルのキーは何か" だけでも自動棚卸しする。

  6. memory_system の記述修正
     -> signals の書き込みタイミングが orchestrator ではなく routes_chat.py
        側に移管されている実態を反映。
"""

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# データ構造
# ---------------------------------------------------------------------------

@dataclass
class HandlerInfo:
    class_name: str
    file_path: str
    language: str = "python"          # "python" | "typescript"
    has_calculate_score: bool = False
    has_can_handle: bool = False      # v2: フォールバック判定用
    has_handle: bool = False
    has_estimate_size: bool = False
    has_signals_param: bool = False


# ---------------------------------------------------------------------------
# Step 1: フォルダスキャン（.ts を追加）
# ---------------------------------------------------------------------------

def scan_folder(project_root: str) -> dict[str, list[str]]:
    root = Path(project_root)
    result: dict[str, list[str]] = {}

    for pattern in ("*.py", "*.ts", "*.tsx"):
        for f in sorted(root.rglob(pattern)):
            # node_modules 等は除外
            if "node_modules" in f.parts or ".git" in f.parts:
                continue
            rel = str(f.relative_to(root))
            dir_key = str(f.parent.relative_to(root))
            result.setdefault(dir_key, []).append(rel)

    return result


# ---------------------------------------------------------------------------
# Step 2: 依存関係解析
# ---------------------------------------------------------------------------

def _parse_imports_py(source: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [alias.asname or alias.name for alias in node.names]
            imports.append({"from": node.module, "names": names})
        elif isinstance(node, ast.Import):
            names = [alias.asname or alias.name for alias in node.names]
            imports.append({"from": None, "names": names})
    return imports


def _parse_imports_ts(source: str) -> list[dict]:
    """
    TS の import 文を正規表現で拾う。
    例: import { GithubHandler } from './handlers/github_handler';
        import DesignHandler from './handlers/DesignHandler';
    """
    imports = []
    for m in re.finditer(
        r'import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]', source
    ):
        named, default, module = m.groups()
        if named:
            names = [n.strip().split(" as ")[-1].strip() for n in named.split(",")]
        else:
            names = [default]
        imports.append({"from": module, "names": names})
    return imports


def _inspect_handler_class_py(source: str, class_name: str) -> HandlerInfo:
    info = HandlerInfo(class_name=class_name, file_path="", language="python")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return info

    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == class_name):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = item.name
            args = [a.arg for a in item.args.args]

            if name == "calculate_score":
                info.has_calculate_score = True
                info.has_signals_param = len(args) >= 3  # self, msg, signals
            elif name == "can_handle":
                info.has_can_handle = True
            elif name == "handle":
                info.has_handle = True
            elif name == "estimate_size":
                info.has_estimate_size = True

    return info


def _inspect_handler_class_ts(source: str, class_name: str) -> HandlerInfo:
    """
    TS 用の簡易検査。ast が使えないので、クラス本体をブレースの対応で
    大まかに切り出してからメソッド名を正規表現で探す。
    完全な構文解析ではないため、ネストが深いクラスでは誤検出しうる —
    精度が必要になったら ts-morph 等の外部 AST パーサーに置き換える。
    """
    info = HandlerInfo(class_name=class_name, file_path="", language="typescript")

    class_start = re.search(rf'class\s+{re.escape(class_name)}\b[^{{]*{{', source)
    if not class_start:
        return info

    # 簡易ブレースカウントでクラス本体を切り出す
    start = class_start.end()
    depth = 1
    end = start
    for i, ch in enumerate(source[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    body = source[start:end]

    # if re.search(r'\bcalculateScore\s*\(([^)]*)\)', body):
    if m := re.search(r'\bcalculateScore\s*\(([^)]*)\)', body):
        params = [p for p in m.group(1).split(",") if p.strip()]
        info.has_calculate_score = True
        info.has_signals_param = len(params) >= 2  # msg, signals (this不要)
    if re.search(r'\bcanHandle\s*\(', body):
        info.has_can_handle = True
    if re.search(r'\bhandle\s*\(', body):
        info.has_handle = True
    if re.search(r'\bestimateSize\s*\(', body):
        info.has_estimate_size = True

    return info


def extract_dependencies(project_root: str, file_map: dict[str, list[str]]) -> dict:
    root = Path(project_root)
    handlers: list[dict] = []
    orchestrator_imports: list[dict] = []
    fastpath: dict = {}
    hundred_point_shortcut = False

    for dir_key, files in file_map.items():
        for rel_path in files:
            abs_path = root / rel_path
            source = abs_path.read_text(encoding="utf-8", errors="ignore")
            is_ts = rel_path.endswith((".ts", ".tsx"))

            # --- orchestrator 検出（Python限定。TS版orchestratorが出てきたら要拡張） ---
            if "ChatOrchestrator" in source and "route_and_execute" in source:
                orchestrator_imports = _parse_imports_py(source)

                if m := re.search(r'image_base64.*?\n.*?(\w+Handler)', source, re.DOTALL):
                    fastpath = {"trigger": "image_base64", "handler": m.group(1)}

                # v2: 100点ショートカットの検出
                if re.search(r'top\[.score.\]\s*==\s*100', source):
                    hundred_point_shortcut = True
                continue

            # --- ハンドラークラス検出 ---
            class_matches = re.findall(r'class\s+(\w+Handler)\s*[\(:{]', source)
            for class_name in class_matches:
                if is_ts:
                    info = _inspect_handler_class_ts(source, class_name)
                else:
                    info = _inspect_handler_class_py(source, class_name)
                info.file_path = rel_path
                handlers.append(vars(info))

    # orchestrator の import 順序（plugins.xxx からの import も含める）
    handler_order: list[str] = []
    handler_sources: dict[str, str] = {}  # handler名 -> import元モジュール
    for imp in orchestrator_imports:
        for name in imp["names"]:
            if name.endswith("Handler") and name != "OcrRecruitHandler":
                if name not in handler_order:
                    handler_order.append(name)
                handler_sources[name] = imp["from"] or ""

    return {
        "orchestrator": "ChatOrchestrator",
        "handler_order": handler_order,
        "handler_sources": handler_sources,   # v2: 追加。plugins/ 配下も可視化
        "handlers": handlers,
        "fastpath": fastpath,
        "hundred_point_shortcut": hundred_point_shortcut,  # v2: 追加
    }


# ---------------------------------------------------------------------------
# Step 3: 変数・定数抽出
# ---------------------------------------------------------------------------

_KNOWN_CONSTANTS = {
    r'top\[.score.\]\s*<\s*(\d+)': ("score_min_threshold", "最低スコア。これを下回ると「どれも対応不可」として即リターン"),
    r'\(top\[.score.\]\s*-\s*second\[.score.\]\)\s*<=\s*(\d+)': ("score_conflict_range", "1位と2位のスコア差がこれ以内なら「競合」と判定"),
    r'total_size\s*>=\s*(\d+)': ("merge_size_limit", "競合時、合計文字数がこれ以上なら聞き返す"),
    r'top\[.score.\]\s*==\s*(100)': ("perfect_score_shortcut", "この点数なら競合判定を無視して即時単独実行"),
}


def extract_variables(project_root: str, file_map: dict[str, list[str]]) -> dict:
    root = Path(project_root)
    found: dict[str, dict] = {}

    for files in file_map.values():
        for rel_path in files:
            source = (root / rel_path).read_text(encoding="utf-8", errors="ignore")
            for pattern, (key, description) in _KNOWN_CONSTANTS.items():
                m = re.search(pattern, source)
                if m:
                    try:
                        value = int(m.group(1))
                    except (IndexError, ValueError):
                        continue
                    if key not in found:
                        found[key] = {
                            "value": value,
                            "description": description,
                            "source_file": rel_path,
                        }
    return found


# ---------------------------------------------------------------------------
# Step 4: 設計ルール言語化
# ---------------------------------------------------------------------------

def build_rules(dep_graph: dict, constants: dict) -> dict:
    min_score = constants.get("score_min_threshold", {}).get("value", 40)
    conflict_range = constants.get("score_conflict_range", {}).get("value", 10)
    size_limit = constants.get("merge_size_limit", {}).get("value", 20000)
    has_shortcut = dep_graph.get("hundred_point_shortcut", False)

    routing_flow = [
        "① fastpath check: request に image_base64 があれば OcrRecruitHandler へ即バイパス",
        "② user_signals.json から現在の文脈（active_context）を読み込む（読み込み専用）",
        "③ 全ハンドラーに対してスコアを計算："
        "calculate_score があれば非同期呼び出し（signalsは引数数で自動判定）、"
        "無ければ can_handle の bool を 100/0 点に変換",
        "④ feedback_scores.json から過去の👍/👎補正を取得して final_score に加算",
    ]
    if has_shortcut:
        routing_flow.append(
            "⑤ top score == 100 の場合、競合判定を一切行わず即座に単独実行して return"
        )
    routing_flow += [
        f"⑥ 全ハンドラーの final_score < {min_score} → 「どれも対応不可」テキストを返す",
        f"⑦ 1位と2位の score 差 ≤ {conflict_range} → 「競合」と判定",
        f"⑧ 競合かつ合計 estimate_size ≥ {size_limit} → ユーザーに優先度を聞き返す",
        f"⑨ 競合かつ合計 estimate_size < {size_limit} → 両ハンドラーを実行して _merge_responses でマージ",
        "⑩ 非競合 → 1位ハンドラーのみ実行",
        "⑪ self.last_used_handler / self.active_context に結果を記録するのみ"
        "（ファイルへの書き込みは orchestrator の責務ではない）",
    ]

    handler_interface = {
        "calculate_score": {
            "signature": "async (self, msg: str, signals: dict = {}) -> int",
            "note": "signals 非対応の古いハンドラーは inspect で引数数を確認してから呼ぶ（後方互換）",
        },
        "can_handle": {
            "signature": "async (self, msg: str) -> bool",
            "note": "calculate_score を持たないハンドラー用のフォールバック。True→100点, False→0点",
        },
        "handle": {
            "signature": "async (self, msg: str) -> Tuple[str, Any] | None",
            "note": "戻り値は ('text' | 'ui_code', content) の2値タプル。None を返すとエラー扱い",
        },
        "estimate_size": {
            "signature": "(self, msg: str) -> int",
            "note": "省略可。デフォルト 1000 文字として扱われる",
        },
    }

    merge_strategy = {
        "message": "c1['message'] + '\\n\\n---\\n\\n' + c2['message'] で結合。str の場合は str() で変換",
        "blocks": "c1['blocks'] + c2['blocks'] でリスト結合",
        "return_type_decision": "merged['blocks'] が非空なら 'ui_code'、空なら 'text'（固定値ではない）",
        "null_safety": "どちらかが None の場合は非 None 側だけを返す",
    }

    backward_compat = (
        "calculate_score の引数数を inspect.signature で確認し、"
        "パラメータが2つ（self+msg）なら signals を渡さず呼び出す"
    )

    non_signals_handlers = [
        h["class_name"] for h in dep_graph.get("handlers", [])
        if not h.get("has_signals_param", True)
    ]
    fallback_handlers = [
        h["class_name"] for h in dep_graph.get("handlers", [])
        if not h.get("has_calculate_score") and h.get("has_can_handle")
    ]
    external_plugin_handlers = [
        name for name, src in dep_graph.get("handler_sources", {}).items()
        if src.startswith("plugins.")
    ]

    return {
        "routing_flow": routing_flow,
        "handler_interface": handler_interface,
        "merge_strategy": merge_strategy,
        "backward_compat": backward_compat,
        "non_signals_handlers": non_signals_handlers,
        "fallback_score_handlers": fallback_handlers,          # v2
        "external_plugin_handlers": external_plugin_handlers,  # v2
        "return_types": ["text", "ui_code"],
    }


def build_naming_rules(dep_graph: dict) -> dict:
    handler_names = [h["class_name"] for h in dep_graph.get("handlers", [])]
    suffixes = set(
        m.group(1) for n in handler_names if (m := re.search(r'(Handler)$', n))
    )
    return {
        "handler": "○○Handler（必ずこのサフィックスで終わること。TS/Py 共通）",
        "handler_suffix": sorted(suffixes)[0] if suffixes else "Handler",
        "handler_method_score_py": "calculate_score",
        "handler_method_score_ts": "calculateScore",
        "handler_method_exec_py": "handle",
        "handler_method_size_py": "estimate_size",
        "memory_dir": "backend/.ai_memory",
        "memory_feedback_file": "feedback_scores.json",
        "memory_signals_file": "user_signals.json",
        "return_type_text": "text",
        "return_type_ui": "ui_code",
    }


def build_memory_system() -> dict:
    return {
        "feedback_scores": {
            "path": "backend/.ai_memory/feedback_scores.json",
            "key_format": "normalized_message（lowercase + 半角/全角スペース除去）",
            "value_format": "{ handler_name: score_delta }",
            "effect": "base_score に加算される補正値。👍 で +N、👎 で -N",
        },
        "user_signals": {
            "path": "backend/.ai_memory/user_signals.json",
            "fields": {
                "last_used_handler": "直前に実行されたハンドラークラス名",
                "active_context": "例: 'recruitment'（OcrRecruitHandler 実行後に付与）",
            },
            "effect": "calculate_score の第2引数 signals として渡され、文脈継続スコアに使える",
            # v2: 書き込み主体の実態を修正
            "read_by": "ChatOrchestrator（route_and_execute 冒頭で読み込み専用）",
            "write_by": "routes_chat.py がリクエスト完了後にバックグラウンドで書き込む"
                        "（orchestrator 自身は last_used_handler / active_context を"
                        "インスタンス変数に持つだけでファイルには書かない）",
        },
    }


# ---------------------------------------------------------------------------
# Step 5: JSON 倉庫のマニフェスト化
# ---------------------------------------------------------------------------

def scan_json_warehouse(project_root: str, exclude_names: set[str] | None = None) -> dict:
    """
    knowledge.json 以外に増殖している JSON ファイル群を棚卸しする。
    各ファイルについて:
      - パス
      - 最終更新時刻
      - トップレベルのキー一覧（値そのものは読まない。個人情報や記憶データを
        knowledge.json に混ぜ込みたくないため、"構造だけ" を見る）
      - 推定される役割（ファイル名やディレクトリ名からのヒューリスティック）
    """
    exclude_names = exclude_names or {"knowledge.json"}
    root = Path(project_root)
    manifest: list[dict] = []

    role_hints = {
        "feedback": "フィードバックスコア（👍/👎補正）",
        "signal": "ユーザー文脈・直近ハンドラー等の状態",
        "memory": "AIの記憶・履歴データ",
        "config": "設定値",
        "schema": "スキーマ定義",
    }

    for json_path in sorted(root.rglob("*.json")):
        if "node_modules" in json_path.parts or ".git" in json_path.parts:
            continue
        if json_path.name in exclude_names:
            continue

        rel_path = str(json_path.relative_to(root))
        try:
            stat = json_path.stat()
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            top_level_keys = list(data.keys()) if isinstance(data, dict) else (
                ["<配列: 要素数 {}>".format(len(data))] if isinstance(data, list) else []
            )
            readable = True
        except Exception as e:
            top_level_keys = []
            readable = False
            stat = json_path.stat()

        guessed_role = next(
            (label for key, label in role_hints.items() if key in json_path.name.lower()),
            "不明（要手動タグ付け）",
        )

        manifest.append({
            "path": rel_path,
            "size_bytes": stat.st_size,
            "last_modified": stat.st_mtime,
            "readable_json": readable,
            "top_level_keys": top_level_keys,
            "guessed_role": guessed_role,
        })

    return {
        "count": len(manifest),
        "files": manifest,
    }


# ---------------------------------------------------------------------------
# メインエントリ
# ---------------------------------------------------------------------------

class ProjectKnowledgeEngine:
    def __init__(self, project_root: str, output_path: str = "knowledge.json"):
        self.project_root = os.path.abspath(project_root)
        self.output_path = output_path

    def run(self, export: bool = True) -> dict:
        print("📂 [1/6] フォルダをスキャン中（.py / .ts / .tsx）...")
        file_map = scan_folder(self.project_root)
        self._print_file_summary(file_map)

        print("\n🔗 [2/6] 依存関係を解析中...")
        dep_graph = extract_dependencies(self.project_root, file_map)
        print(f"   ハンドラー検出: {len(dep_graph['handlers'])} 個")
        print(f"   実行順序: {dep_graph['handler_order']}")
        if dep_graph.get("fastpath"):
            print(f"   ファストパス: {dep_graph['fastpath']}")
        if dep_graph.get("hundred_point_shortcut"):
            print("   ⚡ 100点即時実行ショートカットを検出")

        print("\n🔢 [3/6] 定数・変数を抽出中...")
        constants = extract_variables(self.project_root, file_map)
        for k, v in constants.items():
            print(f"   {k} = {v['value']}  ({v['description']})")

        print("\n📐 [4/6] 設計ルールを構築中...")
        design_rules = build_rules(dep_graph, constants)
        naming_rules = build_naming_rules(dep_graph)
        memory_system = build_memory_system()

        print("\n🗄️  [5/6] JSON 倉庫を棚卸し中...")
        json_warehouse = scan_json_warehouse(
            self.project_root, exclude_names={os.path.basename(self.output_path)}
        )
        print(f"   検出された JSON: {json_warehouse['count']} 個")
        for item in json_warehouse["files"]:
            tag = "✅" if item["readable_json"] else "❌ (パース失敗)"
            print(f"   {tag} {item['path']}  役割推定: {item['guessed_role']}")

        print("\n📦 [6/6] JSON に変換中...")
        schema = {
            "naming_rules": naming_rules,
            "dependency_graph": {
                "orchestrator": dep_graph["orchestrator"],
                "handler_order": dep_graph["handler_order"],
                "handler_sources": dep_graph.get("handler_sources", {}),
                "handlers": dep_graph["handlers"],
                "fastpath": dep_graph.get("fastpath", {}),
                "hundred_point_shortcut": dep_graph.get("hundred_point_shortcut", False),
            },
            "constants": constants,
            "design_rules": design_rules,
            "memory_system": memory_system,
            "json_warehouse": json_warehouse,
            "meta": {
                "generated_from": self.project_root,
                "engine_version": "2.0.0",
            },
        }

        if export:
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 出力完了: {self.output_path}")

        return schema

    def _print_file_summary(self, file_map: dict[str, list[str]]):
        for dir_key, files in file_map.items():
            print(f"   [{dir_key}] → {len(files)} ファイル")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    output = sys.argv[2] if len(sys.argv) > 2 else "knowledge.json"
    engine = ProjectKnowledgeEngine(target, output)
    engine.run()