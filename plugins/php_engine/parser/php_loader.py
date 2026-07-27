"""
plugins/php_engine/parser/php_loader.py

php_engineプラグインのメイン実行モジュール。
chat_orchestratorから _execute_php() 経由で呼び出される。

処理フロー:
    Phase A — knowledge参照 + セキュリティレビュー (php_embedding.py)
    Phase B — テンプレート選択 + sandbox参照
    Phase C — Ollama (LLM) によるコード/企画書生成
    Output  — generated/outputs/ に保存 + dictで返却

依存: httpx, jinja2
インストール: pip install httpx jinja2
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────
# パス定数
# ────────────────────────────────────────────

_BASE        = Path(__file__).parent.parent          # plugins/php_engine/
KNOWLEDGE_DIR = _BASE / "knowledge"
TEMPLATES_DIR = _BASE / "templates"
SANDBOX_DIR   = _BASE / "sandbox"
OUTPUTS_DIR   = _BASE / "generated" / "outputs"
CACHE_DIR     = _BASE / "generated" / "cache"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────
# Ollama設定
# ────────────────────────────────────────────

OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "llama3"          # 環境に合わせて変更
OLLAMA_TIMEOUT = 120               # 秒


# ────────────────────────────────────────────
# 出力モード
# ────────────────────────────────────────────

MODE_CODE     = "code"      # PHPコード生成
MODE_PROPOSAL = "proposal"  # 企画書（UCドキュメント + テーブル定義）
MODE_REVIEW   = "review"    # コードレビューのみ


# ────────────────────────────────────────────
# ユーティリティ
# ────────────────────────────────────────────

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _detect_mode(user_input: str) -> str:
    """
    ユーザー入力からMODE_*を判定する。
    chat_orchestratorのplugin.json triggerより細かい粒度で判別。
    """
    text = user_input.lower()

    proposal_kw = ["企画書", "ucドキュメント", "仕様書", "機能一覧",
                   "テーブル定義", "テーブルレイアウト", "uc ", "ユースケース"]
    review_kw   = ["レビュー", "review", "チェック", "採点", "問題ある",
                   "セキュリティ確認"]
    code_kw     = ["コードを書いて", "コードを作って", "実装して", "生成して",
                   "phpのコード", "php書いて", "crud", "api", "ログイン機能"]

    for kw in proposal_kw:
        if kw in text:
            return MODE_PROPOSAL
    for kw in review_kw:
        if kw in text:
            return MODE_REVIEW
    for kw in code_kw:
        if kw in text:
            return MODE_CODE

    # デフォルト: コード生成
    return MODE_CODE


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        logger.warning(f"[php_loader] ファイルが見つかりません: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_text(path: Path) -> str | None:
    if not path.exists():
        logger.warning(f"[php_loader] ファイルが見つかりません: {path}")
        return None
    return path.read_text(encoding="utf-8")


def _save_output(filename: str, content: str) -> Path:
    """generated/outputs/ に保存してパスを返す。"""
    out = OUTPUTS_DIR / filename
    out.write_text(content, encoding="utf-8")
    logger.info(f"[php_loader] 出力保存: {out}")
    return out


# ────────────────────────────────────────────
# Phase A — knowledge参照 + セキュリティスコアリング
# ────────────────────────────────────────────

def phase_a_knowledge(
    user_input: str,
    mode: str,
    code_snippet: str | None = None,
) -> dict:
    """
    knowledgeフォルダーから関連情報を取得する。
    - security: 常に参照（コードが渡された場合はレビューも実施）
    - patterns:  コード生成・企画書共通
    - sql:       テーブル定義・CRUD時に追加参照
    - basics:    基礎確認が必要なクエリ時に追加参照

    Returns:
        {
            "security_summary": str,    # AIプロンプト用セキュリティ要約
            "critical_hits":    list,   # CRITICALルールヒット一覧
            "pattern_summary":  str,    # 関連パターン要約
            "sql_summary":      str,    # SQL関連サマリー（該当時のみ）
            "score":            int,    # セキュリティ採点（0-100）
            "auto_fail":        bool,   # CRITICAL即D判定フラグ
        }
    """
    try:
        from parser.php_embedding import get_engine
        engine = get_engine()
    except ImportError:
        logger.warning("[php_loader] php_embeddingが使えません。knowledge参照をスキップします。")
        return _empty_phase_a()

    # ── セキュリティレビュー ──
    target   = code_snippet if code_snippet else user_input
    review   = engine.review_code(target, top_k=5)
    sec_hits = review["hits"]
    crit     = review["critical_hits"]

    # スコア計算（php_security.json の scoring 定義に準拠）
    deductions = {"critical": 30, "high": 15, "medium": 8, "low": 3}
    score      = 100
    auto_fail  = False

    for h in sec_hits:
        if h["score"] < 0.45:      # 類似度が低いものは無視
            continue
        sev   = h["doc"].get("severity", "low")
        score -= deductions.get(sev, 0)

    score = max(0, score)

    # auto_failルール（php_security.json scoring_guide 準拠）
    auto_fail_ids = {"sqli_001", "auth_001", "api_001"}
    for h in crit:
        if h["doc"].get("id") in auto_fail_ids and h["score"] >= 0.5:
            auto_fail = True
            break

    # ── パターン参照 ──
    pat_hits = engine.search(user_input, top_k=3, score_threshold=0.4)
    pat_lines = [
        f"- {h['doc'].get('title','')} ({h['doc'].get('source_file','')})"
        for h in pat_hits
        if h["doc"].get("source_file") != "php_security.json"
    ]
    pattern_summary = "\n".join(pat_lines) if pat_lines else "（なし）"

    # ── SQL参照（テーブル定義・CRUD時） ──
    sql_summary = ""
    needs_sql   = mode in (MODE_CODE, MODE_PROPOSAL) and any(
        kw in user_input.lower()
        for kw in ["sql", "テーブル", "crud", "select", "insert", "db", "データベース"]
    )
    if needs_sql:
        sql_path = KNOWLEDGE_DIR / "php_sql_examples.json"
        sql_data = _load_json(sql_path)
        if sql_data:
            # リスト先頭3件のtitle+descriptionをサマリー化
            items = sql_data if isinstance(sql_data, list) else []
            sql_lines = [
                f"- {item.get('title','')}: {item.get('description','')}"
                for item in items[:3]
            ]
            sql_summary = "\n".join(sql_lines)

    return {
        "security_summary": review["summary"],
        "critical_hits":    crit,
        "pattern_summary":  pattern_summary,
        "sql_summary":      sql_summary,
        "score":            score,
        "auto_fail":        auto_fail,
    }


def _empty_phase_a() -> dict:
    return {
        "security_summary": "",
        "critical_hits":    [],
        "pattern_summary":  "",
        "sql_summary":      "",
        "score":            100,
        "auto_fail":        False,
    }


# ────────────────────────────────────────────
# Phase B — テンプレート選択 + sandbox参照
# ────────────────────────────────────────────

def phase_b_template(
    user_input: str,
    mode: str,
) -> dict:
    """
    templatesフォルダーから最適なテンプレートを選択し、
    sandboxから関連サンプルを収集する。

    Returns:
        {
            "template_name": str,          # "crud" | "api" | "login" | None
            "template_code": str,          # テンプレートファイルの中身
            "sandbox_snippets": list[str], # 関連sandboxコードのリスト
        }
    """
    # ── テンプレート選択 ──
    try:
        from parser.php_embedding import get_engine
        tmpl_name = get_engine().suggest_template(user_input)
    except ImportError:
        tmpl_name = _keyword_template(user_input)

    template_code = ""
    if tmpl_name:
        path = TEMPLATES_DIR / f"{tmpl_name}_template.php"
        template_code = _load_text(path) or ""

    # ── sandbox参照 ──
    sandbox_snippets: list[str] = []
    text_lower = user_input.lower()

    # UIフォーム系
    if any(kw in text_lower for kw in ["フォーム", "form", "アップロード", "upload"]):
        for fname in ["form.php", "upload.php"]:
            code = _load_text(SANDBOX_DIR / "ui" / fname)
            if code:
                sandbox_snippets.append(f"=== {fname} ===\n{code}")

    # DB系
    if any(kw in text_lower for kw in ["db", "データベース", "mysql", "sqlite", "select", "insert"]):
        for fname in ["mysql_connect.php", "select_test.php", "sqlite_connect.php"]:
            code = _load_text(SANDBOX_DIR / "database" / fname)
            if code:
                sandbox_snippets.append(f"=== {fname} ===\n{code}")

    # 基礎系（企画書・初心者向け）
    if mode == MODE_PROPOSAL or any(kw in text_lower for kw in ["基本", "基礎", "変数", "ループ"]):
        for fname in ["variables.php", "loops.php", "echo.php"]:
            code = _load_text(SANDBOX_DIR / "basic" / fname)
            if code:
                sandbox_snippets.append(f"=== {fname} ===\n{code}")

    return {
        "template_name":    tmpl_name,
        "template_code":    template_code,
        "sandbox_snippets": sandbox_snippets,
    }


def _keyword_template(user_input: str) -> str | None:
    """php_embeddingが使えない場合のキーワード fallback。"""
    text = user_input.lower()
    if any(kw in text for kw in ["crud", "一覧", "登録", "編集", "削除"]):
        return "crud"
    if any(kw in text for kw in ["api", "rest", "json", "endpoint"]):
        return "api"
    if any(kw in text for kw in ["ログイン", "login", "認証", "auth"]):
        return "login"
    return None


# ────────────────────────────────────────────
# Phase C — Ollama によるコード/企画書生成
# ────────────────────────────────────────────

def _build_code_prompt(
    user_input:   str,
    phase_a:      dict,
    phase_b:      dict,
) -> str:
    tmpl_block    = phase_b["template_code"] or "（テンプレートなし）"
    sandbox_block = "\n\n".join(phase_b["sandbox_snippets"]) or "（なし）"
    sec_block     = phase_a["security_summary"] or "（なし）"
    pat_block     = phase_a["pattern_summary"]  or "（なし）"
    sql_block     = phase_a["sql_summary"]       or "（なし）"

    return f"""あなたはPHPの専門家です。以下の情報をもとに、安全で実用的なPHPコードを生成してください。

