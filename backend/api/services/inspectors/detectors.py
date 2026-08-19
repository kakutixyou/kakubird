import os
import re
from typing import Any, Dict, List, Optional

_DIR = os.path.dirname(__file__)


def load_json(filepath: str) -> dict:
    import json

    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(
            f"   [IntentInspector] {os.path.basename(filepath)} のロードに失敗: {e}",
            flush=True,
        )
    return {}


class ForcedHandlerDetector:
    def detect(self, message: str) -> Optional[str]:
        pattern = r"(?:@|今回の質問は|担当:)\s*([a-zA-Z_]+Handler)(?:\.py)?"
        match = re.search(pattern, message, re.IGNORECASE)
        return match.group(1).lower() if match else None


class ActionDetector:
    def __init__(self, actions_map: Dict[str, List[str]]):
        self.actions_map = actions_map

    def detect(self, msg_lower: str) -> List[str]:
        detected = []
        for action_key, words in self.actions_map.items():
            for w in words:
                if w.lower() in msg_lower and action_key not in detected:
                    detected.append(action_key)
        return detected


class TargetDetector:
    def __init__(self, targets_config: Dict[str, List[str]]):
        self.targets_config = targets_config

    def detect_words(self, msg_lower: str) -> List[str]:
        detected = []
        for words in self.targets_config.values():
            for w in words:
                if w.lower() in msg_lower and w not in detected:
                    detected.append(w)
        return detected

    def detect_categories(self, msg_lower: str) -> List[str]:
        categories = []
        for category, words in self.targets_config.items():
            for w in words:
                if w.lower() in msg_lower:
                    if category not in categories:
                        categories.append(category)
                    break
        return categories


class ThemeSurfaceDetector:
    def detect(self, msg_lower: str) -> Dict[str, Any]:
        result = {
            "theme": None,
            "surface": None,
            "responsive": False,
            "modify_existing": False,
        }
        themes = ["modern", "minimal", "glass", "dark", "light", "cyberpunk"]
        for t in themes:
            if t in msg_lower:
                result["theme"] = t
                break

        if "glass" in msg_lower:
            result["surface"] = "glass"
        elif "neumorphism" in msg_lower:
            result["surface"] = "neumorphism"
        elif "paper" in msg_lower:
            result["surface"] = "paper"

        if any(w in msg_lower for w in ["スマホ", "mobile", "responsive"]):
            result["responsive"] = True

        if any(w in msg_lower for w in ["修正", "変更", "update", "既存", "template"]):
            result["modify_existing"] = True

        return result


class DeploymentMetricDetector:
    def __init__(self, kw_config: Dict[str, Any], themes_config: Dict[str, Any]):
        self.kw = kw_config
        self.themes = themes_config

    def detect(self, msg_lower: str) -> Dict[str, Any]:
        metrics = {
            "intent_score": 0,
            "trigger_hits": 0,
            "surface_hits": 0,
            "mood_hits": 0,
        }
        res = {
            "deployment_surface": None,
            "deployment_theme": None,
            "deployment_metrics": metrics,
        }
        intent_words = [
            "作って",
            "作成",
            "生成",
            "プロジェクト",
            "ビルダー",
            "ハンドラー",
            "project",
            "builder",
            "handler",
            "deployment",
        ]

        for w in intent_words:
            if w.lower() in msg_lower:
                metrics["intent_score"] += 1

        triggers = self.kw.get("triggers", {})
        trigger_words = (
            triggers.get("ja", [])
            + triggers.get("en", [])
            + triggers.get("commands", [])
        )

        for t in trigger_words:
            if t.lower() in msg_lower:
                metrics["trigger_hits"] += 1

        surface_kw = self.kw.get("surface_keywords", {})
        surface_scores: Dict[str, int] = {}

        for surface_name, data in surface_kw.items():
            if surface_name.startswith("_") or not isinstance(data, dict):
                continue
            surface_scores[surface_name] = 0
            words = data.get("ja", []) + data.get("en", [])
            for w in words:
                if w.lower() in msg_lower:
                    metrics["surface_hits"] += 1
                    surface_scores[surface_name] += 1

        if surface_scores:
            best_surface = max(surface_scores, key=lambda k: surface_scores[k])
            if surface_scores[best_surface] > 0:
                res["deployment_surface"] = best_surface

        mood_kw = self.kw.get("mood_keywords", {})
        for _, data in mood_kw.items():
            if not isinstance(data, dict):
                continue
            words = data.get("ja", []) + data.get("en", [])
            for w in words:
                if w.lower() in msg_lower:
                    metrics["mood_hits"] += 1

        named_themes = self.kw.get("named_themes", {})
        for name, info in named_themes.items():
            if name.lower() in msg_lower:
                res["deployment_theme"] = info.get("title", name)
                res["deployment_surface"] = info.get("surface", res["deployment_surface"])
                break

        if not res["deployment_theme"] and res["deployment_surface"]:
            theme_data = self.themes.get(res["deployment_surface"], {})
            res["deployment_theme"] = theme_data.get(
                "title",
                res["deployment_surface"].replace("-", " ").title(),
            )
        return res
