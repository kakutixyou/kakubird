# -*- coding: utf-8 -*-
"""
SummaryAnalyzer.py
- README / ドキュメント / package.json の description 等を解析して短い要約とタグを作成します。
- 特許リスクに関するキーワード検出や、ドキュメント中のライセンス言及の検出を行いアラートを返します。
- 入力: entry dict ({"file_path", "name", "description", "content"})
- 出力: list of alert dicts (make_alert schema)
"""

import re
import json
import time
import uuid
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def make_alert(rule: str, analyzer: str, severity: str, message: str,
               file_path: Optional[str], evidence: str, recommendation: str) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "rule": rule,
        "analyzer": analyzer,
        "severity": severity,            # info/low/medium/high/critical
        "message": message,
        "file_path": file_path,
        "evidence": evidence,
        "recommendation": recommendation,
        "timestamp": int(time.time())
    }

class SummaryAnalyzer:
    name = "SummaryAnalyzer"

    # 特許リスクに関連するキーワード（簡易）
    patent_keywords = {
        "video", "codec", "h264", "h265", "hevc", "av1",
        "encryption", "cryptography", "rsa", "aes", "blockchain",
        "wallet", "firmware", "hardware", "signal-processing", "codec-impl"
    }

    # ドメイン/機能タグ化に使うキーワードマップ (キーワード -> tag)
    keyword_tag_map = {
        "cli": "cli",
        "command line": "cli",
        "library": "library",
        "plugin": "plugin",
        "web": "web",
        "frontend": "frontend",
        "backend": "backend",
        "api": "api",
        "server": "server",
        "docker": "docker",
        "kubernetes": "k8s",
        "wasm": "wasm",
        "embedded": "embedded",
        "iot": "iot",
        "mobile": "mobile",
        "android": "android",
        "ios": "ios",
        "react": "react",
        "vue": "vue",
        "angular": "angular",
        "python": "python",
        "node": "node",
        "rust": "rust",
        "go": "go",
        "c++": "cpp",
        "c#": "csharp",
        "blockchain": "blockchain",
        "cryptocurrency": "crypto",
        "encryption": "crypto",
        "machine learning": "ml",
        "ml": "ml",
        "deep learning": "ml",
        "training": "ml",
        "dataset": "data",
        "database": "database",
        "postgres": "database",
        "mysql": "database",
        "redis": "database",
        "video": "video",
        "audio": "audio",
        "image": "image",
        "firmware": "firmware"
    }

    def __init__(self, summary_max_chars: int = 300):
        self.summary_max_chars = summary_max_chars

    def _text_from_content(self, entry: Dict[str, Any]) -> str:
        content = entry.get("content")
        # common scraped shapes
        if isinstance(content, dict):
            # prefer explicit textual fields if present
            for k in ("text", "content", "body", "readme", "raw"):
                if k in content and isinstance(content[k], str) and content[k].strip():
                    return content[k]
            # fall back to description or full dump
            return entry.get("description", "") or json.dumps(content, ensure_ascii=False)
        if isinstance(content, str):
            return content
        return entry.get("description", "") or ""

    def _short_summary(self, text: str) -> str:
        if not text:
            return ""
        s = text.strip().replace("\r\n", "\n").replace("\t", " ")
        # prefer first paragraph
        paragraphs = [p.strip() for p in s.split("\n\n") if p.strip()]
        first = paragraphs[0] if paragraphs else s
        if len(first) <= self.summary_max_chars:
            return first
        # cut to sentence boundary if possible
        snippet = first[: self.summary_max_chars]
        last_sent_end = max(snippet.rfind("."), snippet.rfind("。"), snippet.rfind("!"), snippet.rfind("?"))
        if last_sent_end > 20:
            return snippet[: last_sent_end + 1]
        return snippet + "..."

    def _collect_tags(self, text: str) -> List[str]:
        tags = set()
        lower = text.lower()
        for kw, tag in self.keyword_tag_map.items():
            if kw in lower:
                tags.add(tag)
        return sorted(tags)

    def _find_patent_keywords(self, text: str) -> List[str]:
        lower = text.lower()
        return [k for k in self.patent_keywords if k in lower]

    def _find_license_mentions(self, text: str) -> List[str]:
        found = []
        lower = text.lower()
        if "license" in lower or "licensed under" in lower or "mit" in lower or "apache" in lower or "gpl" in lower:
            # capture short context lines where license words appear
            for line in text.splitlines():
                low = line.lower()
                if any(tok in low for tok in ("license", "licensed under", "mit", "apache", "gpl", "lgpl", "agpl")):
                    found.append(line.strip())
            return found
        return []

    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze a single entry and return a list of alert dicts (which may include
        info-level summary items and medium/high alerts for patent/license risks).
        """
        alerts: List[Dict[str, Any]] = []
        fp = (entry.get("file_path") or "").lower()
        text = self._text_from_content(entry).strip()
        if not text and not entry.get("description"):
            # nothing to summarize
            return alerts

        # If this is a README or other doc-like file, create a summary
        is_readme = "readme" in fp or fp.endswith(("readme", "readme.md", "readme.markdown"))
        is_package_json = fp.endswith("package.json")
        is_doc = fp.endswith((".md", ".markdown", ".txt", ".rst", ".html")) or is_readme

        # 1) Produce summary info for README / docs
        if is_readme or is_doc:
            summary = self._short_summary(text)
            tags = self._collect_tags(text)
            evidence = json.dumps({"summary": summary, "tags": tags}, ensure_ascii=False)
            alerts.append(make_alert(
                rule="SUMMARY-01",
                analyzer=self.name,
                severity="info",
                message="ドキュメント / README の要約を生成しました。",
                file_path=entry.get("file_path"),
                evidence=evidence,
                recommendation="要約を確認し、README がプロジェクトの目的を明確に伝えているか確認してください。"
            ))
            # license mentions in doc
            license_lines = self._find_license_mentions(text)
            if license_lines:
                alerts.append(make_alert(
                    rule="DOC-LICENSE-MENTION",
                    analyzer=self.name,
                    severity="low",
                    message="ドキュメント中にライセンスに関する記述が見つかりました。",
                    file_path=entry.get("file_path"),
                    evidence="\n".join(license_lines[:10]),
                    recommendation="README のライセンス記載がルートの LICENSE と一致しているか確認してください。"
                ))

            # patent-risk detection
            found_patents = self._find_patent_keywords(text)
            if found_patents:
                alerts.append(make_alert(
                    rule="PATENT-RISK-03",
                    analyzer=self.name,
                    severity="medium",
                    message=f"ドキュメントに特許リスクが想定される語句が含まれています: {', '.join(found_patents)}",
                    file_path=entry.get("file_path"),
                    evidence=summary,
                    recommendation="該当領域は特許リスクが高いため、法務に相談してください（必要なら特許クリアランスを実施）。"
                ))

        # 2) package.json の description を要約 / tags 抽出
        if is_package_json and isinstance(entry.get("content"), dict):
            desc = (entry["content"].get("description") or "").strip()
            if desc:
                summary = self._short_summary(desc)
                tags = self._collect_tags(desc)
                alerts.append(make_alert(
                    rule="SUMMARY-01",
                    analyzer=self.name,
                    severity="info",
                    message="package.json.description から抽出した説明",
                    file_path=entry.get("file_path"),
                    evidence=json.dumps({"summary": summary, "tags": tags}, ensure_ascii=False),
                    recommendation="package.json.description がプロジェクトを簡潔に説明しているか確認してください（README と整合させると良い）。"
                ))
                found_patents = self._find_patent_keywords(desc)
                if found_patents:
                    alerts.append(make_alert(
                        rule="PATENT-RISK-03",
                        analyzer=self.name,
                        severity="medium",
                        message=f"package.json.description に特許リスクが想定される語句が含まれています: {', '.join(found_patents)}",
                        file_path=entry.get("file_path"),
                        evidence=desc,
                        recommendation="該当ドメインについて特許の有無を確認してください。"
                    ))
            else:
                # no description
                alerts.append(make_alert(
                    rule="SUMMARY-MISSING-02",
                    analyzer=self.name,
                    severity="low",
                    message="package.json に description が見当たりません。",
                    file_path=entry.get("file_path"),
                    evidence=json.dumps({"name": entry.get("content", {}).get("name") if isinstance(entry.get("content"), dict) else None}),
                    recommendation="簡潔な description を追加すると可読性が向上します。"
                ))

        # 3) Generic summary for other files (fallback): record short first-line summary if not doc/package
        if not (is_readme or is_package_json or is_doc):
            # use entry.description first, else first paragraph of content
            fallback_source = entry.get("description") or text
            if fallback_source:
                summary = self._short_summary(fallback_source)
                alerts.append(make_alert(
                    rule="SUMMARY-01",
                    analyzer=self.name,
                    severity="info",
                    message="ファイルから生成した簡易要約",
                    file_path=entry.get("file_path"),
                    evidence=summary,
                    recommendation="必要に応じて README に要約を統合してください。"
                ))

        return alerts


# Quick demo/test
if __name__ == "__main__":
    sa = SummaryAnalyzer()
    examples = [
        {
            "file_path": "README.md",
            "content": "# Video Transcoder\n\nThis project provides a video transcoding pipeline with H.264/H.265 encoder wrappers and hardware acceleration.\n\nFeatures: docker, cli, api\n\nLicensed under MIT.\n"
        },
        {
            "file_path": "package.json",
            "content": {"name": "crypto-wallet", "version": "1.0.0", "description": "A lightweight blockchain wallet for mobile and web."}
        },
        {
            "file_path": "docs/overview.txt",
            "content": "This library offers utilities for signal-processing and encryption. Use with care."
        },
    ]
    all_alerts = []
    for e in examples:
        all_alerts.extend(sa.detect(e))
    print(json.dumps(all_alerts, ensure_ascii=False, indent=2))