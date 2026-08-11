<<<<<<< HEAD
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from api.services.manager.KnowledgeManager import KnowledgeManager

logger = logging.getLogger(__name__)


# =========================================================
# 判定結果DTO
# =========================================================
@dataclass
class HumanReviewDecision:
    requires_review: bool
    project_name: str
    summary: str
    alerts: List[Dict[str, Any]]
    chat_message: str


class KnowledgeOrchestra:
    """
    役割:
      - KnowledgeManager から最新ナレッジを読む
      - human_advice.status を評価
      - REQUIRES_HUMAN_REVIEW の場合だけ、最終出力を止めるための判定を返す
      - Chat通知用メッセージを組み立てる

    使い方（DeploymentHandler側の想定）:
      orchestra = KnowledgeOrchestra(base_dir=".")
      blocked, msg = orchestra.guard_before_finalize(relative_dir_path="analyzed_results")
      if blocked:
          return "text", msg
      # blockedでなければ通常処理を続行
    """

    def __init__(
        self,
        base_dir: str = "./knowledge_store",
        index_filename: str = "index.json",
    ) -> None:
        self.knowledge_manager = KnowledgeManager(base_dir)
        self.index_filename = index_filename

    # ---------------------------------------------------------
    # Public API: ガード判定（handle() からこれを呼ぶ）
    # ---------------------------------------------------------
    def guard_before_finalize(
        self,
        relative_dir_path: str = "analyzed_results",
        force_rebuild: bool = False,
        latest_only: bool = True,
    ) -> Tuple[bool, str]:
        """
        Returns:
          (True,  停止メッセージ)  -> REQUIRES_HUMAN_REVIEWあり、最終出力を止める
          (False, "")              -> 停止不要、最終出力してOK
        """
        decision = self.evaluate_human_review(
            relative_dir_path=relative_dir_path,
            force_rebuild=force_rebuild,
            latest_only=latest_only,
        )

        if decision.requires_review:
            logger.warning(
                "🚫 Human review required. project=%s alerts=%d",
                decision.project_name,
                len(decision.alerts),
            )
            return True, decision.chat_message

        logger.info("✅ Human review not required.")
        return False, ""

    # ---------------------------------------------------------
    # Public API: 判定本体
    # ---------------------------------------------------------
    def evaluate_human_review(
        self,
        relative_dir_path: str = "analyzed_results",
        force_rebuild: bool = False,
        latest_only: bool = True,
    ) -> HumanReviewDecision:
        """
        Knowledgeを読み込み、REQUIRES_HUMAN_REVIEW を検出する。
        latest_only=True の場合は更新日時が最も新しい1件を優先評価。
        """

        logger.info("オーケストレータ: ナレッジ評価開始 dir=%s", relative_dir_path)

        knowledges = self.knowledge_manager.load_all_json_from_dir(
            relative_dir_path=relative_dir_path,
            index_filename=self.index_filename,
            force_rebuild=force_rebuild,
        )

        if not knowledges:
            # データが無いときは停止しない（運用方針次第で逆にもできる）
            logger.info("評価対象ナレッジが0件。ガードは発動しません。")
            return HumanReviewDecision(
                requires_review=False,
                project_name="(unknown)",
                summary="",
                alerts=[],
                chat_message="",
            )

        targets = knowledges
        if latest_only:
            latest = self._pick_latest_knowledge(knowledges)
            targets = [latest] if latest is not None else []

        # 優先: REQUIRES_HUMAN_REVIEW を最初に見つけた時点で返す
        for k in targets:
            content = k.get("content", {}) or {}
            human_advice = content.get("human_advice", {}) or {}

            status = str(human_advice.get("status", "")).strip().upper()
            if status == "REQUIRES_HUMAN_REVIEW":
                project_name = self._project_name_of(k)
                summary = human_advice.get("summary", "重要な確認事項があります。")
                alerts = human_advice.get("alerts", []) or []

                chat_message = self._build_human_review_message(
                    project_name=project_name,
                    summary=summary,
                    alerts=alerts,
                )

                return HumanReviewDecision(
                    requires_review=True,
                    project_name=project_name,
                    summary=summary,
                    alerts=alerts,
                    chat_message=chat_message,
                )

        return HumanReviewDecision(
            requires_review=False,
            project_name=self._project_name_of(targets[0]) if targets else "(unknown)",
            summary="",
            alerts=[],
            chat_message="",
        )

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------
    def _project_name_of(self, k: Any) -> str:
        """
        LazyKnowledge互換:
          - title
          - name
          - id
          - file_path
        の順で採用
        """
        return (
            k.get("title")
            or k.get("name")
            or k.get("id")
            or k.get("file_path")
            or "(unknown)"
        )

    def _pick_latest_knowledge(self, knowledges: List[Any]) -> Optional[Any]:
        """
        indexメタの updated_at を優先し、無ければ mtime を使って最新を選ぶ。
        """
        if not knowledges:
            return None

        def key_fn(k: Any):
            updated_at = k.get("updated_at")
            mtime = k.get("mtime", 0)
            # updated_at が文字列でも比較可能なISO想定。無ければmtimeで代替。
            return (str(updated_at or ""), float(mtime or 0.0))

        return sorted(knowledges, key=key_fn, reverse=True)[0]

    def _build_human_review_message(
        self,
        project_name: str,
        summary: str,
        alerts: List[Dict[str, Any]],
    ) -> str:
        """
        Chat通知メッセージを構築。
        DeploymentHandler.handle() の戻り値にそのまま使えるテキスト。
        """
        lines: List[str] = []
        lines.append(f"⚠️ **プロジェクト [{project_name}] に関する重要なお知らせ**")
        lines.append("")
        lines.append(str(summary))
        lines.append("")

        if not alerts:
            lines.append("- 詳細アラートはありませんが、人間確認が必要と判定されました。")
        else:
            for alert in alerts:
                level = alert.get("level", "WARN")
                analyzer = alert.get("analyzer", "Analyzer")
                message = alert.get("message", "確認が必要です。")
                lines.append(f"**[{level}] {analyzer} より:**")
                lines.append(str(message))

                # 正解例（修正案）があれば表示
                if "correct_example" in alert and alert.get("correct_example"):
                    lines.append(f"💡 {alert.get('correct_example')}")
                lines.append("-" * 40)

        lines.append("")
        lines.append("⛔ **安全のため自動実行を停止しました。**")
        lines.append("対応方針を選んでください:")
        lines.append("1) 正解の例を適用して続行")
        lines.append("2) 手動修正して続行")
        lines.append("3) 今回は無視して続行（推奨しません）")

        return "\n".join(lines)