## ユーザーの要求
{user_input}

## ベーステンプレート ({phase_b["template_name"] or "なし"})
```php
{tmpl_block}
```

## 関連sandboxサンプル
{sandbox_block}

## セキュリティチェック結果（必ず守ること）
{sec_block}

## 関連パターン
{pat_block}

## SQL参考
{sql_block}

## 出力ルール
- セキュリティチェック結果のCRITICAL/HIGHに該当する書き方は絶対に使わない
- プリペアドステートメント必須
- 出力は必ず以下のJSONのみ（前後に説明文・コードブロックマーカー不要）

{{"mode":"code","code":"PHPコード全文","explanation":"実装のポイントを日本語で200字以内","security_notes":["注意点1","注意点2"],"template_used":"{phase_b["template_name"] or "none"}"}}"""


def _build_proposal_prompt(
    user_input: str,
    phase_a:    dict,
    phase_b:    dict,
) -> str:
    sec_block = phase_a["security_summary"] or "（なし）"
    sql_block = phase_a["sql_summary"]       or "（なし）"

    return f"""あなたはシステム企画のエキスパートです。以下の要求に対して、UCドキュメントとテーブル定義を含む企画書をMarkdown形式で生成してください。

## ユーザーの要求
{user_input}

## セキュリティ考慮事項
{sec_block}

