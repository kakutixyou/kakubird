# core/config.py

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CUSTOM_API_KEY    = os.getenv("CUSTOM_API_KEY", "")