# ---------------------------------------------------------
# 任意: 単体実行テスト
# ---------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    orchestra = KnowledgeOrchestra(base_dir="./knowledge_store")
    blocked, msg = orchestra.guard_before_finalize(
        relative_dir_path="analyzed_results",
        force_rebuild=False,
        latest_only=True,
    )

    if blocked:
        print("\n" + msg)
    else:
        print("✅ STOPガードは発動しませんでした。")
=======
# knowledge_orchestra.py
import logging
from api.services.manager.KnowledgeManager import KnowledgeManager
# from chat_handler import ChatHandler  # ユーザーにメッセージを送るクラス（想定）

logger = logging.getLogger(__name__)

class KnowledgeOrchestra:
    def __init__(self, base_dir="./knowledge_store"):
        self.KnowledgeManager = KnowledgeManager(base_dir)
        # self.chat_handler = ChatHandler()

    def process_latest_knowledge(self):
        """
        KnowledgeManagerを使って最新のJSONを読み込み、
        人間に助言（正解の例）を送る必要があるか判断する
        """
        logger.info("オーケストレータ: ナレッジの評価を開始します...")
        
        # 1. Managerを使って全JSONをロード
        knowledges = self.KnowledgeManager.load_all_json_from_dir("analyzed_results")

        for k in knowledges:
            content = k.get("content", {})
            human_advice = content.get("human_advice", {})
            
            # 2. 人間の確認が必要な場合 (REQUIRES_HUMAN_REVIEW)
            if human_advice.get("status") == "REQUIRES_HUMAN_REVIEW":
                self._notify_human(k.get("name"), human_advice)
            else:
                logger.info(f"{k.get('name')} は安全(SAFE)です。自動処理を継続します。")

    def _notify_human(self, project_name, advice_data):
        """
        ChatHandler経由で、人間にアラートと正解の例（修正案）を通知する
        """
        summary = advice_data.get("summary", "警告があります。")
        alerts = advice_data.get("alerts", [])

        # チャット用のメッセージを組み立てる
        chat_message = f"⚠️ **プロジェクト [{project_name}] に関する重要なお知らせ**\n\n{summary}\n\n"
        
        for alert in alerts:
            chat_message += f"**[{alert['level']}] {alert['analyzer']} より:**\n"
            chat_message += f"{alert['message']}\n"
            
            # ★ ここで「正解の例」をチャットに付与する
            if "correct_example" in alert:
                chat_message += f"\n💡 {alert['correct_example']}\n"
            
            chat_message += "-" * 40 + "\n"

        chat_message += "\nどう対応しますか？ (例: '正解の例をそのまま適用して', '無視して続行して')"

        # 3. ChatHandlerに渡してユーザーに送信（未実装の場合はprintで代用）
        # self.chat_handler.send_message(chat_message)
        print("\n" + chat_message)

# 実行テスト用
if __name__ == "__main__":
    orchestra = KnowledgeOrchestra()
    orchestra.process_latest_knowledge()
>>>>>>> 5d792e5e62f131b04c45504a321405bdd0a8bb17