## テーブル定義参考
{sql_block}

## 出力ルール
- 出力は必ず以下のJSONのみ（前後に説明文・コードブロックマーカー不要）
- documentフィールドはMarkdown形式で記述

{{"mode":"proposal","document":"# 企画書タイトル\\n\\n## 1. 機能概要\\n（説明）\\n\\n## 2. UCドキュメント\\n### UC-001: （ユースケース名）\\n- **アクター**: \\n- **事前条件**: \\n- **主シナリオ**: \\n  1. \\n- **代替フロー**: \\n\\n## 3. テーブル定義\\n| カラム名 | 型 | 制約 | 説明 |\\n|---|---|---|---|\\n\\n## 4. セキュリティ要件\\n","summary":"企画書の要点を100字以内で"}}"""


def _build_review_prompt(
    user_input: str,
    phase_a:    dict,
) -> str:
    sec_block = phase_a["security_summary"] or "問題は検出されませんでした。"
    score     = phase_a["score"]

    return f"""あなたはPHPセキュリティの専門家です。以下のコードをレビューしてください。

## レビュー対象
{user_input}

## 自動検出結果（採点: {score}/100）
{sec_block}

## 出力ルール
- 出力は必ず以下のJSONのみ（前後に説明文・コードブロックマーカー不要）

