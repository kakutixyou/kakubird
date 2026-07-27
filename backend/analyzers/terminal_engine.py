"""
terminal_engine.py
──────────────────
ターミナルOSSの「評価」と「コマンド抽出」を同時に行うハイブリッドエンジン。
自作AIのRAG（検索拡張生成）に最適化されたメタデータも同時に抽出します。
"""

from __future__ import annotations

import logging
import os
import textwrap
import time
from enum import Enum
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 1. ターミナルOSS評価＆抽出スキーマ
# ──────────────────────────────────────────────

class TerminalCategory(str, Enum):
    EMULATOR      = "EMULATOR"
    MULTIPLEXER   = "MULTIPLEXER"
    SHELL         = "SHELL"
    PROMPT        = "PROMPT"
    CLI_FRAMEWORK = "CLI_FRAMEWORK"
    TUI_LIBRARY   = "TUI_LIBRARY"
    PAGER         = "PAGER"
    UTILITY       = "UTILITY"
    UNKNOWN       = "UNKNOWN"

class PlatformSupport(BaseModel):
    linux: bool   = Field(description="Linux対応")
    macos: bool   = Field(description="macOS対応")
    windows: bool = Field(description="Windows対応（WSL含む）")

class CommandSnippet(BaseModel):
    code: str = Field(description="抽出された具体的なコマンドやスクリプト（例: 'ls -la', 'cargo install yazi-fm'）")
    language: str = Field(description="言語名（例: 'bash', 'sh', 'python', 'rust'）")
    explanation: str = Field(description="このコマンドが何を実行するためのものか、簡潔な解説")
    context: str = Field(description="前提条件（例: 'リポジトリのルートで実行'）。不要な場合は空文字")
    use_case: str = Field(description="ユーザーの目的（例: 'インストールしたい時'）")
    source_section: str = Field(description="情報の出所（例: 'README.md', 'qiita_body'）")

class TipSnippet(BaseModel):
    topic: str = Field(description="小ネタのトピック（例: 'パーミッションの注意点', '高速化のコツ'）")
    content: str = Field(description="実務で役立つ豆知識やエラー解決策などの具体的な内容")
    source_section: str = Field(description="情報の出所（例: 'README.md'）")
    
class TerminalEngineResult(BaseModel):
    """Geminiから確実に返却される評価＋抽出の統合結果"""
    # ── 基本分類 ─────────────────────────────────
    category: TerminalCategory = Field(description="ターミナルOSSのカテゴリ分類")
    platform_support: PlatformSupport = Field(description="動作確認済み or 想定プラットフォーム")

    # ── ターミナル特化スコア（0.0〜1.0） ────────────
    ux_score: float = Field(description="操作性・使い勝手のスコア (0.0〜1.0)")
    performance_score: float = Field(description="動作の軽快さ・リソース効率のスコア (0.0〜1.0)")
    integration_score: float = Field(description="他ツールや自作システムへの組み込みやすさ (0.0〜1.0)")

    # ── 要約・評価 ────────────────────────────────
    summary: str = Field(description="このOSSの1〜2文要約（日本語）")
    strengths: list[str] = Field(description="主な強み（最大3件）")
    weaknesses: list[str] = Field(description="主な弱点・注意点（最大3件）")
    best_for: str = Field(description="どのような人・プロジェクトに最適か（1文）")
    similar_tools: list[str] = Field(description="競合・類似するOSS（例: ['tmux', 'zellij']）")

    # ── RAG抽出 ───────────────────────────────────
    extracted_codes: list[CommandSnippet] = Field(
        description="本文から抽出された実践的で再利用可能なコマンドリスト。無い場合は空リスト。"
    )
    extracted_tips: list[TipSnippet] = Field(
        default_factory=list,
        description="コマンドではないが実務で役立つ小ネタや注意点。無い場合は空リスト。"
    )
    notes: str = Field(description="特筆すべき設定ファイル構造やOSごとの違いなど")


# ──────────────────────────────────────────────
# 2. システムプロンプト
# ──────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
あなたはターミナル・CLIツールの専門評価AIであり、自作AIの知識データベース（RAG）構築も担っています。
入力されたメタ情報と「本文テキスト（README、技術記事等）」をもとに、指定JSONスキーマに完全に準拠して評価とコマンド抽出を行ってください。

