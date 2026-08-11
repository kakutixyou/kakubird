# -*- coding: utf-8 -*-
"""
analyzers.py
- CommentAnalyzer
- DependencyAnalyzer
- SummaryAnalyzer
- ComponentAnalyzer

前提: entry は KnowledgeManager.load_all_json_from_dir() の要素で、
{
  "file_path": "path/to/file",
  "name": "...",
  "description": "...",
  "content": <dict|string>
}
を想定します。
"""

import re
import time
import uuid
import json
import logging
from typing import List, Dict, Any, Optional

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

class BaseAnalyzer:
    name = "BaseAnalyzer"
    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

# -----------------------
# DependencyAnalyzer
# -----------------------
class DependencyAnalyzer(BaseAnalyzer):
    """
    - package.json, requirements.txt, pyproject.toml, setup.cfg, Pipfile などを解析
    - 既知のGPL/AGPL系パッケージと照合（簡易リスト）。本番は SPDX/Registry API で厳密チェックすること。
    - 依存のライセンスが明示されていない場合も警告を出せる。
    """
    name = "DependencyAnalyzer"

    # 簡易の疑わしいパッケージ名リスト（例示） - 本番では外部DBで更新する
    known_gpl_like = {
        "pyqt5", "pyqt6", "python-qt", "ffmpeg-python", "libreoffice", "python-gnome", "some-gpl-lib"
    }

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, dict):
            # いくつかのスクレイプからのキーを考慮
            return content.get("text") or content.get("content") or json.dumps(content)
        elif isinstance(content, str):
            return content
        return ""

    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        alerts = []
        fp = entry.get("file_path", "") or ""
        content = entry.get("content")

        text = self._extract_text(content).lower()

        # package.json の構造的解析（content が dict ならそのまま使う）
        if fp.endswith("package.json") and isinstance(content, dict):
            deps = {}
            for k in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                deps.update(content.get(k, {}) or {})
            found = [p for p in deps.keys() if p.lower() in self.known_gpl_like]
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"package.json の依存に GPL/AGPL 疑いのパッケージが含まれます: {', '.join(found)}",
                    file_path=fp,
                    evidence=f"dependencies keys: {list(deps.keys())}",
                    recommendation="該当パッケージの公式ページでライセンスを確認し、GPL の適用がプロジェクトに及ぶか法務と相談してください。"
                ))

            # 依存パッケージ自体の license フィールドがあるかチェック
            for pkg, meta in deps.items():
                # meta が dict 型なら license を探す（稀なケース）
                if isinstance(meta, dict) and not meta.get("license"):
                    alerts.append(make_alert(
                        rule="DEP-MISSING-LICENSE",
                        analyzer=self.name,
                        severity="low",
                        message=f"依存パッケージ {pkg} の license 情報が package.json のメタにありません（メタがある場合）。実運用では registry を問い合わせて確認推奨。",
                        file_path=fp,
                        evidence=f"{pkg}: {meta}",
                        recommendation="npm / registry API でパッケージメタを照合し、ライセンスを確定してください。"
                    ))

        # requirements.txt の簡易解析
        if fp.lower().endswith("requirements.txt") or "requirements" in fp.lower():
            found = []
            for pkg in self.known_gpl_like:
                if re.search(r"\b" + re.escape(pkg) + r"\b", text, flags=re.I):
                    found.append(pkg)
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"requirements.txt に GPL/AGPL 疑いのパッケージが含まれる可能性: {', '.join(found)}",
                    file_path=fp,
                    evidence="matching lines snippet: " + "\n".join(l for l in text.splitlines() if any(p in l for p in found))[:1000],
                    recommendation="該当依存のライセンスを確認し、GPL の影響（派生物とみなされるか）を法務と確認してください。"
                ))

        # pyproject.toml や Pipfile 等のテキスト検索
        if fp.lower().endswith(("pyproject.toml", "pipfile", "setup.cfg", "setup.py")):
            found = []
            for pkg in self.known_gpl_like:
                if pkg in text:
                    found.append(pkg)
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"{fp} に GPL/AGPL 疑いの依存候補が見つかりました: {', '.join(found)}",
                    file_path=fp,
                    evidence=text[:1000],
                    recommendation="依存関係のライセンス情報を正確に取得して評価してください（registry / SPDX を参照）。"
                ))

        # 依存解析で license 指定が全く見られない package.json 等は info 警告
        if fp.endswith("package.json") and isinstance(content, dict):
            if not content.get("license"):
                alerts.append(make_alert(
                    rule="DEP-NO-LICENSE",
                    analyzer=self.name,
                    severity="low",
                    message="package.json に license フィールドがありません（あると便利です）",
                    file_path=fp,
                    evidence=json.dumps({k: content.get(k) for k in ("name","version","license")}, ensure_ascii=False),
                    recommendation="プロジェクトの意図するライセンスを package.json の license フィールドに明示してください。"
                ))

        return alerts

