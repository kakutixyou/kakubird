# -*- coding: utf-8 -*-
"""
CommentAnalyzer.py
- 各種ソースファイルの先頭コメントヘッダを解析して、ファイル単位のライセンス混入や著作権表示の問題を検出します。
- 入力: entry dict (KnowledgeManager.load_all_json_from_dir() の要素)
    {
      "file_path": "src/foo/bar.py",
      "name": "...",
      "description": "...",
      "content": dict|str
    }
- 出力: alert dict のリスト (make_alert の形式)
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
        "severity": severity,            # "info"/"low"/"medium"/"high"/"critical"
        "message": message,
        "file_path": file_path,
        "evidence": evidence,
        "recommendation": recommendation,
        "timestamp": int(time.time())
    }

class CommentAnalyzer:
    name = "CommentAnalyzer"

    # ライセンス関連パターン
    license_patterns = {
        "gpl": re.compile(r"(gnu (general public license|gpl)|gplv?\s*3|gplv?\s*2)", flags=re.I),
        "agpl": re.compile(r"agpl", flags=re.I),
        "lgpl": re.compile(r"lgpl", flags=re.I),
        "apache": re.compile(r"apache\s+license|licensed under the apache", flags=re.I),
        "mit": re.compile(r"\bmit license\b|\blicense:\s*mit\b", flags=re.I),
        "all-rights": re.compile(r"all rights reserved", flags=re.I),
        # その他の強い帰属表記
        "copyright": re.compile(r"copyright\s*(?:\(|©)?\s*\d{3,4}", flags=re.I),
        "copyright_symbol": re.compile(r"copyright|©", flags=re.I)
    }

    # 対象とするソース拡張子（先頭ヘッダをチェックする対象）
    source_extensions = (".py", ".js", ".ts", ".tsx", ".java", ".c", ".cpp", ".h", ".go", ".rb", ".php", ".cs", ".swift", ".rs")

    def __init__(self, header_line_limit: int = 40):
        """
        header_line_limit: 先頭何行をヘッダ解析対象とするか
        """
        self.header_line_limit = header_line_limit

    def _text_from_content(self, content: Any) -> str:
        if isinstance(content, dict):
            # スクレイピング JSON の一般的キーを参照
            return content.get("text") or content.get("content") or content.get("body") or json.dumps(content, ensure_ascii=False)
        if isinstance(content, str):
            return content
        return ""

    def _get_header_snippet(self, text: str) -> str:
        lines = text.splitlines()
        header = "\n".join(lines[: self.header_line_limit])
        return header

    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        
        logger.info(f"🚀 [{self.name}] を通過中... 対象ファイル: {entry.get('file_path', 'Unknown')}")
        """
        entry: {"file_path": str, "content": dict|str, ...}
        returns: list of alert dicts
        """
        alerts: List[Dict[str, Any]] = []
        fp = (entry.get("file_path") or "")
        content = entry.get("content")
        text = self._text_from_content(content)
        if not fp:
            return alerts

        # Only consider text we can inspect
        if not text:
            return alerts

        lower_fp = fp.lower()

        # 対象ファイルの拡張子がソースコード/ドキュメントであるか判定
        is_source = any(lower_fp.endswith(ext) for ext in self.source_extensions)
        is_text_doc = lower_fp.endswith((".md", ".markdown", ".txt", ".rst", ".html"))

        # 先頭 N 行をヘッダとして切り出す
        header = self._get_header_snippet(text)

        # 1) 強いライセンス表記（GPL/AGPL 等）の検出
        gpl_match = self.license_patterns["gpl"].search(header) or self.license_patterns["agpl"].search(header) or self.license_patterns["lgpl"].search(header)
        if gpl_match:
            evidence = header[:1200]
            alerts.append(make_alert(
                rule="FILE-LICENSE-MIX-02",
                analyzer=self.name,
                severity="high",
                message="ファイルヘッダに GPL/LGPL/AGPL の可能性のある記載が見つかりました（ルート LICENSE と異なる場合、ライセンス混入のリスク）。",
                file_path=fp,
                evidence=evidence,
                recommendation="当該ファイルの出所を確認し、元ライセンスの条件に従ってください。必要であれば法務に相談してください。"
            ))

        # 2) All rights reserved / 強い帰属表記
        if self.license_patterns["all-rights"].search(header):
            evidence = header[:1200]
            alerts.append(make_alert(
                rule="FILE-LICENSE-MIX-02",
                analyzer=self.name,
                severity="high",
                message="ファイルヘッダに 'All rights reserved' 等の強い帰属表記があります（商用利用や再配布に制限がかかる可能性）。",
                file_path=fp,
                evidence=evidence,
                recommendation="出所を確認し、使用・配布が許されるか法務確認してください。"
            ))

        # 3) Apache / MIT 等の注記（ルートと異なる可能性の検出として info）
        if self.license_patterns["apache"].search(header):
            alerts.append(make_alert(
                rule="FILE-OTHER-LICENSE",
                analyzer=self.name,
                severity="low",
                message="ファイルヘッダに Apache 系のライセンス表記が含まれている可能性があります（ルート LICENSE と整合するか確認）。",
                file_path=fp,
                evidence=header[:1200],
                recommendation="ルートの LICENSE と一致しているか、該当部分の出所（コピー元）を確認してください。"
            ))
        if self.license_patterns["mit"].search(header):
            alerts.append(make_alert(
                rule="FILE-OTHER-LICENSE",
                analyzer=self.name,
                severity="info",
                message="ファイルヘッダに MIT ライセンス注記が見つかりました。",
                file_path=fp,
                evidence=header[:1200],
                recommendation="ルート LICENSE と整合するかを確認してください。"
            ))

        # 4) 著作権表示の検出
        copyright_present = bool(self.license_patterns["copyright_symbol"].search(header))
        if copyright_present:
            # より具体的に年と著作者の存在を確認（例: "Copyright (c) 2024 Foo Bar"）
            match = self.license_patterns["copyright"].search(header)
            if match:
                alerts.append(make_alert(
                    rule="FILE-COPYRIGHT-FOUND",
                    analyzer=self.name,
                    severity="info",
                    message="ファイルヘッダに Copyright 表記が見つかりました。",
                    file_path=fp,
                    evidence=header[:300],
                    recommendation="スニペット抽出時はこの著作権表示を残すこと。"
                ))
            else:
                # Copyright の記述はあるが年がない/不完全
                alerts.append(make_alert(
                    rule="FILE-COPYRIGHT-PARTIAL",
                    analyzer=self.name,
                    severity="low",
                    message="ファイルヘッダに Copyright 記載があるが、年や著作者が明確でない可能性があります。",
                    file_path=fp,
                    evidence=header[:300],
                    recommendation="可能なら著作権情報（年・著作者）を明確にしてください。"
                ))
        else:
            # 著作権表示が先頭になければ、スニペット提示時の漏れリスクとして注意を出す（言語によっては通常表示しないこともある）
            if is_source:
                alerts.append(make_alert(
                    rule="COPYRIGHT-MISSING-05",
                    analyzer=self.name,
                    severity="medium",
                    message="ソースファイルの先頭に著作権表示が見当たりません。スニペット抽出時に著作権情報が失われるリスクがあります。",
                    file_path=fp,
                    evidence=header[:300],
                    recommendation="スニペットや引用を行う際は、元ファイルの著作権表示と LICENSE を付記してください。"
                ))

        # 5) ファイル本文に別の LICENSE 表記が later-in-file にあるケース: ヘッダに見つからなかったが本文に 'Licensed under' が含まれる
        if not (gpl_match or self.license_patterns["apache"].search(header) or self.license_patterns["mit"].search(header)):
            # search first 200 lines as fallback
            fallback = "\n".join(text.splitlines()[:200])
            if re.search(r"licensed under", fallback, flags=re.I):
                alerts.append(make_alert(
                    rule="FILE-LICENSE-IN-BODY",
                    analyzer=self.name,
                    severity="low",
                    message="ファイル本文に 'licensed under' の表記が見つかりました（ヘッダにない場合、出所チェックが必要です）。",
                    file_path=fp,
                    evidence=fallback[:1000],
                    recommendation="本文中のライセンス注記を確認し、ルート LICENSE と整合するか確認してください。"
                ))

        # 6) ドキュメント/README の場合は license mention を軽く抽出して summary info として返す
        if is_text_doc:
            # README 等では license に関する短い注記を抽出して info alert を返す
            doc_lower = text.lower()
            if "license" in doc_lower or "licensed under" in doc_lower:
                snippet = "\n".join(text.splitlines()[:20])
                alerts.append(make_alert(
                    rule="DOC-LICENSE-MENTION",
                    analyzer=self.name,
                    severity="info",
                    message="ドキュメントにライセンス言及があります。",
                    file_path=fp,
                    evidence=snippet[:1000],
                    recommendation="README 内のライセンス情報がプロジェクトルートの LICENSE と一致するか確認してください。"
                ))

        return alerts


# Quick manual test
if __name__ == "__main__":
    ca = CommentAnalyzer()
    sample_entries = [
        {
            "file_path": "src/utils/math_helper.py",
            "content": "#!/usr/bin/env python\n# /* This file is licensed under GPL v3 */\n# Copyright (c) 2020 Alice\n\ndef add(a,b): return a+b\n"
        },
        {
            "file_path": "lib/some.c",
            "content": "/*\n * Licensed under the Apache License, Version 2.0 (the \"License\");\n */\nint main(){}\n"
        },
        {
            "file_path": "README.md",
            "content": "# Project\n\nThis project is licensed under MIT License.\n"
        },
        {
            "file_path": "src/no_copyright.js",
            "content": "// sample js file\nfunction f(){}\n"
        }
    ]
    res_all = []
    for e in sample_entries:
        res = ca.detect(e)
        res_all.extend(res)
    print(json.dumps(res_all, ensure_ascii=False, indent=2))