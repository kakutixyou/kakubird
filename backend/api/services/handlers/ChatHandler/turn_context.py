# api/services/handlers/ChatHandler/turn_context.py
"""1ターン分の情報をまとめる。

handle() の前半（準備）で作り、各Responderへそのまま渡す。
knowledge / summary はBuild判定の後で埋める（Build時は不要な処理を避けるため）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from api.services.conversation.ConversationState import ConversationState


@dataclass
class TurnContext:
    message: str
    resolved_message: str
    current_signals: Dict[str, Any]
    state: ConversationState
    analysis: Dict[str, Any]
    intent: str
    project_context: Dict[str, Any]
    requirement_result: Dict[str, Any]
    context_result: Dict[str, Any]
    topic_result: Dict[str, Any]
    knowledge_paths: List[str]
    preloaded_knowledge: List[Any]
    request: Any = None
    orchestrated_knowledge: bool = False

    # enrich 段階で埋まる
    loaded_knowledge: List[Any] = field(default_factory=list)  # 実Knowledgeのみ
    system_context: List[Any] = field(default_factory=list)    # health / progress
    summary: Dict[str, Any] = field(default_factory=dict)

    @property
    def llm_knowledge(self) -> List[Any]:
        """LLMへ渡す全文脈（実Knowledge + system文脈）。"""
        return [*self.loaded_knowledge, *self.system_context]

    def base_extra(self) -> Dict[str, Any]:
        """finalize の extra に共通で入れる項目。"""
        return {
            "intent": self.intent,
            "analysis": self.analysis,
            "project_context": self.project_context,
            "requirements": self.requirement_result,
            "context_resolution": self.context_result,
            "topic_tracking": self.topic_result,
            "summary": self.summary,
        }
