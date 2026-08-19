"""
recruit_handler.py (Part 1)

役割
-------------------------------------------------------
・求人テキスト解析の入口
・URL取得
・スコア判定
・RecruitMemory保持
・UI生成用データ作成

Part2では handle() を実装します。
Part3では UI Builder を実装します。
"""

from __future__ import annotations

import re
import httpx
from typing import Any, Dict, Optional, Tuple

from .base_handler import BaseHandler
from plugins.recruit.evaluator import evaluate
from core.job_database import save_job_to_db


# ====
# RecruitMemory
# ====

class RecruitMemory:
    """
    直近の解析結果だけを保持する簡易メモリ。

    将来的には

        plugins/
            recruit/
                memory.py

    へ移動して
    OCRRecruitHandler と共有できるようにする。
    """

    last_result: Optional[dict] = None
    last_company: str = ""
    last_source: str = ""


# ====
# Recruit Handler
# ====

class RecruitHandler(BaseHandler):
    """
    求人票・求人URL・スカウトメール解析を担当。

    対応入力

        ・求人票テキスト
        ・求人URL
        ・スカウトメール
        ・求人についての質問

    Part2で handle() を実装する。
    """

    # 
    # 初期化
    # 

    def __init__(self):

        super().__init__()

        self.url_pattern = re.compile(
            r"(https?://[^\s]+)",
            re.IGNORECASE
        )

        self.job_keywords = [

            "募集要項",
            "仕事内容",
            "勤務地",
            "給与",
            "年収",
            "勤務時間",
            "休日",
            "福利厚生",
            "応募資格",
            "歓迎スキル",
            "歓迎経験",
            "残業",
            "エンジニア",
            "SES",
            "客先常駐",

        ]

    # 
    # 判定
    # 

    async def can_handle(
        self,
        message: str
    ) -> bool:

        msg = message.lower()

        #
        # URL付き求人
        #

        if self.url_pattern.search(message):

            if "求人" in msg:
                return True

            if "評価" in msg:
                return True

        #
        # 求人解析依頼
        #

        keyword_count = sum(

            1
            for keyword in self.job_keywords
            if keyword in message

        )

        if keyword_count >= 2:
            return True

        #
        # 長文求人
        #

        if "求人" in msg and len(message) > 50:
            return True

        #
        # JSON化依頼
        #

        if "json" in msg and "求人" in msg:
            return True

        #
        # 保存依頼
        #

        if "保存" in msg and "求人" in msg:
            return True

        return False

    # 
    # スコア
    # 

    async def calculate_score(
        self,
        message: str,
        signals: dict
    ) -> int:

        score = 0
        msg = message.lower()

        #
        # 求人ワード
        #

        keyword_count = sum(

            1
            for keyword in self.job_keywords
            if keyword in message

        )

        score += keyword_count * 15

        #
        # URL
        #

        if self.url_pattern.search(message):
            score += 40

        #
        # JSON
        #

        if "json" in msg:
            score += 20

        #
        # 保存
        #

        if "保存" in msg:
            score += 15

        #
        # RecruitMemoryを利用中
        #

        if signals.get("last_used_handler") == "RecruitHandler":
            score += 10

        #
        # OCRから続いている
        #

        if signals.get("last_used_handler") == "OcrRecruitHandler":
            score += 10

        return score

    # 
    # URL取得
    # 

    async def _fetch_url(
        self,
        message: str
    ) -> str:

        """
        URL付きメッセージなら
        HTMLを取得して返す。
        """

        match = self.url_pattern.search(message)

        if not match:
            return message

        url = match.group(1)

        try:

            async with httpx.AsyncClient() as client:

                response = await client.get(
                    url,
                    timeout=15.0,
                    follow_redirects=True
                )

                response.raise_for_status()

                html = response.text[:5000]

                return (
                    f"URLの内容:\n"
                    f"{html}\n\n"
                    f"ユーザーメッセージ:\n"
                    f"{message}"
                )

        except Exception as e:

            print(f"Recruit URL Error : {e}")

            return message

    # 
    # 企業名抽出
    # 

    def _extract_company(
        self,
        evaluation_result: dict
    ) -> str:

        return (
            evaluation_result
            .get("company", {})
            .get("name", "該当企業")
        )

    # 
    # RecruitReportBlock用データ生成
    # 

    def _build_job_info(
        self,
        evaluation_result: dict
    ) -> Dict[str, Any]:

        company = evaluation_result.get("company", {})
        offer = evaluation_result.get("offer_summary", {})

        return {

            "company_name":
                company.get("name", ""),

            "industry":
                company.get("industry", ""),

            "location":
                company.get("location", ""),

            "headline":
                offer.get("headline", ""),

            "salary":
                offer.get("salary_range", {}),

            "work_style":
                offer.get("work_style", {}),

            "overall_label":
                evaluation_result.get(
                    "ai_analysis",
                    {}
                ).get(
                    "overall_label",
                    "gray"
                ),

        }

    async def handle(
        self,
        message: str
    ) -> Tuple[str, Any]:

        print("📝 RecruitHandler 起動")

        #
        # --------------------------------------------------
        # 保存だけ要求された場合
        # --------------------------------------------------
        #

        msg = message.lower()

        if (
            "保存" in msg
            and RecruitMemory.last_result is not None
        ):

            success = save_job_to_db(
                RecruitMemory.last_result
            )

            if success:

                return (
                    "text",
                    "💾 求人データをデータベースへ保存しました。"
                )

            return (
                "text",
                "❌ データベースへの保存に失敗しました。"
            )

        #
        # --------------------------------------------------
        # URL取得
        # --------------------------------------------------
        #

        target_text = await self._fetch_url(message)

        #
        # --------------------------------------------------
        # 求人解析
        # --------------------------------------------------
        #

        try:

            evaluation_result = evaluate(
                target_text
            )

        except Exception as e:

            print("Recruit Evaluate Error")
            print(e)

            return self._error_response(
                "求人情報の解析中にエラーが発生しました。"
            )

        #
        # evaluator保険
        #

        if not isinstance(
            evaluation_result,
            dict
        ):

            return self._error_response(
                "求人情報の解析に失敗しました。"
            )

        #
        # --------------------------------------------------
        # RecruitMemoryへ保存
        # --------------------------------------------------
        #

        RecruitMemory.last_result = evaluation_result

        RecruitMemory.last_company = (
            self._extract_company(
                evaluation_result
            )
        )

        RecruitMemory.last_source = target_text

        #
        # --------------------------------------------------
        # DB保存
        # --------------------------------------------------
        #

        db_saved = False

        try:

            db_saved = save_job_to_db(
                evaluation_result
            )

        except Exception as e:

            print("DB Save Error")
            print(e)

        #
        # --------------------------------------------------
        # RecruitReportBlock
        # --------------------------------------------------
        #

        job_info = self._build_job_info(
            evaluation_result
        )

        #
        # --------------------------------------------------
        # JsonViewerBlock
        # --------------------------------------------------
        #

        company_name = RecruitMemory.last_company

        #
        # --------------------------------------------------
        # ChatActionBlock
        # --------------------------------------------------
        #

        actions = self._build_action_buttons(
            company_name
        )

        #
        # --------------------------------------------------
        # メッセージ
        # --------------------------------------------------
        #

        if db_saved:

            message_text = (
                f"🤖 {company_name} の求人情報を解析しました。\n\n"
                "💾 データベースへ保存しました。"
            )

        else:

            message_text = (
                f"🤖 {company_name} の求人情報を解析しました。"
            )

        #
        # --------------------------------------------------
        # UI生成
        # --------------------------------------------------
        #

        content = {

            "message": message_text,

            "blocks": [

                {
                    "type": "RecruitReportBlock",
                    "props": {
                        "data": job_info
                    }
                },

                {
                    "type": "JsonViewerBlock",
                    "props": {
                        "title": "📊 AI解析JSON",
                        "data": evaluation_result
                    }
                },

                {
                    "type": "ChatActionBlock",
                    "props": {

                        "title": "次の一手",

                        "actions": actions

                    }
                }

            ]

        }

        #
        # --------------------------------------------------
        # UI返却
        # --------------------------------------------------
        #

        return (
            "ui_code",
            content
        )
        # 
    # Action Buttons
    # 

    def _build_action_buttons(
        self,
        company_name: str
    ) -> list:

        """
        ChatActionBlock用ボタン生成

        将来的には
        RecruitUIBuilderへ移動予定。
        """

        return [

            {
                "label": "志望動機を作成",
                "icon": "✉️",
                "next_prompt":
                    f"{company_name}への志望動機を作成して"
            },

            {
                "label": "懸念点を深掘り",
                "icon": "🚩",
                "next_prompt":
                    f"{company_name}の求人について詳しく分析して"
            },

            {
                "label": "保存済み求人一覧",
                "icon": "📂",
                "next_prompt":
                    "データベースに保存した求人一覧を表示して"
            },

            {
                "label": "求人JSONを表示",
                "icon": "📊",
                "next_prompt":
                    "この求人JSONをもう一度表示して"
            }

        ]


    # 
    # UI Builder
    # 

    def _build_ui(
        self,
        company_name: str,
        evaluation_result: dict,
        job_info: dict,
        actions: list,
        db_saved: bool
    ) -> dict:

        """
        Recruit画面全体を生成

        RecruitHandler
                ↓
            _build_ui()
                ↓
        RecruitReportBlock
        JsonViewerBlock
        ChatActionBlock
        """

        if db_saved:

            message = (
                f"🤖 {company_name} の求人を解析しました。\n\n"
                "💾 データベースへ保存済みです。"
            )

        else:

            message = (
                f"🤖 {company_name} の求人を解析しました。"
            )

        return {

            "message": message,

            "blocks": [

                {
                    "type": "RecruitReportBlock",

                    "props": {

                        "data": job_info

                    }
                },

                {
                    "type": "JsonViewerBlock",

                    "props": {

                        "title": "📊 AI解析JSON",

                        "data": evaluation_result

                    }

                },

                {
                    "type": "ChatActionBlock",

                    "props": {

                        "title": "次の一手",

                        "actions": actions

                    }

                }

            ]

        }


    # 
    # Success Response
    # 

    def _success_response(
        self,
        content: dict
    ) -> Tuple[str, Any]:

        """
        UIレスポンス生成

        将来的に

        RecruitHandler
        OCRRecruitHandler

        共通利用予定
        """

        return (

            "ui_code",

            content

        )


    # 
    # Error Response
    # 

    def _error_response(
        self,
        message: str
    ) -> Tuple[str, Any]:

        """
        エラー画面生成
        """

        return (

            "text",

            f"❌ {message}"

        )


    # 
    # 保存確認
    # 

    def _has_memory(self) -> bool:

        """
        RecruitMemoryに解析結果があるか
        """

        return RecruitMemory.last_result is not None


    # 
    # RecruitMemory取得
    # 

    def _get_last_result(self) -> Optional[dict]:

        """
        OCR側とも共通利用可能
        """

        return RecruitMemory.last_result
    # 
    # RecruitMemoryクリア
    # 

    def _clear_memory(self):

        """
        新しい求人解析前などで利用
        """

        RecruitMemory.last_result = None
        RecruitMemory.last_company = ""
        RecruitMemory.last_source = ""