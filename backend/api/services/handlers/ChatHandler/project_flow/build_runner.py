# api/services/handlers/ChatHandler/project_flow/build_runner.py
"""ChatHandler から ProjectBuildService へ移行する唯一の入口。"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, Tuple, cast

from api.services.conversation.ConversationState import ConversationState

from ..compat import accepts_kwarg
from ..result_builder import ResultBuilder
from .context import get_project_context, has_project_context

logger = logging.getLogger(__name__)


def normalize_build_result(
    result: Any,
    project_context: Dict[str, Any],
) -> Dict[str, Any]:

    if hasattr(result, "to_dict"):
        try:
            result = result.to_dict()
        except Exception:
            pass

    build_data: Dict[str, Any]

    # ProjectBuilderHandler.build_project() の応答:
    #   {"message", "status", "project_name", "blocks": [{"type": "project_build", "data": {...}}]}
    if isinstance(result, dict) and isinstance(result.get("blocks"), list):
        for block in result["blocks"]:
            if (
                isinstance(block, dict)
                and block.get("type") == "project_build"
                and isinstance(block.get("data"), dict)
            ):
                result = block["data"]
                break

    if isinstance(result, dict):
        data = result.get("data")

        if isinstance(data, dict):
            build_data = dict(data)
        else:
            build_data = dict(result)

    else:
        build_data = {"status": "success", "message": str(result)}

    project_name = project_context.get("project_name") or "generated-app"

    build_data.setdefault("project_name", str(project_name))
    build_data.setdefault("status", "success")

    files_written = build_data.get("files_written")

    build_data.setdefault(
        "files_generated",
        files_written if isinstance(files_written, int) else 0,
    )

    build_data.setdefault("logs", [])

    return build_data


async def _execute_build(
    *,
    build_service: Any,
    build_delegate: Any,
    request: Any,
    message: str,
    project_context: Dict[str, Any],
    use_ai: bool,
    clean_existing: bool,
) -> Any:
    """Buildを実行する。同期のbuild()は別スレッドで動かす。"""

    # 1. ProjectBuilderHandler に任せる（設定・名前正規化を1か所に）
    if build_delegate is not None:
        return await build_delegate.build_project(
            request=request,
            project_context=project_context,
            message=message,
        )

    # 2. 自前の ProjectBuildService
    build = getattr(build_service, "build", None)

    if not callable(build):
        raise AttributeError("ProjectBuildService.build() がありません。")

    # 引数名が一致する時だけ渡す（不一致なら従来どおり既定値）
    kwargs: Dict[str, Any] = {}

    if accepts_kwarg(build, "use_ai"):
        kwargs["use_ai"] = use_ai

    if accepts_kwarg(build, "clean_existing"):
        kwargs["clean_existing"] = clean_existing

    if inspect.iscoroutinefunction(build):
        return await build(project_context, **kwargs)

    # 同期関数をイベントループ上で直接呼ぶと、ビルド中サーバー全体が止まる
    result = await asyncio.to_thread(build, project_context, **kwargs)

    if inspect.isawaitable(result):
        result = await cast(Awaitable[Any], result)

    return result


async def handle_project_build(
    *,
    build_service: Any,
    results: ResultBuilder,
    debug: Callable[[str], None],
    state: ConversationState,
    current_signals: Dict[str, Any],
    analysis: Dict[str, Any],
    requirement_result: Dict[str, Any],
    context_result: Dict[str, Any],
    topic_result: Dict[str, Any],
    build_delegate: Any = None,
    request: Any = None,
    message: str = "",
    use_ai: bool = False,
    clean_existing: bool = True,
) -> Tuple[str, Any]:

    project_context = get_project_context(state)

    # ----------------------------------------------------
    # Project context無し
    # ----------------------------------------------------

    if not has_project_context(project_context):

        response = (
            "アプリを生成するための要件が"
            "まだありません。"
            "まず、どのようなアプリを作るか"
            "教えてください。"
        )

        state.add_assistant_message(
            content=response,
            source="project_system",
            intent="project_build",
            topic=state.current_topic,
        )

        return results.finalize(
            message=response,
            source="project_system",
            state=state,
            current_signals=current_signals,
            extra={
                "intent": "project_build",
                "project_context": project_context,
            },
        )

    # ----------------------------------------------------
    # Build Service未接続
    # ----------------------------------------------------

    if build_service is None and build_delegate is None:

        response = (
            "アプリの要件は保持できています。"
            "ただしProjectBuildServiceが"
            "まだ接続されていないため、"
            "現時点では実ファイル生成を開始できません。"
        )

        state.set_error("project_build_service_unavailable")

        state.add_assistant_message(
            content=response,
            source="project_system",
            intent="project_build",
            topic=state.current_topic,
        )

        return results.finalize(
            message=response,
            source="project_system",
            state=state,
            current_signals=current_signals,
            extra={
                "intent": "project_build",
                "project_context": project_context,
                "project_build": {
                    "status": "unavailable",
                    "project_name": project_context.get("project_name"),
                    "message": response,
                },
                "blocks": [
                    {
                        "type": "project_build",
                        "data": {
                            "status": "error",
                            "project_name":
                                project_context.get("project_name"),
                            "message": response,
                            "files_generated": 0,
                        },
                    }
                ],
            },
        )

    # ----------------------------------------------------
    # Build
    # ----------------------------------------------------

    try:
        debug("ProjectBuildService started")

        result: Any = await _execute_build(
            build_service=build_service,
            build_delegate=build_delegate,
            request=request,
            message=message,
            project_context=project_context,
            use_ai=use_ai,
            clean_existing=clean_existing,
        )

    except Exception as exc:

        logger.exception("Project build failed")

        state.set_error(f"project_build_error: {exc}")

        response = "プロジェクト生成中にエラーが発生しました。"

        state.add_assistant_message(
            content=response,
            source="project_build",
            intent="project_build",
            topic=state.current_topic,
        )

        build_data = {
            "project_name":
                project_context.get("project_name") or "generated-app",
            "status": "error",
            "files_generated": 0,
            "message": str(exc),
        }

        return results.finalize_project_build(
            message=response,
            build_data=build_data,
            state=state,
            current_signals=current_signals,
            analysis=analysis,
            requirement_result=requirement_result,
            context_result=context_result,
            topic_result=topic_result,
        )

    # ----------------------------------------------------
    # Normalize
    # ----------------------------------------------------

    build_data = normalize_build_result(result, project_context)

    status = str(build_data.get("status", "success")).lower()

    if status in ("success", "completed", "complete"):

        response = (
            build_data.get("message")
            or (
                f"{build_data.get('project_name', 'アプリ')} "
                "の生成が完了しました。"
            )
        )

        state.clear_error()

    else:

        project_name = str(build_data.get("project_name") or "プロジェクト")
        build_message = str(build_data.get("message") or "").strip()
        errors = build_data.get("errors")

        error_messages = []

        if isinstance(errors, list):
            error_messages = [str(e) for e in errors if e]

        response = (
            f"{project_name} の生成を試みましたが、"
            "正常に完了できませんでした。"
        )

        if build_message:
            response += f"\n\n{build_message}"

        if error_messages:
            response += (
                "\n\n確認されたエラー:\n- "
                + "\n- ".join(error_messages[:3])
            )

        response += "\n\nアプリの要件は保持されています。"

        state.set_error("project_build_failed")

    state.add_assistant_message(
        content=str(response),
        source="project_build",
        intent="project_build",
        topic=state.current_topic,
    )

    return results.finalize_project_build(
        message=str(response),
        build_data=build_data,
        state=state,
        current_signals=current_signals,
        analysis=analysis,
        requirement_result=requirement_result,
        context_result=context_result,
        topic_result=topic_result,
    )