{{"mode":"review","score":{score},"grade":"{'A' if score>=90 else 'B' if score>=70 else 'C' if score>=50 else 'D'}","issues":[{{"severity":"critical|high|medium|low","line":"該当コード","problem":"問題の説明","fix":"修正方法"}}],"overall":"総評を日本語200字以内"}}"""


async def phase_c_generate(
    user_input: str,
    mode:       str,
    phase_a:    dict,
    phase_b:    dict,
) -> dict:
    """
    Ollamaにプロンプトを送り、JSONレスポンスをパースして返す。
    Ollamaが使えない場合はfallbackレスポンスを返す。

    Returns:
        dict — AIが生成したJSONをパースしたもの
    """
    if mode == MODE_CODE:
        prompt = _build_code_prompt(user_input, phase_a, phase_b)
    elif mode == MODE_PROPOSAL:
        prompt = _build_proposal_prompt(user_input, phase_a, phase_b)
    else:  # MODE_REVIEW
        prompt = _build_review_prompt(user_input, phase_a)

    raw = await _call_ollama(prompt)
    if raw is None:
        return _fallback_response(mode, phase_a, phase_b)

    return _parse_json_response(raw, mode)


async def _call_ollama(prompt: str) -> str | None:
    """Ollama APIを呼び出してテキストを返す。失敗時はNone。"""
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 2048},
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            t0  = time.time()
            res = await client.post(OLLAMA_URL, json=payload)
            res.raise_for_status()
            elapsed = time.time() - t0
            logger.info(f"[php_loader] Ollama応答: {elapsed:.1f}秒")
            return res.json().get("response", "")
    except httpx.ConnectError:
        logger.error("[php_loader] Ollamaに接続できません。起動しているか確認してください。")
    except httpx.TimeoutException:
        logger.error(f"[php_loader] Ollamaがタイムアウトしました ({OLLAMA_TIMEOUT}秒)。")
    except Exception as e:
        logger.error(f"[php_loader] Ollama呼び出しエラー: {e}")
    return None


def _parse_json_response(raw: str, mode: str) -> dict:
    """
    OllamaのレスポンスからJSONを抽出してパースする。
    コードブロックマーカーや前後の余分なテキストを除去する。
    """
    # ```json ... ``` や ``` ... ``` を除去
    text = re.sub(r"```(?:json)?\s*", "", raw).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    # 最初の { から最後の } までを抽出
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        logger.warning("[php_loader] JSONが見つかりませんでした。fallbackを使用します。")
        return _fallback_response(mode)

    json_str = text[start:end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"[php_loader] JSONパースエラー: {e}。fallbackを使用します。")
        return _fallback_response(mode)


def _fallback_response(
    mode:    str,
    phase_a: dict | None = None,
    phase_b: dict | None = None,
) -> dict:
    """OllamaがNGの場合のフォールバック応答。"""
    if mode == MODE_CODE:
        tmpl = (phase_b or {}).get("template_code", "")
        return {
            "mode":            "code",
            "code":            tmpl or "<?php\n// Ollamaが使えないためテンプレートをそのまま返します\n",
            "explanation":     "Ollamaに接続できなかったためテンプレートを返しました。",
            "security_notes":  [(phase_a or {}).get("security_summary", "")],
            "template_used":   (phase_b or {}).get("template_name", "none"),
        }
    elif mode == MODE_PROPOSAL:
        return {
            "mode":     "proposal",
            "document": "# 企画書\n\nOllamaが使えないため生成できませんでした。",
            "summary":  "Ollama接続エラー",
        }
    else:
        score = (phase_a or {}).get("score", 100)
        return {
            "mode":    "review",
            "score":   score,
            "grade":   "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "D",
            "issues":  [],
            "overall": (phase_a or {}).get("security_summary", "レビュー結果を取得できませんでした。"),
        }


# ────────────────────────────────────────────
# Output — generated/outputs/ に保存
# ────────────────────────────────────────────

def save_output(result: dict, user_input: str) -> dict:
    """
    生成結果をファイルに保存し、保存先パスをresultに追加して返す。

    保存ファイル:
        - mode=code     → .php ファイル
        - mode=proposal → .md  ファイル
        - mode=review   → .json ファイル
    """
    ts   = _timestamp()
    mode = result.get("mode", "code")

    if mode == "code":
        code     = result.get("code", "")
        filename = f"code_{ts}.php"
        _save_output(filename, code)
        result["output_file"] = str(OUTPUTS_DIR / filename)

    elif mode == "proposal":
        doc      = result.get("document", "")
        filename = f"proposal_{ts}.md"
        _save_output(filename, doc)
        result["output_file"] = str(OUTPUTS_DIR / filename)

    elif mode == "review":
        filename = f"review_{ts}.json"
        _save_output(filename, json.dumps(result, ensure_ascii=False, indent=2))
        result["output_file"] = str(OUTPUTS_DIR / filename)

    return result


# ────────────────────────────────────────────
# メインエントリー（chat_orchestratorから呼ぶ）
# ────────────────────────────────────────────

async def execute(
    user_input:   str,
    code_snippet: str | None = None,
    mode_override: str | None = None,
) -> dict:
    """
    php_engineプラグインのエントリーポイント。
    chat_orchestratorの _execute_php() から呼び出す。

    Args:
        user_input:    チャット欄のテキスト
        code_snippet:  レビュー対象のコード（MODE_REVIEW時に渡す）
        mode_override: 強制的にモードを指定したい場合

    Returns:
        {
            "mode":          str,          # "code" | "proposal" | "review"
            "response_type": "ui_code",    # フロントエンド向けフラグ
            "score":         int,          # セキュリティスコア（review時）
            "code":          str,          # 生成コード（code時）
            "document":      str,          # 企画書Markdown（proposal時）
            ... + 各Phaseの詳細フィールド
        }
    """
    mode = mode_override or _detect_mode(user_input)
    logger.info(f"[php_loader] モード: {mode} | 入力: {user_input[:60]}...")

    # Phase A
    phase_a = phase_a_knowledge(user_input, mode, code_snippet)

    # auto_fail: CRITICAL脆弱性が確定している場合はPhase C不要
    if phase_a["auto_fail"] and mode == MODE_REVIEW:
        result = {
            "mode":          "review",
            "response_type": "ui_code",
            "score":         0,
            "grade":         "D",
            "issues":        [
                {"severity": h["doc"].get("severity"),
                 "problem":  h["doc"].get("title"),
                 "fix":      h["doc"].get("fix_template")}
                for h in phase_a["critical_hits"]
            ],
            "overall": "重大な脆弱性が検出されました。即座に修正してください。",
            "auto_fail": True,
        }
        return save_output(result, user_input)

    # Phase B
    phase_b = phase_b_template(user_input, mode)

    # Phase C
    result = await phase_c_generate(user_input, mode, phase_a, phase_b)

    # 共通フィールドを付加
    result["response_type"]     = "ui_code"
    result["security_score"]    = phase_a["score"]
    result["template_used"]     = phase_b.get("template_name")
    result["phase_a_summary"]   = phase_a["security_summary"]

    # 保存
    result = save_output(result, user_input)

    logger.info(
        f"[php_loader] 完了 | mode={result['mode']} "
        f"score={result.get('security_score')} "
        f"file={result.get('output_file','')}"
    )
    return result


# ────────────────────────────────────────────
# chat_orchestrator への組み込みサンプル
# ────────────────────────────────────────────
#
# # chat_orchestrator.py に追加するコード
#
# from plugins.php_engine.parser.php_loader import execute as php_execute
#
# def _is_php_request(self, text: str) -> bool:
#     meta = self._load_plugin_meta("php_engine")  # metadata/plugin.json
#     return any(kw in text for kw in meta.get("triggers", []))
#
# async def _execute_php(self, message: str) -> dict:
#     code_snippet = None
#     # ```php ... ``` ブロックが含まれる場合はレビューモード
#     match = re.search(r"```php\s*(.*?)```", message, re.DOTALL)
#     if match:
#         code_snippet = match.group(1)
#     return await php_execute(message, code_snippet=code_snippet)
#


# ────────────────────────────────────────────
# CLI（動作確認用）
# ────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import asyncio

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="php_loader 動作確認ツール")
    parser.add_argument("input",  help="ユーザー入力テキスト")
    parser.add_argument("--mode", choices=[MODE_CODE, MODE_PROPOSAL, MODE_REVIEW],
                        default=None, help="モードを強制指定")
    parser.add_argument("--code", default=None, help="レビュー対象コード（review時）")
    parser.add_argument("--dry",  action="store_true",
                        help="Phase A/BのみでOllama呼び出しをスキップ")
    args = parser.parse_args()

    async def main():
        if args.dry:
            mode    = args.mode or _detect_mode(args.input)
            phase_a = phase_a_knowledge(args.input, mode, args.code)
            phase_b = phase_b_template(args.input, mode)
            print("\n=== Phase A ===")
            print(f"  score     : {phase_a['score']}")
            print(f"  auto_fail : {phase_a['auto_fail']}")
            print(f"  security  :\n{phase_a['security_summary']}")
            print("\n=== Phase B ===")
            print(f"  template  : {phase_b['template_name']}")
            print(f"  sandboxes : {len(phase_b['sandbox_snippets'])}件")
        else:
            result = await execute(args.input, args.code, args.mode)
            print("\n=== 結果 ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(main())