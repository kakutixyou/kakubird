# jimdo_studio_react/backend/api/services/ollama_service.py

import os
import traceback
from typing import Dict, Any, List

import httpx
# ===
# Ollama Config
# ===

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",  # 🌟 "OLLAMA_BASE_URL" から変更
    "http://127.0.0.1:11434" # 🌟 デフォルトも 127.0.0.1 に変更
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "gemma3"
)
OLLAMA_TIMEOUT = float(
    os.getenv("OLLAMA_TIMEOUT", "240")
)


# ===
# Tool Definitions
# ===

def build_tool_definitions() -> List[Dict[str, Any]]:
    """
    Ollama Tool Calling 用のツール定義

    将来的には:
    - tool_registry
    - plugins
    - dynamic loading

    に置き換え可能。
    """

    return [
        {
            "type": "function",
            "function": {
                "name": "github_search",
                "description": (
                    "GitHubのオープンソースプロジェクトや"
                    "リポジトリを検索します。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "検索クエリ"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "weather_fetch",
                "description": (
                    "指定された都市の現在の天気や"
                    "週間予報を取得します。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "都市名"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    ]


# ===
# Payload Builder
# ===

def build_chat_payload(
    user_message: str,
    system_context: str,
    history: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    """
    Ollama API用 payload 構築

    history を後で追加可能な形にしておく。
    """

    messages = []

    # -----------------------------------------------------
    # System Prompt
    # -----------------------------------------------------
    messages.append({
        "role": "system",
        "content": system_context
    })

    # -----------------------------------------------------
    # History
    # -----------------------------------------------------
    if history:
        messages.extend(history)

    # -----------------------------------------------------
    # User Message
    # -----------------------------------------------------
    messages.append({
        "role": "user",
        "content": user_message
    })

    return {
        "model": OLLAMA_MODEL,
        "messages": messages,
        # "tools": build_tool_definitions(),
        "stream": False,
    }


# ===
# Main Chat Function
# ===

async def ask_ollama_with_tools(
    user_message: str,
    system_context: str,
    history: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    """
    Ollama Chat API 呼び出し

    Returns:
        Dict[str, Any]

    成功:
        Ollama APIレスポンス

    失敗:
        {
            "error": "offline"
        }
    """

    payload = build_chat_payload(
        user_message=user_message,
        system_context=system_context,
        history=history,
    )

    try:

        async with httpx.AsyncClient(
            timeout=OLLAMA_TIMEOUT
        ) as client:

            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )

            response.raise_for_status()

            return response.json()

    except httpx.ConnectError:

        print("❌ Ollama Connection Error")

        return {
            "error": "offline",
            "message": "Ollama server is offline"
        }

    except httpx.TimeoutException:

        print("❌ Ollama Timeout")

        return {
            "error": "timeout",
            "message": "Ollama request timeout"
        }

    except httpx.HTTPStatusError as e:

        print(f"❌ Ollama HTTP Error: {e}")

        return {
            "error": "http_error",
            "message": str(e)
        }

    except Exception as e:

        traceback.print_exc()

        return {
            "error": "unknown",
            "message": str(e)
        }


# ===
# Health Check
# ===

async def check_ollama_health() -> bool:
    """
    Ollamaサーバーの生存確認

    Returns:
        bool
    """

    try:

        async with httpx.AsyncClient(
            timeout=5.0
        ) as client:

            response = await client.get(
                f"{OLLAMA_BASE_URL}/api/tags"
            )

            response.raise_for_status()

            return True

    except Exception:

        return False


# ===
# Simple Chat (No Tools)
# ===

async def simple_ollama_chat(
    prompt: str,
    system_prompt: str = "あなたは優秀なAIアシスタントです。"
) -> str:
    """
    Tool Callingなしの簡易チャット

    軽量用途:
    - summarize
    - classify
    - title generation
    - internal helper
    """

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
    }

    try:

        async with httpx.AsyncClient(
            timeout=OLLAMA_TIMEOUT
        ) as client:

            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload
            )

            response.raise_for_status()

            data = response.json()

            return (
                data.get("message", {})
                .get("content", "")
            )

    except Exception:

        traceback.print_exc()

        return "AI応答生成中にエラーが発生しました。"


# ===
# Future Expansion Notes
# ===

"""
将来的な拡張ポイント:

1. Tool Registry
--------------------------------------------------------
tools = tool_registry.get_openai_schema()

2. Provider Abstraction
--------------------------------------------------------
class BaseLLMProvider:
    async def chat(...)

3. Streaming
--------------------------------------------------------
stream=True
async generator

4. Multi Model Routing
--------------------------------------------------------
if task == "coding":
    model = "deepseek-coder"

5. Memory Injection
--------------------------------------------------------
messages += memory_context

6. Vision Support
--------------------------------------------------------
images=[...]

7. Plugin Tool Exposure
--------------------------------------------------------
plugins → tool schema 自動生成

8. Agent Runtime
--------------------------------------------------------
tool loop
reasoning loop
planning loop

9. Retry / Circuit Breaker
--------------------------------------------------------
resilience layer

10. Observability
--------------------------------------------------------
logging
metrics
token tracking
"""