## 評価・抽出方針
- 評価タスク: ツールのUX、パフォーマンス、組み込みやすさを 0.0〜1.0 で客観的にスコアリングしてください。
- 抽出タスク: 本文から、実践的で再利用可能なコマンド（インストール、起動、応用引数など）と、実務で役立つ小ネタ（Tips）を抽出してください。
- 各コマンドには必ず「use_case（〜したい時）」と「context（前提条件）」を付与してください。
""").strip()


# ──────────────────────────────────────────────
# 3. TerminalEngine クラス本体
# ──────────────────────────────────────────────

class TerminalEngine:
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            logger.warning("[TerminalEngine] GEMINI_API_KEY が未設定です。")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def analyze(self, item_dict: dict) -> TerminalEngineResult:
        """1件のOSS情報を解析して結果を返す"""
        if not self.client:
            return self._fallback_result("APIキー未設定")

        # 抽出元テキストの特定とクリッピング（API制限回避のため8000文字に制限）
        raw_text = item_dict.get("full_body") or item_dict.get("content") or item_dict.get("readme") or ""
        clipped_text = raw_text[:5000]

        source_hint = "qiita_body" if "full_body" in item_dict else "README"

        user_prompt = textwrap.dedent(f"""
        以下のOSS情報を解析してください。
        
        名前: {item_dict.get('name') or item_dict.get('title', 'UNKNOWN')}
        説明: {item_dict.get('description', '')}
        スター数: {item_dict.get('stars', item_dict.get('lgtm_count', 0))}
        言語: {item_dict.get('language', '不明')}
        情報源: {source_hint}
        
        ## 本文 (README / 記事本文)
        {clipped_text}
        """).strip()

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,  # 抽出精度を上げるために低く設定
                    response_mime_type="application/json",
                    response_schema=TerminalEngineResult,
                )
            )

            if response.text is None:
                raise ValueError("Empty response from Gemini API")

            return TerminalEngineResult.model_validate_json(response.text)

        except ValidationError as e:
            name = item_dict.get('name') or item_dict.get('title', 'UNKNOWN')
            logger.error(f"[TerminalEngine] スキーマ検証エラー ({name}): {e}")
            return self._fallback_result(f"Validation Error: {str(e)}")
        except Exception as e:
            name = item_dict.get('name') or item_dict.get('title', 'UNKNOWN')
            logger.error(f"[TerminalEngine] API呼び出しエラー ({name}): {e}")
            return self._fallback_result(f"API Error: {str(e)}")

    def analyze_batch(self, items: list[dict], delay_sec: float = 15.0) -> list[tuple[dict, TerminalEngineResult]]:
        """
        複数件を一括で解析する。
        無料枠のトークン制限（15RPM / TPM）を回避するため、デフォルトで15秒の待機を挟む。
        """
        results = []
        total = len(items)
        
        for i, item in enumerate(items):
            name = item.get("name") or item.get("title", "unknown")
            logger.info(f"[TerminalEngine] 評価中 {i+1}/{total}: {name}")
            
            res = self.analyze(item)
            results.append((item, res))
            
            # 最後の1件以外はインターバルを空ける
            if i < total - 1:
                logger.info(f"  -> API制限回避のため {delay_sec} 秒待機します...")
                time.sleep(delay_sec)
                
        return results

    def _fallback_result(self, error_msg: str) -> TerminalEngineResult:
        """APIが落ちた場合でも、ワークフローを止めないためのダミー結果"""
        return TerminalEngineResult(
            category=TerminalCategory.UNKNOWN,
            platform_support=PlatformSupport(linux=False, macos=False, windows=False),
            ux_score=0.0,
            performance_score=0.0,
            integration_score=0.0,
            summary="解析エラーが発生しました。",
            strengths=[],
            weaknesses=[],
            best_for="不明",
            similar_tools=[],
            extracted_codes=[],
            extracted_tips=[],
            notes=f"エラー詳細: {error_msg}"
        )