# api/services/handlers/ChatHandler/Chathandler.py
"""ChatHandler 本体（窓口）。

ここには「処理の流れ」だけを置く。個々の処理は同フォルダーの
各モジュールに分けてある。

依存の向き:
    constants / request_utils / mode_switch ...  →  Chathandler.py
    （サブモジュールから Chathandler.py を import しないこと）

ターンの流れ:
    Message → Signals → State復元 → Mode → (モード切替だけなら終了)
    → ContextResolver → Intent → RequirementAnalyzer
    → KnowledgeRouter → TopicTracker → User履歴保存
    → Build判定 → Knowledge応答 → chatbot応答 → AI応答 → LLM不可

重要:
    「アプリを作りたい」だけではBuildしない（要件相談）。
    「じゃあ作って」等の明示命令で初めて ProjectBuildService へ移行する。
    Requirement更新 → ユーザー履歴保存 → Build判定 の順序は変えないこと。

※ ts_ai の「Alignment検証」「未解決タスクのプール化」の概念を統合済み。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from api.services.conversation.ContextResolver import ContextResolver
from api.services.conversation.ConversationState import ConversationState
from api.services.conversation.ConversationSummary import ConversationSummary
from api.services.conversation.ResponseComposer import ResponseComposer
from api.services.conversation.TopicTracker import TopicTracker
from api.services.handlers.base_handler import BaseHandler
from api.services.project_generation.RequirementAnalyzer import (
    RequirementAnalyzer,
)
from api.services.handlers.VSCode.VSCodeHandler import VSCodePreResponder
from . import optional_deps
from .compat import accepts_kwarg
from .constants import (
    AI_MODE,
    CHATBOT_MODE,
    DEFAULT_SCORE,
    PROJECT_BUILDER_POLICIES,
    HANDLER_NAME,
)
from .conversation_adapters import (
    build_summary,
    resolve_context,
    track_topic,
)
from .knowledge_access import KnowledgeAccess
from .knowledge_filter import has_knowledge_channel, split_knowledge
from .llm_bridge import generate_with_local_llm
from .mode_switch import extract_requested_mode, mode_switch_response
from .project_flow.context import (
    get_project_context,
    has_project_context,
    update_project_context,
)
from .request_utils import (
    analysis_from_request_or_signals,
    compact_json,
    extract_message,
    extract_preloaded_knowledge,
    extract_signals,
)
from .responders import (
    AiChatResponder,
    BuildResponder,
    ChatbotResponder,
    KnowledgeResponder,
    LlmUnavailableResponder,
    ProjectConversationResponder,
    Responder,
)
from .result_builder import ResultBuilder
from .scoring import calculate_chat_score
from .state_restore import restore_state
from .turn_context import TurnContext

logger = logging.getLogger(__name__)


def _try_init(factory, name: str):
    if factory is None:
        return None
    try:
        return factory()
    except Exception as exc:
        logger.warning("%s initialization failed: %s", name, exc)
        return None


class ChatHandler(BaseHandler):
    """雑談・Knowledge応答・Conversation管理・アプリ要件収集を担当。"""

    HANDLER_NAME = HANDLER_NAME
    CHATBOT_MODE = CHATBOT_MODE
    AI_MODE = AI_MODE
    DEFAULT_SCORE = DEFAULT_SCORE

    # ========================================================
    # Init
    # ========================================================

    def __init__(
        self,
        knowledge_dir: str = "knowledge",
        default_mode: str = AI_MODE,
        knowledge_threshold: int = 1,
        knowledge_top_k: Optional[int] = 5,
        enable_debug: bool = True,
        project_builder_policy: str = "delegate",
        build_delegate: Optional[Any] = None,
        build_clean_existing: bool = True,
        fallback_generate: Optional[Callable[..., Optional[str]]] = None,
    ) -> None:
        """
        project_builder_policy:
            "delegate": mode=project_builder の発話は ProjectBuilderHandler へ
            "chat"    : ChatHandler が要件相談として引き受ける
        build_delegate:
            build_project(request, project_context, message) を持つオブジェクト
            （ProjectBuilderHandler）。渡すとBuildの設定・実行をそちらに一本化し、
            自前の ProjectBuildService は作らない。
        fallback_generate:
            Ollama等のローカルLLMが利用できない場合に呼び出す自作代替関数。
        """

        super().__init__()

        self.enable_debug = enable_debug
        self.fallback_generate = fallback_generate

        if project_builder_policy not in PROJECT_BUILDER_POLICIES:
            logger.warning(
                "unknown project_builder_policy=%r; using 'delegate'",
                project_builder_policy,
            )
            project_builder_policy = "delegate"

        self.project_builder_policy = project_builder_policy

        if default_mode not in (CHATBOT_MODE, AI_MODE):
            default_mode = AI_MODE

        self.default_mode = default_mode

        # Knowledge
        self.knowledge_dir = Path(knowledge_dir)

        self.knowledge = KnowledgeAccess(
            knowledge_dir=self.knowledge_dir,
            threshold=knowledge_threshold,
            top_k=knowledge_top_k,
            debug=self._debug,
        )
        self.knowledge_router = self.knowledge.router
        self.knowledge_loader = self.knowledge.loader

        # Conversation
        self.topic_tracker = TopicTracker()
        self.context_resolver = ContextResolver()
        self.conversation_summary = ConversationSummary()
        self.response_composer = ResponseComposer()

        # Requirement
        self.requirement_analyzer = RequirementAnalyzer()

        # LLM
        self.prompt_builder = _try_init(
            optional_deps.PromptBuilder, "PromptBuilder"
        )
        self.local_llm = _try_init(
            optional_deps.LocalLLMEngine, "LocalLLMEngine"
        )

        # Project Build Service（可能なら同じLLM Engineを共有）
        self.project_build_service = None

        # Build委譲先（ProjectBuilderHandler.build_project）
        self.build_delegate = None
        self.build_clean_existing = bool(build_clean_existing)

        if build_delegate is not None:
            if callable(getattr(build_delegate, "build_project", None)):
                self.build_delegate = build_delegate
            else:
                logger.warning(
                    "build_delegate に build_project() がありません。"
                    "自前の ProjectBuildService を使います。"
                )

        build_cls = optional_deps.ProjectBuildService

        if self.build_delegate is None and build_cls is not None:
            try:
                # 同じLLM Engineを共有できる場合だけ渡す（旧constructor互換）
                build_kwargs = (
                    {"llm_engine": self.local_llm}
                    if accepts_kwarg(build_cls, "llm_engine")
                    else {}
                )
                self.project_build_service = build_cls(**build_kwargs)
            except Exception as exc:
                logger.warning(
                    "ProjectBuildService initialization failed: %s",
                    exc,
                )

        # Result
        self.results = ResultBuilder(
            debug=self._debug,
            enable_debug=self.enable_debug,
        )

        # Responders（先に条件が合ったものが勝つ）
        generate = self._generate_with_local_llm
        
        # Buildは本物のローカルLLMがある時のみ有効
        real_llm_available = lambda: self.local_llm is not None  # noqa: E731
        # チャット・Knowledge応答は、本物のLLMまたは自作フォールバックがあれば有効とみなす
        chat_llm_available = lambda: (  # noqa: E731
            self.local_llm is not None or self.fallback_generate is not None
        )

        # Build判定は Knowledge読込・Summary生成より前に行う
        self.pre_responders: List[Responder] = [
            VSCodePreResponder(),
            BuildResponder(
                results=self.results,
                debug=self._debug,
                get_build_service=lambda: self.project_build_service,
                get_build_delegate=lambda: self.build_delegate,
                llm_available=real_llm_available,
                clean_existing=self.build_clean_existing,
            ),
        ]

        # KnowledgeResponderが extra_kwargs として fallback_generate を受け取れる場合は渡す
        knowledge_kwargs: Dict[str, Any] = {}
        if accepts_kwarg(KnowledgeResponder, "fallback_generate"):
            knowledge_kwargs["fallback_generate"] = self.fallback_generate

        self.responders: List[Responder] = [
            ProjectConversationResponder(
                self.results, generate, chat_llm_available
            ),
            KnowledgeResponder(
                self.results,
                self.response_composer,
                generate,
                chat_llm_available,
                self._debug,
                **knowledge_kwargs,
            ),
            ChatbotResponder(self.results),
            AiChatResponder(self.results, generate),
            LlmUnavailableResponder(self.results),  # 必ず最後
        ]

        self._debug(
            "initialized "
            f"default_mode={self.default_mode}, "
            f"project_build={self.project_build_service is not None}, "
            f"fallback_llm={self.fallback_generate is not None}"
        )

    # ========================================================
    # Debug
    # ========================================================

    def _debug(self, message: str) -> None:

        logger.debug("[%s] %s", self.HANDLER_NAME, message)

        # 移行期間: enable_debug=True の間は従来どおりコンソールにも出す。
        # logging設定が整ったら enable_debug=False にして print を削除する。
        if self.enable_debug:
            print(f"💬 [{self.HANDLER_NAME}] {message}", flush=True)

    # ========================================================
    # Handler Score
    # ========================================================

    async def calculate_score(
        self,
        message: str,
        current_signals: Optional[dict] = None,
    ) -> int:
        """司令塔(IntentInspector)が決めたモードに従う。詳細は scoring.py。"""

        if not self.enabled:
            return 0

        return calculate_chat_score(
            message,
            current_signals,
            default_score=self.DEFAULT_SCORE,
            debug=self._debug,
            project_builder_policy=self.project_builder_policy,
        )

    def estimate_size(self, message: str) -> int:
        return 1600

    # ========================================================
    # LLM wrapper（self.local_llm の差し替えと fallback に追従）
    # ========================================================

    def _generate_with_local_llm(
        self,
        user_message: str,
        analysis: Dict[str, Any],
        state: ConversationState,
        summary: Dict[str, Any],
        knowledge_data: Optional[List[Any]] = None,
    ) -> Optional[str]:

        response: Optional[str] = None

        # 1. ローカルLLM（Ollama等）が利用可能なら生成を試みる
        if self.local_llm is not None:
            response = generate_with_local_llm(
                local_llm=self.local_llm,
                prompt_builder=self.prompt_builder,
                user_message=user_message,
                analysis=analysis,
                state=state,
                summary=summary,
                knowledge_data=knowledge_data,
                debug=self._debug,
            )

        # 2. 生成できなかった場合、自作フォールバック関数（ダジャレ等）があれば呼び出す
        if not response and self.fallback_generate is not None:
            self._debug("Local LLM unavailable or empty; invoking fallback_generate.")
            try:
                response = self.fallback_generate(
                    user_message=user_message,
                    analysis=analysis,
                    state=state,
                    summary=summary,
                    knowledge_data=knowledge_data,
                )
            except Exception as exc:
                self._debug(f"fallback_generate failed: {exc}")
                response = None

        return response

    # ========================================================
    # Main
    # ========================================================

    async def handle(self, request) -> Tuple[str, Any]:

        early, ctx = self._prepare_turn(request)

        if early is not None:
            return early

        assert ctx is not None

        for responder in self.pre_responders:
            result = await responder.try_respond(ctx)

            if result is not None:
                # BuildResponderなどの出力に対する自己検証 (Alignment)
                return self._apply_alignment_check(ctx, result)

        self._enrich_turn(ctx)

        for responder in self.responders:
            result = await responder.try_respond(ctx)

            if result is not None:
                self._debug(f"responded by {responder.name}")

                # 回答できた場合、過去の未解決キューをチェックして消化する (UnresolvedQuestion)
                self._resolve_pending_queries(ctx, result)

                # アライメント検証・齟齬ログの適用 (Alignment Layer)
                return self._apply_alignment_check(ctx, result)

        # 全Responderが失敗した場合（通常 LlmUnavailableResponder でカバーされるが念のため）
        # ここに到達した場合は「未解決」としてキューに追加する (UnresolvedQuestion)
        self._add_to_unresolved(ctx, ctx.message)

        return self.results.simple(
            message="現在、適切な応答を生成できません。未解決リストに登録し、後ほど再確認します。",
            source="system",
            state=ctx.state,
        )

    # ========================================================
    # ts_ai 移植概念: Alignment & Unresolved Tasks
    # ========================================================

    def _apply_alignment_check(
        self, ctx: TurnContext, result: Tuple[str, Any]
    ) -> Tuple[str, Any]:
        """
        ts_aiの `alignment_layer` / `discrepancy_log` の概念。
        生成された回答がユーザーの要件(project_context)や文脈に違反していないか検証する。
        """
        message, meta = result

        # NOTE: 簡易的なアライメント検証ロジック
        # 実際にはここでLLMを用いた自己検証や、ルールベースの要件チェックを呼び出す
        discrepancy_detected = False
        discrepancy_details = ""

        # 例: 「Pythonで書いて」とproject_contextにあるのに、出力がTypeScriptである等
        # if "Python" in str(ctx.project_context) and "```typescript" in message:
        #     discrepancy_detected = True
        #     discrepancy_details = "言語指定と生成されたコードに齟齬があります"

        if discrepancy_detected:
            self._debug(f"Alignment Warning: {discrepancy_details}")
            # メタデータに齟齬情報を追加（ダッシュボード側で警告・ログ表示するため）
            if isinstance(meta, dict) and "extra" in meta:
                if "alignment_warnings" not in meta["extra"]:
                    meta["extra"]["alignment_warnings"] = []
                meta["extra"]["alignment_warnings"].append(discrepancy_details)

        return message, meta

    def _resolve_pending_queries(
        self, ctx: TurnContext, result: Tuple[str, Any]
    ) -> None:
        """
        ts_aiの `UnresolvedQuestion` プーリング概念。
        今回回答できたことで、過去の未解決タスクが消化できたかをチェックする。
        """
        unresolved = getattr(ctx.state, "unresolved_queries", [])
        if not unresolved:
            return

        # NOTE: 実際の運用では、今回回答したトピックと未解決リストを突き合わせ、
        # 解決したものをリストから削除するロジックを入れる
        # resolved_items = check_resolved(result[0], unresolved)
        # for item in resolved_items: unresolved.remove(item)

        setattr(ctx.state, "unresolved_queries", unresolved)

    def _add_to_unresolved(self, ctx: TurnContext, message: str) -> None:
        """
        ts_aiの `UnresolvedQuestion` プーリング概念。
        回答できなかったり、処理がフォールバックした質問をStateに退避させ、次回以降に再解決を試みる。
        """
        unresolved = getattr(ctx.state, "unresolved_queries", [])
        if message not in unresolved:
            unresolved.append(message)
        setattr(ctx.state, "unresolved_queries", unresolved)
        self._debug(f"Added to unresolved queries: {message!r}")

    # ========================================================
    # Prepare（旧 STEP 1〜12）
    #
    # 戻り値: (早期終了の結果, TurnContext)
    # 順序は意味を持つ:
    #   Requirement更新 → User履歴保存 → Build判定
    # ========================================================

    def _prepare_turn(
        self,
        request,
    ) -> Tuple[Optional[Tuple[str, Any]], Optional[TurnContext]]:

        # STEP 1  Message
        message = extract_message(request)

        if not message.strip():
            state = ConversationState(mode=self.default_mode)
            return (
                self.results.simple(
                    message="メッセージが空です。",
                    source="system",
                    state=state,
                ),
                None,
            )

        self._debug(f"input={message!r}")

        # STEP 2  Signals
        current_signals = extract_signals(request)

        # STEP 3  Restore State
        state = restore_state(
            current_signals, self.default_mode, self._debug
        )

        self._debug(
            f"restored mode={state.mode}, topic={state.current_topic}"
        )

        # STEP 4  Mode
        requested_mode = extract_requested_mode(request, message)

        if requested_mode:
            state.set_mode(requested_mode)

        self._debug(
            f"requested chat_mode={getattr(request, 'chat_mode', None)!r}, "
            f"ai_mode={getattr(request, 'ai_mode', None)!r}, "
            f"resolved={requested_mode!r}"
        )

        # STEP 5  Mode Switch only
        mode_response = mode_switch_response(message)

        if mode_response:
            state.next_turn()
            state.update_intent("mode_change")

            state.add_user_message(
                content=message,
                intent="mode_change",
                topic=state.current_topic,
            )
            state.add_assistant_message(
                content=mode_response,
                source="system",
                intent="mode_change",
                topic=state.current_topic,
            )

            return (
                self.results.finalize(
                    message=mode_response,
                    source="system",
                    state=state,
                    current_signals=current_signals,
                    extra={"intent": "mode_change"},
                ),
                None,
            )

        # STEP 6  Context Resolver
        context_result = resolve_context(
            self.context_resolver, message, state, self._debug
        )

        resolved_message = str(
            context_result.get("resolved", message) or message
        )

        self._debug(
            f"context changed={context_result.get('changed')}, "
            f"resolved={resolved_message!r}"
        )

        # STEP 7  Intent（Orchestratorの結果を優先）
        analysis = analysis_from_request_or_signals(
            request=request,
            current_signals=current_signals,
            fallback_message=resolved_message,
            debug=self._debug,
        )

        intent = analysis.get("intent") or analysis.get("mode") or "unknown"

        state.update_intent(intent)
        self._debug(f"intent={intent}")

        # STEP 8  Requirement Analyzer（Build判定より先に実行）
        requirement_result = update_project_context(
            self.requirement_analyzer, resolved_message, state, self._debug
        )

        project_context = get_project_context(state)

        self._debug("project_context=" + compact_json(project_context))

        preloaded_knowledge = extract_preloaded_knowledge(request)

        # Orchestrator が Knowledge を管理している場合（空でも）は
        # 自前の Router / Loader を使わない。
        orchestrated = has_knowledge_channel(request)

        if orchestrated:
            self._debug(
                "using orchestrator knowledge count="
                f"{len(preloaded_knowledge)}"
            )

        # STEP 9  Knowledge Router
        if orchestrated:
            knowledge_paths: List[str] = []
        else:
            knowledge_paths = self.knowledge.extract_route_paths(
                self.knowledge.route(
                    message=resolved_message,
                    state=state,
                    analysis=analysis,
                )
            )

        self._debug(f"knowledge_paths={knowledge_paths}")

        # STEP 10  Topic
        topic_result = track_topic(
            self.topic_tracker,
            resolved_message,
            state,
            analysis,
            knowledge_paths,
            self._debug,
        )

        detected_topic = topic_result.get("topic")

        if detected_topic:
            state.update_topic(detected_topic)
            state.add_entity(detected_topic)

        # Project中なのにTopicが取れない場合の補完
        if not state.current_topic and has_project_context(project_context):
            state.update_topic("アプリ開発")

        self._debug(
            f"topic={state.current_topic}, "
            f"previous={state.previous_topic}"
        )

        # STEP 11  Active Knowledge
        state.update_active_knowledge(knowledge_paths)

        # STEP 12  User History
        state.next_turn()

        state.add_user_message(
            content=message,
            intent=intent,
            topic=state.current_topic,
        )

        # STEP 13  Unresolved Queries Check
        unresolved = getattr(state, "unresolved_queries", [])
        if unresolved:
            self._debug(f"Pending unresolved queries count: {len(unresolved)}")
            # TurnContextのextra情報に含めてLLMに伝えることも可能（必要に応じて拡張）

        return (
            None,
            TurnContext(
                message=message,
                resolved_message=resolved_message,
                current_signals=current_signals,
                state=state,
                analysis=analysis,
                intent=intent,
                project_context=project_context,
                requirement_result=requirement_result,
                context_result=context_result,
                topic_result=topic_result,
                knowledge_paths=knowledge_paths,
                preloaded_knowledge=preloaded_knowledge,
                request=request,
                orchestrated_knowledge=orchestrated,
            ),
        )

    # ========================================================
    # Enrich（旧 STEP 14〜15）: Build判定の後に実行
    # ========================================================

    def _enrich_turn(self, ctx: TurnContext) -> None:

        items = (
            ctx.preloaded_knowledge
            if ctx.orchestrated_knowledge
            else self.knowledge.load(ctx.knowledge_paths)
        )

        # system文脈（health / progress）は「Knowledgeがある」に数えない
        ctx.loaded_knowledge, ctx.system_context = split_knowledge(items)

        self._debug(
            f"loaded knowledge count={len(ctx.loaded_knowledge)} "
            f"(system_context={len(ctx.system_context)})"
        )

        ctx.summary = build_summary(
            self.conversation_summary, ctx.state, self._debug
        )
        ctx.state.update_summary(ctx.summary)