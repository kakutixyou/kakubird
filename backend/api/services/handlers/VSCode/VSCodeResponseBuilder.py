from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from .VSCodeIntentParser import VSCodeIntent


class VSCodeResponseBuilder:
    """
    cards・blocks・エラー形式の統一を行うレスポンスビルダー。
    - `Index.tsx` 側で `VSCodeBlock` と `ProjectBuildBlock` の両方を扱える統一スキーマを出力
    - チャット画面が真っ白になったり意図しないコンポーネントに奪われたりしないよう、
      自然言語の Markdown メッセージを主軸に返す
    """

    @classmethod
    def build(
        cls,
        intent: VSCodeIntent,
        cards: List[Dict[str, Any]],
        generated_task: Optional[Dict[str, Any]],
        written_report: Dict[str, List[str]],
        matched_paths: List[str],
        launch_result: Optional[Dict[str, Any]] = None,
        partial_patch: Optional[Dict[str, Any]] = None,
        project_build_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        embed_html_payload: bool = False,
    ) -> Tuple[str, Dict[str, Any]]:
        summary_lines = cls._build_human_readable_summary(
            intent=intent,
            cards=cards,
            generated_task=generated_task,
            written_report=written_report,
            launch_result=launch_result,
            partial_patch=partial_patch,
            error=error,
        )
        human_message = "\n".join(summary_lines)

        payload: Dict[str, Any] = {
            "status": "error" if error else "success",
            "intent_mode": intent.mode,
            "language": intent.language,
            "target_files": intent.target_files,
            "target_symbol": intent.target_symbol,
            "cards": cards,
            "generated_task": generated_task,
            "written_files": written_report,
            "matched_paths": matched_paths,
            "launch_result": launch_result,
            "partial_patch": partial_patch,
            "error": error,
            "summary": human_message.splitlines()[0] if human_message else "VS Code 処理が完了しました。",
        }

        if embed_html_payload:
            final_message = (
                f"{human_message}\n\n"
                f"<!--VSCODE_PAYLOAD-->{json.dumps(payload, ensure_ascii=False)}"
            )
        else:
            final_message = human_message

        blocks: List[Dict[str, Any]] = [
            {"type": "VSCodeBlock", "data": payload},
            {"type": "vscode", "data": payload},
        ]
        if project_build_data:
            blocks.append({"type": "ProjectBuildBlock", "data": project_build_data})
            blocks.append({"type": "project_build", "data": project_build_data})

        is_vscode_ui_mode = intent.mode in ("task_build", "write_workspace", "vscode_action", "partial_patch")
        meta: Dict[str, Any] = {
            "type": "vscode" if is_vscode_ui_mode else "chat",
            "response_type": "vscode" if is_vscode_ui_mode else "chat",
            "status": "error" if error else "success",
            "mode": "vscode_assistant",
            "source": "vscode_tool",
            "message": final_message,
            "data": payload,
            "content": payload,
            "blocks": blocks,
        }
        return final_message, meta

    @staticmethod
    def _build_human_readable_summary(
        intent: VSCodeIntent,
        cards: List[Dict[str, Any]],
        generated_task: Optional[Dict[str, Any]],
        written_report: Dict[str, List[str]],
        launch_result: Optional[Dict[str, Any]],
        partial_patch: Optional[Dict[str, Any]],
        error: Optional[str],
    ) -> List[str]:
        lines: List[str] = []

        if error:
            lines.append(f"⚠️ VS Code 処理中にエラーが発生しました: {error}")
            return lines

        if intent.mode == "code_analysis":
            lines.append("### `VSCode` パッケージの構成と役割")
            lines.append("- **`VSCodeIntentParser.py`**: 操作モード（コード解析・部分修正・アプリ開発・タスク生成・会話）と対象ファイルの解析")
            lines.append("- **`VSCodeKnowledgeService.py`**: `KnowledgeManager` による検索とカードの取得")
            lines.append("- **`VSCodeTaskBuilder.py`**: 言語・用途・Diff確認に応じた `.vscode/tasks.json` の生成")
            lines.append("- **`WorkspaceFileService.py`**: パス検証・バックアップ作成・安全な書き込み・ロールバック制御")
            lines.append("- **`VSCodeLauncher.py`**: VS Code の起動（Goto / Diff / フォルダ展開）と実行結果管理")
            lines.append("- **`VSCodeResponseBuilder.py`**: `cards`・`blocks`（`VSCodeBlock` / `ProjectBuildBlock`）・エラー形式の統一")
            lines.append("- **`VSCodeHandler.py`**: 意図判定・`ProjectBuilderHandler` との連携調整・共通レスポンス変換")
            return lines

        if partial_patch:
            fp = partial_patch.get("file_path", "")
            sym = partial_patch.get("target_symbol") or f"L{partial_patch.get('modified_start_line', 1)}"
            lines.append(f"✂️ `{fp}` の **{sym}** をピンポイント修正しました。")
        else:
            lines.append(f"VS Code ナレッジ **{len(cards)}件** を準備しました。")

        for c in cards[:3]:
            title = c.get("title", "設定項目")
            shortcut = c.get("shortcut_win")
            desc = c.get("description", "")
            sc_text = f" (`{shortcut}`)" if shortcut and shortcut != "N/A" else ""
            lines.append(f"- **{title}**{sc_text}: {desc}")

        if generated_task and intent.mode in ("task_build", "write_workspace"):
            lines.append("\n#### 生成された `.vscode/tasks.json`")
            lines.append("```json\n" + json.dumps(generated_task, indent=2, ensure_ascii=False) + "\n```")

        if written_report.get("success"):
            lines.append(f"✅ 書き込み完了: `{', '.join(written_report['success'])}`")
        if written_report.get("skipped"):
            lines.append(f"ℹ️ スキップ: `{', '.join(written_report['skipped'])}`")
        if written_report.get("failed"):
            lines.append(f"❌ 書き込み失敗: `{', '.join(written_report['failed'])}`")

        if launch_result:
            if launch_result.get("launched"):
                lines.append(f"🚀 VS Code ({launch_result.get('mode')}) で開きました: `{launch_result.get('target')}`")
            elif launch_result.get("reason"):
                lines.append(f"ℹ️ VS Code 起動スキップ: {launch_result.get('reason')}")

        return lines