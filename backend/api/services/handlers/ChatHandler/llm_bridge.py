# api/services/handlers/ChatHandler/llm_bridge.py
# -*- coding: utf-8 -*-
"""
ChatHandler / 専門Handler（GagHandler等） → 共有LocalLLMEngine接続ブリッジ。

責務:
    1. AI機能が有効か確認する
    2. PromptBuilder（または専門Handlerのシステム指示）を使ってメッセージを構築する
    3. LocalLLMEngine.chat() による生成を試みる
    4. chat()が利用できない・失敗した場合にgenerate()を試みる
    5. 生成結果の成功状態・本文を検証する
    6. エラーとデバッグ情報を適切に処理する

責務に含めないもの:
    - LLM本体やGGUFモデルの初期化
    - Handler固有の品質評価
    - Handler固有のプロンプトの重複実装
    - 外部APIや別のLLMプロバイダーの独自初期化
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from api.services.conversation.ConversationState import ConversationState
logger = logging.getLogger(__name__)

DebugCallback = Optional[Callable[[str], None]]


def _debug(debug: DebugCallback, message: str) -> None:
    """デバッグ出力の失敗で本来の処理を止めない。"""
    if debug is None:
        return

    try:
        debug(message)
    except Exception:
        logger.debug("LLM bridge debug callback failed.", exc_info=True)


def _extract_generated_text(result: Any) -> Optional[str]:
    """
    Engineの戻り値から、成功した生成本文だけを取り出す。

    対応:
        - str
        - success / text 属性を持つ結果オブジェクト
        - dict (text / content / response キー)
    """
    if result is None:
        return None

    if isinstance(result, str):
        text = result.strip()
        return text or None

    if isinstance(result, dict):
        if result.get("success") is False:
            return None
        for key in ("text", "content", "response", " message"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None

    # GenerationResultなど、successを持つ戻り値を検証する。
    success = getattr(result, "success", None)

    if success is False:
        return None

    generated_text = getattr(result, "text", None)

    if not isinstance(generated_text, str):
        return None

    generated_text = generated_text.strip()

    if not generated_text:
        return None

    return generated_text


def _set_state_error(
    state: ConversationState,
    error_message: str,
) -> None:
    """
    ConversationStateのエラー設定を安全に試みる。
    """
    set_error = getattr(state, "set_error", None)

    if not callable(set_error):
        return

    try:
        set_error(error_message)
    except Exception:
        logger.debug(
            "Could not update ConversationState error.",
            exc_info=True,
        )


def _build_chat_messages(
    *,
    prompt_builder: Any,
    user_message: str,
    analysis: Dict[str, Any],
    state: ConversationState,
    summary: Dict[str, Any],
    knowledge_data: Optional[List[Any]],
    custom_system_prompt: Optional[str] = None,
) -> Optional[Any]:
    """
    共通PromptBuilderを使ってチャットメッセージを構築する。
    専門Handlerから custom_system_prompt が指定されている場合は、
    雑談用プロンプトと混ざらないよう直接 messages リストを構築して chat() に渡す。
    """
    if custom_system_prompt:
        return [
            {"role": "system", "content": custom_system_prompt.strip()},
            {"role": "user", "content": user_message.strip()},
        ]

    if prompt_builder is None:
        return None

    build_messages = getattr(
        prompt_builder,
        "build_chat_messages",
        None,
    )

    if not callable(build_messages):
        return None

    messages = build_messages(
        user_message=user_message,
        state=state,
        analysis=analysis,
        summary=summary,
        knowledge_data=list(knowledge_data or []),
    )

    if not messages:
        return None

    return messages


def _try_chat(
    *,
    local_llm: Any,
    messages: Any,
    debug: DebugCallback,
    temperature: float = 0.3,
    max_tokens: int = 1200,
) -> Optional[str]:
    """PromptBuilder（または専門指示）とchat()を使って生成する。"""
    chat = getattr(local_llm, "chat", None)

    if not callable(chat):
        _debug(debug, "LocalLLMEngine.chat() is unavailable.")
        return None

    try:
        result = chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        generated_text = _extract_generated_text(result)

        if generated_text is None:
            _debug(
                debug,
                "LocalLLMEngine.chat() returned no valid generated text.",
            )
            return None

        _debug(
            debug,
            "LocalLLMEngine.chat() generated a response.",
        )
        return generated_text

    except Exception as exc:
        _debug(
            debug,
            "LocalLLMEngine.chat() failed; "
            f"trying generate() if available: {exc}",
        )

        logger.warning(
            "LocalLLMEngine.chat() failed.",
            exc_info=True,
        )

        return None


def _try_generate(
    *,
    local_llm: Any,
    prompt: str,
    debug: DebugCallback,
) -> Optional[str]:
    """
    旧generate(prompt)方式で生成する。
    """
    generate = getattr(local_llm, "generate", None)

    if not callable(generate):
        _debug(debug, "LocalLLMEngine.generate() is unavailable.")
        return None

    try:
        result = generate(prompt)

        generated_text = _extract_generated_text(result)

        if generated_text is None:
            _debug(
                debug,
                "LocalLLMEngine.generate() returned no valid generated text.",
            )
            return None

        _debug(
            debug,
            "LocalLLMEngine.generate() generated a response.",
        )
        return generated_text

    except Exception as exc:
        logger.warning(
            "LocalLLMEngine.generate() failed.",
            exc_info=True,
        )

        _debug(debug, f"LocalLLMEngine.generate() failed: {exc}")

        return None


def generate_with_local_llm(
    *,
    local_llm: Any,
    prompt_builder: Any,
    user_message: str,
    analysis: Dict[str, Any],
    state: ConversationState,
    summary: Dict[str, Any],
    knowledge_data: Optional[List[Any]] = None,
    debug: DebugCallback = None,
    custom_system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1200,
) -> Optional[str]:
    """
    共有LocalLLMEngineを使って回答を生成する。

    呼び出し元:
        - ChatHandler._generate_with_local_llm()
        - GagHandler (generator.py) などの専門ハンドラー

    引数 custom_system_prompt:
        GagHandler 等が独自のプロンプト指示を渡す場合に使用する。
        指定時は雑談用の build_legacy_prompt による上書きをスキップし、
        流暢でブレのない専門応答を生成する。
    """

    # --------------------------------------------------------
    # 1. 入力・利用条件の確認
    # --------------------------------------------------------

    if not getattr(state, "ai_enabled", False):
        _debug(debug, "AI generation skipped: AI is disabled.")
        return None

    if local_llm is None:
        _debug(debug, "AI generation skipped: LocalLLMEngine is unavailable.")
        return None

    if not isinstance(user_message, str) or not user_message.strip():
        _debug(debug, "AI generation skipped: user_message is empty.")
        return None

    analysis = analysis if isinstance(analysis, dict) else {}
    summary = summary if isinstance(summary, dict) else {}

    # --------------------------------------------------------
    # 2. 共通PromptBuilder (または custom_system_prompt) + chat()
    # --------------------------------------------------------

    messages = None

    try:
        messages = _build_chat_messages(
            prompt_builder=prompt_builder,
            user_message=user_message,
            analysis=analysis,
            state=state,
            summary=summary,
            knowledge_data=knowledge_data,
            custom_system_prompt=custom_system_prompt,
        )

    except Exception as exc:
        logger.warning(
            "PromptBuilder.build_chat_messages() failed.",
            exc_info=True,
        )

        _debug(
            debug,
            "PromptBuilder failed; trying legacy prompt: "
            f"{exc}",
        )

    if messages is not None:
        response = _try_chat(
            local_llm=local_llm,
            messages=messages,
            debug=debug,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if response is not None:
            return response

    else:
        _debug(
            debug,
            "PromptBuilder messages unavailable; "
            "using legacy prompt path.",
        )

    # --------------------------------------------------------
    # 3. フォールバック用プロンプトを構築
    # --------------------------------------------------------

    if custom_system_prompt:
        # 専門Handlerの場合は、雑談用の build_legacy_prompt で汚染せず結合する
        prompt = f"{custom_system_prompt.strip()}\n\n{user_message.strip()}"
    

    if not isinstance(prompt, str) or not prompt.strip():
        _debug(debug, "Legacy prompt is empty or invalid.")
        return None

    # --------------------------------------------------------
    # 4. generate(prompt)で再試行
    # --------------------------------------------------------

    response = _try_generate(
        local_llm=local_llm,
        prompt=prompt,
        debug=debug,
    )

    if response is not None:
        return response

    # --------------------------------------------------------
    # 5. すべて失敗した場合
    # --------------------------------------------------------

    _set_state_error(
        state,
        "local_llm_generation_failed: "
        "chat and generate returned no valid response",
    )

    _debug(
        debug,
        "LocalLLM generation failed through all available paths.",
    )

    return None