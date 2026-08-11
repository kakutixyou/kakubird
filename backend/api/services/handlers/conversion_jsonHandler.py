# conversion_jsonHandler.py
from  api.services.inspectors.IntentInSpector import IntentInspector
import json
import re
import textwrap
import traceback
from typing import Any, Tuple

from .base_handler import BaseHandler

class ConversionJsonHandler(BaseHandler):
    """
    あらゆるテキストをJSONへ変換するHandler
    """

    async def can_handle(self, message: str) -> bool:
        # can_handle もインスペクターに委譲するか、簡易チェックを残すか選べますが、
        # ここでは最低限のキーワードチェックとして残しておきます。
        msg = message.lower()
        keywords = ["json", "json形式", "json化", "jsonに変換", "convert json", "to json"]
        return any(k in msg for k in keywords)

    async def calculate_score(self, message: str, signals=None) -> int:
        # 1. 絶対コマンドのチェック（もし将来 `/json` などのコマンドを作るならここが100点になる）
        if message.strip().startswith("/json"):
            return 100

        # 2. インスペクター（共通の審査員）に丸投げ
        inspector = IntentInspector(message)
        analysis = inspector.inspect()

        # 3. 自分が担当すべき「モード」のスコアだけを厳密に採用する
        if analysis["mode"] == "data_conversion":
            return analysis["score"]  # インスペクターが計算した安全なスコア（最大85点）

        # もし「json」という単語が含まれていても、UIデザインの文脈（例：「Timeline JSONの見た目を綺麗にして」等）
        # であれば、このハンドラーは身を引く（スコア0にする）
        return 0

    async def handle(self, message: str) -> Tuple[str, Any]:

        print("⚡ ConversionJsonHandler 起動")

        try:

            json_data = self.convert_text_to_json(message)

            return (
                "json_data",
                {
                    "message": "JSONへ変換しました。",
                    "json": json_data
                }
            )

        except Exception:

            traceback.print_exc()

            return (
                "text",
                "JSONへの変換中にエラーが発生しました。"
            )

    # ---------------------------------------------------

    def convert_text_to_json(self, message: str) -> dict:

        message = message.strip()

        wrapped = self.wrap_text(message)

        lines = [x.strip() for x in message.splitlines() if x.strip()]

        data = {}

        ####################################################
        # key:value 形式
        ####################################################

        for line in lines:

            if "：" in line:

                key, value = line.split("：", 1)

                data[key.strip()] = value.strip()

            elif ":" in line:

                key, value = line.split(":", 1)

                data[key.strip()] = value.strip()

            elif "=" in line:

                key, value = line.split("=", 1)

                data[key.strip()] = value.strip()

            elif "＝" in line:

                key, value = line.split("＝", 1)

                data[key.strip()] = value.strip()

            else:

                match = re.match(r"^(.+?)（(.+?)）$", line)

                if match:

                    data[match.group(1).strip()] = match.group(2).strip()

        ####################################################
        # key:valueが見つからない場合
        ####################################################

        if len(data) == 0:

            if len(lines) > 1:

                return {
                    "type": "list",
                    "count": len(lines),
                    "items": lines
                }

            return {
                "type": "text",
                "length": len(message),
                "wrapped_width": 45,
                "text": wrapped
            }

        ####################################################
        # key:value があった場合
        ####################################################

        return {
            "type": "object",
            "count": len(data),
            "wrapped_width": 45,
            "data": data
        }

    # ---------------------------------------------------

    def wrap_text(self, text: str, width: int = 45) -> str:

        return "\n".join(

            textwrap.wrap(
                text,
                width=width,
                break_long_words=True,
                break_on_hyphens=False
            )

        )

    # ---------------------------------------------------

    def estimate_size(self, message: str) -> int:

        return len(message)