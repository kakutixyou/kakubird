from __future__ import annotations
from dataclasses import dataclass
# )
class PriorityEngine:
    def __init__(
        self,
        active_tags_weight: float = 2.0,
        status_weight: float = 3.0,
        priority_weight: float = 2.0,
        keyword_weight: float = 1.5,
    ) -> None:
        self.active_tags_weight = active_tags_weight
        self.status_weight = status_weight
        self.priority_weight = priority_weight
        self.keyword_weight = keyword_weight

def prioritize(
    self,
    tasks,
    current_focus: str = "",
    active_tags: list[str] | None = None,
    limit: int | None = None,
):
    """
    タスク一覧をスコアリングして優先順位順に返す。

    Returns:
        list[PrioritizedTask]
    """
    active_tags = active_tags or []
    tasks = list(tasks)

    results = []

    for task in tasks:
        scored = self._score_task(
            task=task,
            current_focus=current_focus,
            active_tags=active_tags,
        )
        results.append(scored)

    # スコアの高い順に並べる
    results.sort(key=lambda x: x.score, reverse=True)

    # 件数制限
    if limit is not None:
        results = results[:limit]

    return results


def get_next_task(
    self,
    tasks,
    current_focus: str = "",
    active_tags: list[str] | None = None,
):
    """
    最優先のタスクを 1 件返す。

    Returns:
        PrioritizedTask | None
    """
    ranked = self.prioritize(
        tasks=tasks,
        current_focus=current_focus,
        active_tags=active_tags,
        limit=1,
    )

    if not ranked:
        return None

    return ranked[0]
@dataclass
class PrioritizedTask:
    task: Task
    score: float
    reasons: list[str]

    def __lt__(self, other: Self) -> bool:
        return self.score < other.score

    # -------------------------------------------------
    # Main Methods
    # -------------------------------------------------

    def get_highest_priority_task(
        self,
        tasks: list[Task],
        current_focus: str,
        active_tags: list[str],
    ) -> Task | None:
        ranked = [
            self._score_task(task, current_focus, active_tags)
            for task in tasks
        ]
        ranked.sort(reverse=True)
        return ranked[0] if ranked else None

    # -------------------------------------------------
    # Scoring
    # -------------------------------------------------

    def _score_task(
        self,
        task: Task,
        current_focus: str,
        active_tags: list[str],
    ) -> PrioritizedTask:
        score = 0.0
        reasons: list[str] = []

        # 1. status
        if task.status == "doing":
            score += 10 * self.status_weight
            reasons.append("現在進行中のタスク")
        elif task.status == "todo":
            score += 5 * self.status_weight
            reasons.append("未着手タスク")
        elif task.status == "done":
            score -= 100
            reasons.append("完了済み")

        # 2. priority (1 が最優先)
        normalized_priority = max(1, min(task.priority, 5))
        priority_score = (6 - normalized_priority) * self.priority_weight
        score += priority_score
        reasons.append(f"priority={task.priority}")

        # 3. active tags
        if task.tags:
            overlap = set(task.tags) & set(active_tags)
            if overlap:
                tag_score = len(overlap) * self.active_tags_weight
                score += tag_score
                reasons.append(
                    f"タグ一致: {', '.join(sorted(overlap))}"
                )

        # 4. focus keyword match
        if current_focus:
            focus_lower = current_focus.lower()
            haystack = f"{task.title} {task.description}".lower()

            if focus_lower in haystack:
                score += 5 * self.keyword_weight
                reasons.append("現在の作業内容と一致")
            else:
                # 部分一致
                for word in focus_lower.split():
                    if len(word) >= 3 and word in haystack:
                        score += 1 * self.keyword_weight
                        reasons.append(f"キーワード一致: {word}")

        return PrioritizedTask(
            task=task,
            score=score,
            reasons=reasons,
        )