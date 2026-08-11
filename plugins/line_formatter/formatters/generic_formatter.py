# plugins/line_formatter/formatters/generic_formatter.py
import re
from .base_formatter import BaseFormatter


class GenericFormatter(BaseFormatter):
    name = "generic"

    async def calculate_score(self, message: str) -> int:
        # 他のFormatterが取れなかった場合の保険なので常に低スコアで待機
        return 10

    async def format(self, message: str) -> str:
        # カンマ・句読点・接続助詞あたりで緩やかに改行する程度の保守的な整形
        text = message.strip()
        text = re.sub(r"([。、,])\s*", r"\1\n", text)
        return text.strip()