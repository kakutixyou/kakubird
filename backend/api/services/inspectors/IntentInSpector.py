# Intentinspector.py
import os
from typing import Any, Dict, List, Optional

from .detectors import (
    ForcedHandlerDetector,
    ActionDetector,
    TargetDetector,
    ThemeSurfaceDetector,
    DeploymentMetricDetector,
    load_json,
)

from .MessageTypeDetector import MessageTypeDetector
from .mode_rule import build_mode_rules

# =========================================================
# パス設定
# =========================================================

_DIR = os.path.dirname(__file__)
_KNOWLEDGE_DIR = os.path.join(_DIR, "knowledge")

# =========================================================
# JSONキャッシュ
# =========================================================

_INSPECTOR_CACHE: Dict[str, Any] = {}


class IntentInspector:

    """
    IntentInspector

    役割
    ----------------------------

    ・Detectorへ解析を依頼する
    ・Contextを構築する
    ・ModeRuleへ判定を依頼する

    自分では判定ロジックを持たない。
    """

    def __init__(
        self,
        message: Any,
        available_knowledge_keys: Optional[List[str]] = None,
    ):

        self.raw_message = message
        self.available_knowledge_keys = available_knowledge_keys or []

        if isinstance(message, str):
            self.message = message
        else:
            self.message = str(
                getattr(
                    message,
                    "text",
                    getattr(
                        message,
                        "content",
                        getattr(message, "body", message),
                    ),
                )
            )

        self.msg_lower = self.message.lower().strip()

        self._load_knowledge()

    # =========================================================
    # JSON読み込み
    # =========================================================

    def _load_knowledge(self):

        global _INSPECTOR_CACHE

        if not _INSPECTOR_CACHE:

            print(
                "📦 [IntentInspector] JSONをキャッシュします...",
                flush=True,
            )

            _INSPECTOR_CACHE["actions"] = load_json(
                os.path.join(_KNOWLEDGE_DIR, "actions.json")
            )

            _INSPECTOR_CACHE["targets"] = load_json(
                os.path.join(_KNOWLEDGE_DIR, "targets.json")
            )

            _INSPECTOR_CACHE["scoring"] = load_json(
                os.path.join(_KNOWLEDGE_DIR, "scoring.json")
            )

            _INSPECTOR_CACHE["mode_rules"] = load_json(
                os.path.join(_KNOWLEDGE_DIR, "mode_rules.json")
            )

            _INSPECTOR_CACHE["deployment_keywords"] = load_json(
                os.path.join(_DIR, "deployment_keywords.json")
            )

            _INSPECTOR_CACHE["deployment_themes"] = load_json(
                os.path.join(_DIR, "deployment_themes.json")
            )

        # ----------------------------
        # Detector
        # ----------------------------

        self.forced_detector = ForcedHandlerDetector()

        self.action_detector = ActionDetector(
            _INSPECTOR_CACHE["actions"]
        )

        self.target_detector = TargetDetector(
            _INSPECTOR_CACHE["targets"]
        )

        self.theme_detector = ThemeSurfaceDetector()

        self.deployment_detector = DeploymentMetricDetector(
            _INSPECTOR_CACHE["deployment_keywords"],
            _INSPECTOR_CACHE["deployment_themes"],
        )

        self.message_detector = MessageTypeDetector(self.message)

        # ----------------------------
        # Rule
        # ----------------------------

        self.mode_rules = build_mode_rules(
            _INSPECTOR_CACHE["scoring"],
            _INSPECTOR_CACHE["mode_rules"],
            list(_INSPECTOR_CACHE["mode_rules"].keys()),
        )

    # =========================================================
    # Context生成
    # =========================================================

    def _build_context(
        self,
        message_type: Dict[str, Any],
        ui_context: Dict[str, Any],
        deployment: Dict[str, Any],
        target_categories: List[str],
    ) -> Dict[str, Any]:

        context = {

            "message_type":
                message_type.get("type", "unknown"),

            "is_code":
                message_type.get("is_code", False),

            "has_html":
                message_type.get("has_html", False),

            "theme":
                ui_context.get("theme"),

            "surface":
                ui_context.get("surface"),

            "responsive":
                ui_context.get("responsive", False),

            "modify_existing":
                ui_context.get("modify_existing", False),

            "deployment_metrics":
                deployment.get("deployment_metrics", {}),

            "deployment_surface":
                deployment.get("deployment_surface"),

            "deployment_theme":
                deployment.get("deployment_theme"),

            "target_categories":
                target_categories,

            "_KW_named_themes":
                _INSPECTOR_CACHE["deployment_keywords"].get(
                    "named_themes",
                    {},
                ),
        }

        return context

    # =========================================================
    # Inspect
    # =========================================================

    def inspect(self) -> Dict[str, Any]:

        forced_handler = self.forced_detector.detect(
            self.message
        )

        message_type = self.message_detector.detect()

        actions = self.action_detector.detect(
            self.msg_lower
        )

        targets = self.target_detector.detect_words(
            self.msg_lower
        )

        target_categories = self.target_detector.detect_categories(
            self.msg_lower
        )

        ui_context = self.theme_detector.detect(
            self.msg_lower
        )

        deployment = self.deployment_detector.detect(
            self.msg_lower
        )

        context = self._build_context(
            message_type,
            ui_context,
            deployment,
            target_categories,
        )

        result = {

            "mode": "unknown",

            "score": 0,

            "forced_handler": forced_handler,

            "actions": actions,

            "targets": targets,

            "message_type_info": message_type,

            "available_knowledge":
                self.available_knowledge_keys,

            **ui_context,

            **deployment,
        }

        # ===== 第二回 =====
        # ・mode_ruleへ渡す
        # ・最高スコア決定
        # ・例外処理
        # ・resultへmodeとscoreを格納
        # ・return
            # =========================================================
        # Mode判定
        # =========================================================

        highest_score = 0
        best_mode = "unknown"

        for rule in self.mode_rules:

            if not rule.match(
                self.msg_lower,
                actions,
                targets,
                context,
            ):
                continue

            score = rule.calculate_score(
                self.msg_lower,
                actions,
                targets,
                context,
            )

            if score > highest_score:
                highest_score = score
                best_mode = rule.mode_name

        # =========================================================
        # Global Score Cap
        # =========================================================

        scoring = _INSPECTOR_CACHE.get("scoring", {})

        max_score = (
            scoring.get("global", {})
            .get("max_score_cap", 85)
        )

        highest_score = min(highest_score, max_score)

        # =========================================================
        # System Exception Rule
        # =========================================================

        #
        # 空箱を作らない
        #
        if (
            "空箱" in self.msg_lower
            and "作らない" in self.msg_lower
        ):
            best_mode = "unknown"
            highest_score = 0
         #js抽出   
        if (
        "script" in self.msg_lower 
        and ("js" in self.msg_lower or "抽出" in self.msg_lower or "読み取って" in self.msg_lower)
        ):
        # モードを強制的にJS抽出用に上書きし、スコアをMAX（100）にする
            best_mode = "script_extraction"  
            highest_score = 100
        
        # もし forced_handler（強制ハンドラー指定）で動かしている場合は以下も追加
            forced_handler = "DecompositionHandler"
        # =========================================================
        # Result
        # =========================================================

        result["mode"] = best_mode
        result["score"] = highest_score

        # =========================================================
        # Debug Log
        # =========================================================

        print(
            "[IntentInspector]",
            {
                "mode": best_mode,
                "score": highest_score,
                "actions": actions,
                "targets": targets,
                "forced_handler": forced_handler,
            },
            flush=True,
        )

        return result