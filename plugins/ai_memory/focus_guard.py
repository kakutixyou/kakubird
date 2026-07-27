from __future__ import annotations

from anyio import current_time
from .models import Task, FocusDecision

class FocusGuard:
    def decide_focus(self, tasks: list[Task], user_message: str, active_tags: list[str]) -> FocusDecision:
        # doing が無い場合は最優先タスクを提示
        next_task = self.priority_engine.get_next_task(
            tasks=tasks,
            current_focus=user_message,
            active_tags=active_tags,
        )

        if next_task:
            if self._is_related(user_message, next_task.task):
                return FocusDecision( # type: ignore
                    should_redirect=False,
                    message="優先タスクに関連しています。",
                    suggested_task=next_task.task,
                )

            return FocusDecision(
                should_redirect=True,
                message=(
                    f"次に取り組むべきタスクは『{next_task.task.title}』です。"
                ),
                suggested_task=next_task.task,
            )

        return FocusDecision(
            should_redirect=False,
            message="現在、未完了タスクはありません。",
        )

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _find_doing_task(self, tasks: list[Task]) -> Task | None:
        for task in tasks:
            if task.status == "doing":
                return task
        return None

    def _is_related(self, text: str, task: Task) -> bool:
        text_lower = text.lower()
        target = f"{task.title} {task.description}".lower()

        # タイトル全体が含まれている
        if task.title.lower() in text_lower:
            return True

        # 単語レベルで一致
        for word in self._extract_keywords(task.title + " " + task.description):
            if word in text_lower:
                return True

        return False

    def _extract_keywords(self, text: str) -> list[str]:
        words = []

        for word in text.lower().replace("_", " ").split():
            word = word.strip()
            if len(word) >= 3:
                words.append(word)

        return list(dict.fromkeys(words))