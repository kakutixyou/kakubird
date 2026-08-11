# backend/core/config.py
# ちなみにctrl+shift+Fで調べるとSqlのpluginにも同じようなコードがあるぞ！
import os
from dotenv import load_dotenv
import anthropic
# from core.config import ANTHROPIC_API_KEY#無限ループを防ぐこと
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CUSTOM_API_KEY    = os.getenv("CUSTOM_API_KEY", "")