# -----------------------
# CommentAnalyzer
# -----------------------
class CommentAnalyzer(BaseAnalyzer):
    """
    - ファイル先頭のコメントヘッダ内に 'GPL', 'AGPL', 'All rights reserved' 等がないかを検出。
    - コピー元の帰属情報（Copyright）を検出。
    """
    name = "CommentAnalyzer"

    header_patterns = [
        re.compile(r"gnu (?:general public license|gpl)", flags=re.I),
        re.compile(r"gplv?3", flags=re.I),
        re.compile(r"agpl", flags=re.I),
        re.compile(r"all rights reserved", flags=re.I),
        re.compile(r"copyright\s*\(c\)\s*\d{4}", flags=re.I),
        re.compile(r"copyright\s*©", flags=re.I),
    ]

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, dict):
            return content.get("text") or content.get("content") or json.dumps(content)
        elif isinstance(content, str):
            return content
        return ""

    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"🚀 [{self.name}] を通過中... 対象ファイル: {entry.get('file_path', 'Unknown')}")
        alerts = []
        fp = entry.get("file_path", "") or ""
        text = self._extract_text(entry.get("content", ""))

        # 対象をソースコードに限定
        if not any(fp.endswith(ext) for ext in (".py", ".js", ".java", ".c", ".cpp", ".h", ".go", ".rb", ".ts", ".tsx")):
            return alerts

        if not text:
            return alerts

        # 先頭 N 行をスキャン
        first_lines = "\n".join(text.splitlines()[:40])

        matches = []
        for pat in self.header_patterns:
            m = pat.search(first_lines)
            if m:
                matches.append((pat.pattern, m.group(0)))

        if matches:
            evidence = first_lines[:1200]
            msg = "ファイルヘッダに別ライセンス/帰属表記の可能性があります: " + ", ".join(p[0] for p in matches)
            alerts.append(make_alert(
                rule="FILE-LICENSE-MIX-02",
                analyzer=self.name,
                severity="high",
                message=msg,
                file_path=fp,
                evidence=evidence,
                recommendation="当該ソースの出所とライセンス条件を確認し、ルートの LICENSE と整合するか法務に相談してください。"
            ))

        # もしファイル中に "Licensed under the Apache License" といった明示があれば info を返す
        if re.search(r"licensed under the apache", text, flags=re.I):
            alerts.append(make_alert(
                rule="FILE-OTHER-LICENSE",
                analyzer=self.name,
                severity="low",
                message="ファイルに Apache 系のライセンス注記が含まれています（ルートと異なる可能性）",
                file_path=fp,
                evidence=first_lines[:800],
                recommendation="ライセンス整合性を確認してください（Apache-2.0 は特許許諾を含むため重要です）。"
            ))

        return alerts

# -----------------------
# SummaryAnalyzer
# -----------------------
class SummaryAnalyzer(BaseAnalyzer):
    """
    - README や package.json の description 等からリポジトリの目的・ドメインを要約して tags を付与する。
    - 特許リスクの高いドメイン（video/codec/crypto/hardware など）を検出して警告を返す。
    """
    name = "SummaryAnalyzer"

    patent_keywords = {"video", "codec", "h264", "h265", "hevc", "av1", "encryption", "cryptography", "blockchain", "wallet", "firmware", "hardware", "codec", "codec-impl", "signal-processing"}

    def _extract_text(self, entry: Dict[str, Any]) -> str:
        content = entry.get("content")
        if isinstance(content, dict):
            return content.get("text") or content.get("content") or entry.get("description", "") or ""
        elif isinstance(content, str):
            return content
        return entry.get("description", "") or ""

    def _short_summary(self, text: str, max_chars: int = 200) -> str:
        if not text:
            return ""
        # 単純: 最初の 200 文字を取り、文末で切る
        s = text.strip().replace("\r\n", "\n")
        if len(s) <= max_chars:
            return s
        snippet = s[:max_chars]
        # 文末で切る
        m = re.search(r"(.+[.。!?！？])", snippet[::-1])
        # 上記は逆向きの面倒な処理なので、代替で最後の句点位置を探す
        last_sent_end = max(snippet.rfind("."), snippet.rfind("。"), snippet.rfind("!"), snippet.rfind("？"), snippet.rfind("!"))
        if last_sent_end > 20:
            return snippet[:last_sent_end+1]
        return snippet + "..."

    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        alerts = []
        fp = (entry.get("file_path") or "").lower()
        text = self._extract_text(entry).lower()

        # README か package.json の description などから summary を作る（返却では alert を使ってメタ情報として保存）
        if "readme" in fp or fp.endswith("readme.md") or fp.endswith("readme"):
            summary = self._short_summary(text, 300)
            tags = []
            for kw in ("cli", "library", "web", "api", "plugin", "ui", "docker", "wasm", "embedded"):
                if kw in text:
                    tags.append(kw)
            # patent risk キーワード検出
            found_patent = [k for k in self.patent_keywords if k in text]
            if found_patent:
                alerts.append(make_alert(
                    rule="PATENT-RISK-03",
                    analyzer=self.name,
                    severity="medium",
                    message=f"README に特許リスクが高い領域の語句が含まれています: {', '.join(found_patent)}",
                    file_path=entry.get("file_path"),
                    evidence=summary,
                    recommendation="特許クリアランスが必要な領域です。法務に相談し、必要なら特許許諾を含むライセンス（例: Apache-2.0）や別実装を検討してください。"
                ))
            else:
                # 要約を info レベルで残す
                alerts.append(make_alert(
                    rule="SUMMARY-01",
                    analyzer=self.name,
                    severity="info",
                    message="README から自動生成した要約",
                    file_path=entry.get("file_path"),
                    evidence=summary,
                    recommendation="特になし"
                ))
        # package.json の description
        if fp.endswith("package.json") and isinstance(entry.get("content"), dict):
            desc = (entry["content"].get("description") or "")[:400]
            found_patent = [k for k in self.patent_keywords if k in desc.lower()]
            if found_patent:
                alerts.append(make_alert(
                    rule="PATENT-RISK-03",
                    analyzer=self.name,
                    severity="medium",
                    message=f"package.json.description に特許リスク語句が含まれます: {', '.join(found_patent)}",
                    file_path=entry.get("file_path"),
                    evidence=desc,
                    recommendation="プロジェクトの対象領域に特許リスクがないか検討してください。"
                ))
            else:
                alerts.append(make_alert(
                    rule="SUMMARY-01",
                    analyzer=self.name,
                    severity="info",
                    message="package.json から抽出した説明",
                    file_path=entry.get("file_path"),
                    evidence=desc,
                    recommendation="必要ならREADMEの要約も合わせて確認してください。"
                ))

        return alerts

