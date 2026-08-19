# MessageTypeDetector.py
from typing import Dict, Any
import re

class MessageTypeDetector:
    """
    メッセージの種類を判定する。

    役割
    ----------------------
    Natural Language
    HTML
    CSS
    JavaScript
    JSX / React
    JSON
    SVG
    Markdown
    Unknown
    """

    def __init__(self, message: str):
        self.message = message or ""
        self.text = self.message.strip()
        self.lower = self.text.lower()

    # ==
    # Public
    # ==

    def detect(self) -> Dict[str, Any]:

        result = {
            "type": "unknown",
            "confidence": 0.0,
            "framework": None,
            "has_html": False,
            "has_css": False,
            "has_script": False,
            "has_svg": False,
            "is_code": False
        }

        # HTML
        if self._is_html():
            result["type"] = "html"
            result["confidence"] = 0.98
            result["is_code"] = True
            result["has_html"] = True
            result["has_script"] = "<script" in self.lower
            result["has_css"] = "<style" in self.lower
            return result

        # JSX
        if self._is_jsx():
            result["type"] = "jsx"
            result["framework"] = "react"
            result["confidence"] = 0.97
            result["is_code"] = True
            return result

        # CSS
        if self._is_css():
            result["type"] = "css"
            result["confidence"] = 0.96
            result["is_code"] = True
            return result

        # JavaScript
        if self._is_javascript():
            result["type"] = "javascript"
            result["confidence"] = 0.95
            result["is_code"] = True
            return result

        # SVG
        if self._is_svg():
            result["type"] = "svg"
            result["confidence"] = 0.98
            result["is_code"] = True
            result["has_svg"] = True
            return result

        # JSON
        if self._is_json():
            result["type"] = "json"
            result["confidence"] = 0.94
            result["is_code"] = True
            return result

        # Markdown
        if self._is_markdown():
            result["type"] = "markdown"
            result["confidence"] = 0.90
            return result

        # Natural Language
        result["type"] = "natural_language"
        result["confidence"] = 0.80

        # 空箱を作らない場合、タイプをunknownに設定
        if "空箱" in self.lower and "作らない" in self.lower:
            result["type"] = "unknown"
            result["confidence"] = 0.0

        return result

    # ==
    # HTML
    # ==

    def _is_html(self):

        patterns = [
            r"<html",
            r"<body",
            r"<head",
            r"<div",
            r"<section",
            r"<button",
            r"<form",
            r"<table",
            r"</"
        ]

        score = 0

        for p in patterns:
            if re.search(p, self.lower):
                score += 1

        return score >= 2

    # ==
    # JSX
    # ==

    def _is_jsx(self):

        patterns = [
            "export default",
            "return (",
            "usestate(",
            "useeffect(",
            "usesnapshot(",
            "props",
            "className=",
            "<>"
        ]

        score = 0

        for p in patterns:
            if p.lower() in self.lower:
                score += 1

        return score >= 2

    # ==
    # CSS
    # ==

    def _is_css(self):

        patterns = [
            "{",
            "}",
            "display:",
            "margin:",
            "padding:",
            "background:",
            "font-size:",
            "color:"
        ]

        score = 0

        for p in patterns:
            if p.lower() in self.lower:
                score += 1

        return score >= 3

    # ==
    # JavaScript
    # ==

    def _is_javascript(self):

        patterns = [
            "function ",
            "const ",
            "let ",
            "var ",
            "=>",
            "document.",
            "window.",
            "fetch(",
            "async ",
            "await "
        ]

        score = 0

        for p in patterns:
            if p.lower() in self.lower:
                score += 1

        return score >= 2

    # ==
    # SVG
    # ==

    def _is_svg(self):

        return "<svg" in self.lower

    # ==
    # JSON
    # ==

    def _is_json(self):

        text = self.text

        if text.startswith("{") and text.endswith("}"):
            return True

        if text.startswith("[") and text.endswith("]"):
            return True

        return False

    # ==
    # Markdown
    # ==

    def _is_markdown(self):

        patterns = [
            "# ",
            "## ",
            "- ",
            "* ",
            "\`\`\`"
        ]

        score = 0

        for p in patterns:
            if p in self.text:
                score += 1

        return score >= 2
