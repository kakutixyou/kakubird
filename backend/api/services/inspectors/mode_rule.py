import re
from typing import Any, Dict, List, Type


class BaseModeRule:
    def __init__(self, mode_name: str, config: Dict[str, Any]):
        self.mode_name = mode_name
        self.config = config

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        return False

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        return 0


class GenericModeRule(BaseModeRule):
    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        match_cfg = self.config.get("match", {})

        expected_types = match_cfg.get("message_type", [])
        if expected_types and context.get("message_type") in expected_types:
            return True

        if any(a in detected_actions for a in match_cfg.get("actions", [])):
            return True

        target_keys = context.get("target_categories", [])
        if any(t in detected_targets for t in match_cfg.get("targets", [])):
            return True
        if any(t in target_keys for t in match_cfg.get("target_categories", [])):
            return True

        if any(k.lower() in msg_lower for k in match_cfg.get("keywords", [])):
            return True

        return False

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        score_cfg = self.config.get("score", {})
        match_cfg = self.config.get("match", {})

        score = score_cfg.get("base", 0)

        if any(a in detected_actions for a in match_cfg.get("actions", [])):
            score += score_cfg.get("action_bonus", 0)

        if any(t in detected_targets for t in match_cfg.get("targets", [])):
            score += score_cfg.get("target_bonus", 0)

        target_keys = context.get("target_categories", [])
        if any(t in target_keys for t in match_cfg.get("target_categories", [])):
            score += score_cfg.get("target_category_bonus", score_cfg.get("target_bonus", 0))

        expected_types = match_cfg.get("message_type", [])
        if expected_types and context.get("message_type") in expected_types:
            score += score_cfg.get("type_bonus", 0)

        return score


class ScoringModeRule(BaseModeRule):
    """scoring.json のモード別セクションを参照する Python ルールの基底。"""

    def __init__(self, mode_name: str, scoring_config: Dict[str, Any]):
        super().__init__(mode_name, scoring_config.get(mode_name, {}))


class AuthorKnowledgeModeRule(ScoringModeRule):
    def __init__(self, scoring_config: Dict[str, Any]):
        super().__init__("save_author_knowledge", scoring_config)

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        is_author = any(w in msg_lower for w in ["作者", "開発者", "じぶん", "自分"])
        wants_save = any(
            w in msg_lower
            for w in ["正解例", "正解の例", "jsonとして残", "jsonで残", "保存"]
        )
        has_direct_phrase = "作者なんだけど" in msg_lower or re.search(
            r"残して[お起]きたい", msg_lower
        )
        return bool((is_author and wants_save) or has_direct_phrase)

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        return self.config.get("base_score", 100)


class ProjectBuilderModeRule(ScoringModeRule):
    def __init__(self, scoring_config: Dict[str, Any]):
        super().__init__("project_builder", scoring_config)

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        target_keys = context.get("target_categories", [])
        has_app_target = "app_target" in target_keys
        has_build_action = "build_app" in detected_actions
        has_direct_word = any(w in msg_lower for w in ["カレンダー", "todo", "アプリ"])
        return bool(has_app_target or has_build_action or has_direct_word)

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        score = self.config.get("base_score", 60)
        if any(w in msg_lower for w in ["カレンダー", "todo", "タスク"]):
            score += self.config.get("app_name_bonus", 40)
        return score


class UiDesignModeRule(ScoringModeRule):
    def __init__(self, scoring_config: Dict[str, Any]):
        super().__init__("ui_design", scoring_config)

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        ui_targets = {
            "hero",
            "gallery",
            "pricing",
            "card",
            "sidebar",
            "table",
            "header",
            "footer",
            "form",
            "button",
        }
        has_ui_target = any(t in detected_targets for t in ui_targets)
        has_ui_context = (
            context.get("theme")
            or context.get("surface")
            or context.get("responsive")
        )
        return bool(has_ui_target or has_ui_context)

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        score = 0
        score += len(detected_actions) * self.config.get("action_weight", 20)
        score += len(detected_targets) * self.config.get("target_weight", 10)
        if context.get("theme"):
            score += self.config.get("theme_bonus", 10)
        if context.get("surface"):
            score += self.config.get("surface_bonus", 10)
        if context.get("responsive"):
            score += self.config.get("responsive_bonus", 10)
        return score