# -----------------------
# ComponentAnalyzer
# -----------------------
class ComponentAnalyzer(BaseAnalyzer):
    """
    - アセット (画像ファイル .png/.svg/.jpg) のファイル名や README 中の画像参照を走査し、
      商標や公式ロゴの無断利用に関する警告を生成する。
    - 本番ではロゴのハッシュ照合（pHash 等）や公式ガイドライン DB が望ましい。
    """
    name = "ComponentAnalyzer"

    # 簡易の商標キーワード
    trademarks = {"react", "aws", "amazon", "google", "azure", "docker", "kubernetes", "nodejs", "flutter"}

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, dict):
            return content.get("text") or content.get("content") or json.dumps(content)
        elif isinstance(content, str):
            return content
        return ""

    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        alerts = []
        fp = (entry.get("file_path") or "") or ""
        lower_fp = fp.lower()

        # 画像ファイル名に商標語が入っているケース
        if any(lower_fp.endswith(ext) for ext in (".png", ".svg", ".jpg", ".jpeg", ".gif", ".ico")):
            fname = lower_fp.split("/")[-1]
            found = [t for t in self.trademarks if t in fname]
            if found:
                alerts.append(make_alert(
                    rule="TRADEMARK-04",
                    analyzer=self.name,
                    severity="medium",
                    message=f"画像ファイル名に商標を含む可能性があります: {', '.join(found)}",
                    file_path=fp,
                    evidence=f"filename: {fname}",
                    recommendation="公式ガイドラインに従ってロゴ使用の権利を確認してください。商用利用の場合は特に注意。"
                ))

        # Markdown/html などに埋められた画像 URL の参照チェック
        if lower_fp.endswith((".md", ".markdown", ".html")):
            text = self._extract_text(entry.get("content", ""))
            # 画像リンク例: ![alt](path/to/react-logo.png) や <img src="...react-logo.svg">
            img_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)|<img[^>]+src=['\"]([^'\"]+)['\"]", text, flags=re.I)
            img_paths = set([x[0] or x[1] for x in img_refs if x and (x[0] or x[1])])
            matched = []
            for ip in img_paths:
                ip_low = ip.lower()
                for t in self.trademarks:
                    if t in ip_low or t in ip_low.split("/")[-1]:
                        matched.append((ip, t))
            if matched:
                evidence = "; ".join([f"{p} matches {t}" for (p,t) in matched])
                alerts.append(make_alert(
                    rule="TRADEMARK-04",
                    analyzer=self.name,
                    severity="low",
                    message=f"ドキュメントに商標に関連する画像参照が見つかりました",
                    file_path=entry.get("file_path"),
                    evidence=evidence,
                    recommendation="参照している画像の権利関係を確認してください。無断使用は権利侵害になります。"
                ))

        # UI テキスト等で商標名の言及があれば軽い注意
        if lower_fp.endswith((".md", ".txt", ".html")):
            text = self._extract_text(entry.get("content", ""))
            mention = [t for t in self.trademarks if re.search(r"\b" + re.escape(t) + r"\b", text, flags=re.I)]
            if mention:
                alerts.append(make_alert(
                    rule="TRADEMARK-04",
                    analyzer=self.name,
                    severity="low",
                    message=f"ドキュメントに商標名が言及されています: {', '.join(mention)}",
                    file_path=entry.get("file_path"),
                    evidence=text[:800],
                    recommendation="商標の言及は許容される場合が多いが、商標やロゴの再利用はガイドラインを確認してください。"
                ))

        return alerts

# EOF


