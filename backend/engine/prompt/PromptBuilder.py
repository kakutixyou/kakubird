# PromptBuilder.py
import os
import json
from typing import Any, Dict, List, Optional

class PromptBuilder:
    def __init__(self):
        # AIアシスタントへの基本的な振る舞いとファイル出力形式の定義（ベースシステムプロンプト）
        self.base_system_prompt = (
            "あなたは非常に優秀なフルスタックエンジニアであり、プログラミングアシスタントです。\n"
            "ユーザーの要望に対して、正確で安全、かつメンテナンス性の高いコードを提供してください。\n"
            "回答内で新規ファイルの作成や既存ファイルの修正を行う場合は、以下の【ファイル出力フォーマット】を必ず厳守してください。\n\n"
            "【ファイル出力フォーマット】\n"
            "FILE: <ファイルへの相対パス>\n"
            "```<言語名>\n"
            "// ここにファイルの内容全体（一部分だけの省略ではなく、そのまま動作する完全なコード）を記述\n"
            "```\n"
            "※ 複数のファイルを生成・修正する場合、このフォーマットを繰り返してください。\n"
            "※ ファイルのヘッダー名（FILE: パス）は、コードブロックの直前に、独立した1行で記述してください。\n"
            "※ マークダウンの解説テキストとコードブロックは明確に分けて記述してください。\n"
        )
        # ✅ 動的ナレッジを保持するためのリストを初期化
        self.active_knowledge: List[Dict[str, Any]] = []

    def set_active_knowledge(self, knowledge_list: List[Dict[str, Any]]):
        """
        KnowledgeRouter等で取得したナレッジデータ（辞書のリスト）をセットします。
        """
        self.active_knowledge = knowledge_list if isinstance(knowledge_list, list) else []
        print(f"📥 [PromptBuilder] {len(self.active_knowledge)} 件のナレッジをセットしました。")

    def build(self, user_text: str, *args, signals: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """
        現在のコンテキスト、履歴、エラー状態（Signals）、およびロードされたナレッジを統合し、
        LLMに渡す最終的なプロンプトを構築します。
        """
        if signals is None:
            signals = {}

        # 現在の動作モード（デフォルトは unknown）
        active_mode = signals.get("active_mode", "unknown")

        # 1. 会話履歴の構築（直近3件分など、ContextManagerから引き継ぐ）
        history_str = self._build_history_prompt(signals.get("recent_history", []))

        # 2. ワークスペースの文脈（現在開いているファイルや編集中のコード）の構築
        workspace_context = ""
        active_context = signals.get("active_context")
        base_code = signals.get("base_code")

        if active_context:
            workspace_context += f"【現在の編集環境】\n{active_context}\n"
        if base_code:
            # コード修復モードでない場合、またはベースコードが存在する場合に表示
            workspace_context += f"【現在ワークスペースにあるコード】\n```python\n{base_code}\n```\n"

        # ✅ 3. ロードされているナレッジ情報をプロンプト用テキストに構築
        knowledge_context = ""
        if self.active_knowledge:
            knowledge_context += "【システムが検出した関連ナレッジ（最優先ルール・仕様）】\n"
            for k in self.active_knowledge:
                title = k.get("title", "仕様ナレッジ")
                content = k.get("content", k)
                
                # コンテンツが辞書やリストの場合は読みやすいJSON形式に展開
                if isinstance(content, (dict, list)):
                    content_str = json.dumps(content, ensure_ascii=False, indent=2)
                else:
                    content_str = str(content)
                    
                knowledge_context += f"■ {title}:\n{content_str}\n---\n"
            knowledge_context += "※実装を行う際、上記のナレッジやルールを最優先で順守してください。\n"

        # 4. モードごとに専用指示プロンプトを差し替え・追加
        if active_mode == "code_healing":
            mode_prompt = self._build_healing_prompt(signals)
        elif active_mode == "ui_design":
            mode_prompt = self._build_ui_design_prompt(signals)
        else:
            mode_prompt = self._build_general_prompt(signals)

        # 5. すべてのパーツを統合 (ナレッジコンテキストを適切な場所に挿入)
        final_prompt = (
            f"{self.base_system_prompt}\n"
            f"=====\n"
            f"【これまでの会話履歴（直近の文脈）】\n"
            f"{history_str}\n"
            f"=====\n"
            f"{workspace_context}\n"
            f"=====\n"
            f"{knowledge_context}" # ✅ ナレッジ情報を埋め込み
            f"=====\n"
            f"{mode_prompt}\n"
            f"=====\n"
            f"【ユーザーからの直接指示】\n"
            f"{user_text}\n"
        )

        # 次回呼び出し時のために、使用済みのナレッジをクリア（必要な場合のみ）
        # self.active_knowledge = [] 

        return final_prompt

    def _build_history_prompt(self, history: List[Dict[str, Any]]) -> str:
        """会話履歴をプロンプト用にテキスト化する"""
        if not history:
            return "（過去の会話履歴はありません）"
        
        lines = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_label = "ユーザー" if role == "user" else "アシスタント"
            lines.append(f"[{role_label}]:\n{content}\n")
        return "\n---\n".join(lines)

    def _build_healing_prompt(self, signals: Dict[str, Any]) -> str:
        """構文エラーが発生している時の「自己修復（code_healing）」指示プロンプト"""
        error_info = signals.get("error_info") or {}
        base_code = signals.get("base_code", "# コードが見つかりませんでした")

        err_msg = error_info.get("message", "構文エラー（SyntaxError）")
        err_line = error_info.get("line", "不明")
        err_offset = error_info.get("offset", "不明")
        err_text = error_info.get("text", "")

        healing_prompt = (
            "🚨【最優先警告：コード修復モード（code_healing）】🚨\n"
            "現在、あなたが直前に出力したコードに構文エラー（SyntaxError）が検出されました。\n"
            "ユーザーはコードを実行できずに困っています。以下の「エラー情報」と「問題のあるコード」を注意深く確認し、エラーを解決してください。\n\n"
            "<error_info>\n"
            f"エラー内容: {err_msg}\n"
            f"発生場所  : {err_line}行目 (文字位置: {err_offset})\n"
            f"エラー行のコード: {err_text}\n"
            "</error_info>\n\n"
            "<broken_code>\n"
            f"{base_code}\n"
            "</broken_code>\n\n"
            "【出力ルール（厳守）】\n"
            "以下の順番で、指定された構成のみを出力してください。余計な前置きや挨拶は一切不要です。\n\n"
            "1. ### 解説\n"
            "なぜこのエラーが起きたのかの原因と修正方法を、ユーザー向けに日本語で分かりやすく簡潔に解説してください。\n\n"
            "2. ### 修正コード\n"
            "その後、修正を適用した「コードの全体」を、以下の【FILEフォーマット】で出力してください。\n"
            "部分的な省略は行わず、必ずすべての行を記述した完全なファイルを出力してください。\n\n"
            "FILE: app.py  (※ファイル名は既存のものに合わせて適切に設定してください)\n"
            "```python\n"
            "# ここに修正した完全なコード\n"
            "```\n"
        )
        return healing_prompt

    def _build_ui_design_prompt(self, signals: Dict[str, Any]) -> str:
        """UIデザインモードがONのときの指示プロンプト"""
        theme = signals.get("theme", "modern")
        responsive = "有効 (スマートフォン等の画面サイズに最適化してください)" if signals.get("responsive") else "無効"

        ui_prompt = (
            "🎨【UIデザインモードが有効です】🎨\n"
            "ユーザーは美しいデザインのUIやモジュールの作成・修正を望んでいます。\n"
            "以下の要件とデザインポリシーを取り入れてコードを構築してください。\n\n"
            f"- 全体のテーマ: {theme}\n"
            f"- レスポンシブ対応: {responsive}\n\n"
            "※ モダンで直感的なインターフェースになるよう、一貫性のあるマージンやカラーパレット、トランジション等を考慮してください。\n"
            "※ コードブロックを出力する際は、共通の【ファイル出力フォーマット】に従ってください。\n"
        )
        return ui_prompt

    def _build_general_prompt(self, signals: Dict[str, Any]) -> str:
        """通常の対話・一般的なプログラミング指示のときのプロンプト"""
        return (
            "📝【通常対話・開発モード】\n"
            "文脈に沿って、ユーザーの質問や指示に的確に回答してください。\n"
            "もしコードを記述する場合は、必ず前述の【ファイル出力フォーマット】(FILE: パス名 + コードブロック) に則って出力してください。\n"
        )