class DeploymentModeRule(ScoringModeRule):
    def __init__(self, scoring_config: Dict[str, Any]):
        super().__init__("deployment", scoring_config)

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        deps = context.get("deployment_metrics", {})
        return bool(
            deps.get("intent_score", 0) > 0
            or deps.get("trigger_hits", 0) > 0
            or context.get("deployment_surface")
        )

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        deps = context.get("deployment_metrics", {})
        score = 0
        score += deps.get("intent_score", 0) * self.config.get("intent_weight", 20)
        score += deps.get("trigger_hits", 0) * self.config.get("trigger_weight", 15)
        score += deps.get("surface_hits", 0) * self.config.get("surface_weight", 10)
        score += deps.get("mood_hits", 0) * self.config.get("mood_weight", 5)
        named_themes = context.get("_KW_named_themes", {})

        if any(name.lower() in msg_lower for name in named_themes.keys()):
            score += self.config.get("named_theme_bonus", 40)
        if (
            deps.get("surface_hits", 0) > 0
            and deps.get("trigger_hits", 0) == 0
            and deps.get("intent_score", 0) <= 1
            and score < 60
        ):
            score = 20
        elif (
            deps.get("surface_hits", 0) == 0
            and deps.get("trigger_hits", 0) == 0
            and score < 60
        ):
            score = min(40, score)

        if deps.get("surface_hits", 0) > 0:
            score += self.config.get("surface_trigger_bonus", 20)
        if deps.get("trigger_hits", 0) > 0:
            score += self.config.get("surface_trigger_bonus", 20)
        return score


class LineFormatModeRule(ScoringModeRule):
    def __init__(self, scoring_config: Dict[str, Any]):
        super().__init__("line_format", scoring_config)

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        keywords = [
            "改行",
            "整形",
            "フォーマット",
            "1行",
            "折り返し",
            "正しい形",
            "全文",
            "整理したい",
            "書き直して",
            "きれいにして",
        ]
        return any(k in msg_lower for k in keywords)

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        return self.config.get("base_score", 85)


class LineBreakModeRule(ScoringModeRule):
    def __init__(self, scoring_config: Dict[str, Any]):
        super().__init__("line_break", scoring_config)

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        keywords = ["改行", "整形", "フォーマット", "1行", "折り返し"]
        return any(k in msg_lower for k in keywords)

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        return self.config.get("base_score", 85)


class DatabaseOperationModeRule(ScoringModeRule):
    def __init__(self, scoring_config: Dict[str, Any]):
        super().__init__("database_operation", scoring_config)

    def match(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> bool:
        db_words = ["データベース", "db", "求人", "保存済", "履歴"]
        has_db_target = any(t in detected_targets for t in db_words)
        has_db_word = any(w in msg_lower for w in ["データベース", "一覧", "求人データ"])
        return bool(has_db_target or has_db_word)

    def calculate_score(
        self,
        msg_lower: str,
        detected_actions: List[str],
        detected_targets: List[str],
        context: Dict[str, Any],
    ) -> int:
        score = self.config.get("base_score", 50)
        if "show" in detected_actions:
            score += self.config.get("action_show_bonus", 20)
        if any(
            t in detected_targets
            for t in ["データベース", "db", "求人", "保存済", "履歴"]
        ):
            score += self.config.get("target_db_bonus", 15)
        return score


PYTHON_MODE_RULES: Dict[str, Type[ScoringModeRule]] = {
    "save_author_knowledge": AuthorKnowledgeModeRule,
    "project_builder": ProjectBuilderModeRule,
    "ui_design": UiDesignModeRule,
    "deployment": DeploymentModeRule,
    "line_format": LineFormatModeRule,
    "line_break": LineBreakModeRule,
    "database_operation": DatabaseOperationModeRule,
}


def build_mode_rules(
    scoring_config: Dict[str, Any],
    mode_rules_config: Dict[str, Any],
    rule_order: List[str],
) -> List[BaseModeRule]:
    rules: List[BaseModeRule] = []
    for mode_name in rule_order:
        if mode_name in PYTHON_MODE_RULES:
            rules.append(PYTHON_MODE_RULES[mode_name](scoring_config))
        elif mode_name in mode_rules_config:
            rules.append(GenericModeRule(mode_name, mode_rules_config[mode_name]))
    return rules
