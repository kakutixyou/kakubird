# -*- coding: utf-8 -*-
"""
DependencyAnalyzer.py
- KnowledgeManager.load_all_json_from_dir() の出力形式を受け取り、依存関係ファイルを解析してアラートを返す。
- 対応ファイル: package.json, package-lock.json, yarn.lock (テキスト), requirements.txt, pyproject.toml, Pipfile, setup.py, setup.cfg,
  Pipfile.lock, Pipfile, environment.yml (conda), go.mod, Cargo.toml, Gemfile, composer.json など。
- 実運用では SPDX/registry API との照合を組み込むことを強く推奨します（下に stub 関数あり）。
"""

import re
import json
import time
import uuid
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
        "severity": severity,            # info/low/medium/high/critical
        "message": message,
        "file_path": file_path,
        "evidence": evidence,
        "recommendation": recommendation,
        "timestamp": int(time.time())
    }

class DependencyAnalyzer:
    name = "DependencyAnalyzer"

    # 簡易の疑わしい (GPL/AGPL 系) パッケージ名。実運用では外部DBで更新する。
    known_gpl_like = {
        "pyqt5", "pyqt6", "python-qt", "ffmpeg-python", "libreoffice", "python-gnome",
        # examples
        "some-gpl-lib", "gpl-lib-example"
    }

    # 許容されないライセンスキーワード（package.json 等に直接書かれている場合）
    non_permissive_license_keywords = {"gpl", "agpl", "lgpl", "proprietary", "commercial-use-restricted"}

    def __init__(self, enable_registry_lookup: bool = False):
        """
        enable_registry_lookup: 将来的に registry (npm/pypi etc) を問い合わせる場合に True にするフック。
        現在は stub で実装しているだけです。
        """
        self.enable_registry_lookup = enable_registry_lookup

    # ---- Registry / SPDX stub (実運用では実装する) ----
    def _query_registry_license(self, package_name: str, ecosystem: str) -> Optional[str]:
        """
        パッケージレジストリからライセンス情報を取得するフック。
        本実装では未実装（None を返す）。本番では npm / PyPI / crates.io / golang.org などの API を呼ぶ。
        """
        logger.debug(f"registry lookup stub: {ecosystem}::{package_name}")
        # TODO: 実装: npm registry, pypi JSON API, crates.io API, rubygems API などを叩く
        return None

    # ---- Helpers: 抽出・解析 ----
    def _ensure_dict(self, content: Any) -> Optional[Dict[str, Any]]:
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            try:
                return json.loads(content)
            except Exception:
                return None
        return None

    def _text_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            # common scraped fields
            return content.get("text") or content.get("content") or json.dumps(content, ensure_ascii=False)
        return ""

    def _parse_requirements_lines(self, text: str) -> List[str]:
        """
        requirements.txt のような行からパッケージ名を抽出する簡易ロジック。
        - コメント行を除外
        - git+ や direct URLs は special_sources として扱う
        """
        pkgs = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # direct git or url
            if line.startswith(("git+", "http://", "https://", "ssh://")) or "@" in line and "://" in line:
                pkgs.append(line)
                continue
            # example: package==1.2.3, package>=1.0, package[extras]==x
            m = re.match(r"^\s*([A-Za-z0-9_\-\.]+)", line)
            if m:
                pkgs.append(m.group(1).lower())
        return pkgs

    def _parse_package_json_deps(self, content: Dict[str, Any]) -> Dict[str, str]:
        deps = {}
        for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            block = content.get(k) or {}
            if isinstance(block, dict):
                for pkg, ver in block.items():
                    deps[pkg] = ver
        return deps

    def _parse_lockfile_package_names(self, text: str) -> List[str]:
        """
        yarn.lock / package-lock.json テキストから包摂的にパッケージ名を抽出する。
        For package-lock.json: try json parse, else fallback regex
        """
        names = []
        try:
            parsed = json.loads(text)
            # npm package-lock.json has "dependencies" top-level
            if isinstance(parsed, dict):
                def walk_deps(d):
                    if isinstance(d, dict):
                        for k, v in d.items():
                            if k not in names:
                                names.append(k)
                            if isinstance(v, dict) and "dependencies" in v:
                                walk_deps(v["dependencies"])
                if "dependencies" in parsed:
                    walk_deps(parsed["dependencies"])
                else:
                    # fallback: scan keys
                    for k in parsed.keys():
                        if isinstance(k, str):
                            names.append(k)
        except Exception:
            # fallback: simple regex for lines like "  react@^16.13.1:"
            for m in re.finditer(r"^([A-Za-z0-9_\-\.\/]+)(?:@|\s)", text, flags=re.M):
                names.append(m.group(1))
        # normalize
        return list(dict.fromkeys([n.lower() for n in names if n]))

    # ---- Main detect ----
    def detect(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"🚀 [{self.name}] を通過中... 対象ファイル: {entry.get('file_path', 'Unknown')}")
        """
        entry: {"file_path": str, "name": str, "description": str, "content": dict|str}
        returns: list of alert dicts
        """
        alerts: List[Dict[str, Any]] = []
        fp = (entry.get("file_path") or "").lower()
        content = entry.get("content")
        text = self._text_content(content)

        # 1) package.json
        if fp.endswith("package.json"):
            logger.debug("Parsing package.json: %s", fp)
            pj = self._ensure_dict(content)
            if pj is None:
                # maybe content is string
                try:
                    pj = json.loads(text)
                except Exception:
                    pj = None
            if pj:
                # license field missing?
                license_field = pj.get("license")
                if not license_field:
                    alerts.append(make_alert(
                        rule="DEP-NO-LICENSE",
                        analyzer=self.name,
                        severity="low",
                        message="package.json に license フィールドがありません。",
                        file_path=fp,
                        evidence=json.dumps({k: pj.get(k) for k in ("name", "version", "license")}, ensure_ascii=False),
                        recommendation="package.json にプロジェクトのライセンス（例: MIT）を明記してください。"
                    ))
                else:
                    # direct license text check for non-permissive keywords
                    lf = str(license_field).lower()
                    for kw in self.non_permissive_license_keywords:
                        if kw in lf:
                            alerts.append(make_alert(
                                rule="DEP-PROJ-NON-PERMISSIVE",
                                analyzer=self.name,
                                severity="high" if kw in ("gpl","agpl","proprietary") else "medium",
                                message=f"package.json の license フィールドに非許諾性または注意が必要な記述が見つかりました: {license_field}",
                                file_path=fp,
                                evidence=f"license: {license_field}",
                                recommendation="プロジェクトのライセンスが商用利用/配布に与える影響を法務と確認してください。"
                            ))
                # dependencies scan
                deps = self._parse_package_json_deps(pj)
                if deps:
                    found = [p for p in deps.keys() if p.lower() in self.known_gpl_like]
                    if found:
                        alerts.append(make_alert(
                            rule="DEP-GPL-01",
                            analyzer=self.name,
                            severity="high",
                            message=f"package.json の依存に GPL/AGPL 疑いのパッケージが含まれます: {', '.join(found)}",
                            file_path=fp,
                            evidence=f"dependencies: {list(deps.keys())}",
                            recommendation="該当パッケージのライセンスを確認し、GPL がプロジェクト全体へ波及するかを法務と評価してください。"
                        ))
                    # optional: check version spec that points to git/url
                    unsafe_sources = {p: v for p,v in deps.items() if isinstance(v, str) and any(prefix in v for prefix in ("git+", "http://", "https://", "file:"))}
                    if unsafe_sources:
                        alerts.append(make_alert(
                            rule="DEP-UNSAFE-SOURCE-03",
                            analyzer=self.name,
                            severity="medium",
                            message="依存バージョンに git/url/file 指定が含まれています（レジストリのメタが使えない可能性があります）。",
                            file_path=fp,
                            evidence=json.dumps(unsafe_sources, ensure_ascii=False),
                            recommendation="指定先のソースにライセンス情報があるか確認してください。可能なら公開パッケージで代替を検討してください。"
                        ))

        # 2) package-lock.json / yarn.lock
        if fp.endswith("package-lock.json") or fp.endswith("yarn.lock") or fp.endswith("npm-shrinkwrap.json"):
            logger.debug("Parsing lockfile: %s", fp)
            names = self._parse_lockfile_package_names(text)
            found = [n for n in names if n in self.known_gpl_like]
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"ロックファイルに GPL/AGPL 疑いのパッケージが含まれています: {', '.join(found)}",
                    file_path=fp,
                    evidence=f"matched packages: {found[:30]}",
                    recommendation="ロックファイルに現れる実際の依存ツリーを確認し、GPL の影響を評価してください。"
                ))

        # 3) requirements.txt / Pipfile / Pipfile.lock / setup.py / setup.cfg / pyproject.toml
        if fp.endswith("requirements.txt") or "requirements" in fp:
            logger.debug("Parsing requirements: %s", fp)
            pkgs = self._parse_requirements_lines(text)
            found = [p for p in pkgs if any(k in p for k in self.known_gpl_like)]
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"requirements に GPL/AGPL 疑いのパッケージが見つかりました: {', '.join(found)}",
                    file_path=fp,
                    evidence="\n".join(line for line in text.splitlines() if any(f in line for f in found))[:1000],
                    recommendation="該当パッケージのライセンスを確認し、商用利用や配布に与える影響を法務に確認してください。"
                ))

        if fp.endswith(("pyproject.toml", "Pipfile", "pipfile")) or fp.endswith("setup.cfg") or fp.endswith("setup.py"):
            logger.debug("Parsing pyproject/Pipfile/setup: %s", fp)
            # pyproject は TOML 形式。スクレイピングで dict で来る場合は内容確認
            if isinstance(content, dict):
                # pyproject toml parsed -> check [project] or [tool.poetry.dependencies]
                found_names = []
                # check common dict positions
                for block in ("project", "tool", "tool.poetry", "tool.poetry.dependencies", "tool.poetry.dev-dependencies"):
                    # naive traversal
                    parts = block.split(".")
                    node = content
                    ok = True
                    for p in parts:
                        if not isinstance(node, dict) or p not in node:
                            ok = False
                            break
                        node = node[p]
                    if ok and isinstance(node, dict):
                        for k in node.keys():
                            found_names.append(k.lower())
                found = [n for n in found_names if n in self.known_gpl_like]
                if found:
                    alerts.append(make_alert(
                        rule="DEP-GPL-01",
                        analyzer=self.name,
                        severity="high",
                        message=f"{fp} 中の依存に GPL 疑いのパッケージが含まれています: {', '.join(found)}",
                        file_path=fp,
                        evidence=", ".join(found_names[:200]),
                        recommendation="依存元のライセンスを確認してください。"
                    ))
            else:
                # fallback: keyword search in text
                lowers = text.lower()
                found = [k for k in self.known_gpl_like if k in lowers]
                if found:
                    alerts.append(make_alert(
                        rule="DEP-GPL-01",
                        analyzer=self.name,
                        severity="high",
                        message=f"{fp} に GPL/AGPL 疑いの文字列が見つかりました: {', '.join(found)}",
                        file_path=fp,
                        evidence=text[:1000],
                        recommendation="依存のライセンスを詳細に確認してください。"
                    ))

        # 4) go.mod, Cargo.toml, Gemfile, composer.json, environment.yml
        if fp.endswith("go.mod"):
            logger.debug("Parsing go.mod: %s", fp)
            # go mod lines like "require github.com/pkg/errors v0.8.1"
            mods = []
            for l in text.splitlines():
                m = re.match(r"^\s*require\s+([^\s]+)", l)
                if m:
                    mods.append(m.group(1).lower())
            found = [m for m in mods if any(k in m for k in self.known_gpl_like)]
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"go.mod に GPL 疑いの依存が含まれます: {', '.join(found)}",
                    file_path=fp,
                    evidence=", ".join(found[:200]),
                    recommendation="依存のライセンスを確認してください。"
                ))

        if fp.endswith(("cargo.toml", "cargo.lock", "Cargo.toml", "Cargo.lock")):
            logger.debug("Parsing Cargo file: %s", fp)
            # simple keyword search
            found = [k for k in self.known_gpl_like if k in text.lower()]
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"Cargo 関連ファイルに GPL 疑いパッケージが見つかりました: {', '.join(found)}",
                    file_path=fp,
                    evidence=text[:1000],
                    recommendation="該当クレートのライセンスを確認してください。"
                ))

        if fp.endswith(("gemfile", "gemfile.lock", "Gemfile", "Gemfile.lock")):
            found = [k for k in self.known_gpl_like if k in text.lower()]
            if found:
                alerts.append(make_alert(
                    rule="DEP-GPL-01",
                    analyzer=self.name,
                    severity="high",
                    message=f"Gemfile に GPL 疑いの gem が含まれている可能性: {', '.join(found)}",
                    file_path=fp,
                    evidence=text[:800],
                    recommendation="Gem のライセンスを確認してください。"
                ))

        if fp.endswith(("composer.json", "composer.lock")):
            try:
                cj = self._ensure_dict(content) or json.loads(text)
            except Exception:
                cj = None
            if isinstance(cj, dict):
                # composer.json has require, require-dev
                reqs = {}
                for k in ("require", "require-dev"):
                    block = cj.get(k) or {}
                    if isinstance(block, dict):
                        for pkg in block.keys():
                            reqs[pkg.lower()] = True
                found = [p for p in reqs.keys() if any(k in p for k in self.known_gpl_like)]
                if found:
                    alerts.append(make_alert(
                        rule="DEP-GPL-01",
                        analyzer=self.name,
                        severity="high",
                        message=f"composer の依存に GPL 疑いのパッケージが含まれます: {', '.join(found)}",
                        file_path=fp,
                        evidence=", ".join(list(reqs.keys())[:200]),
                        recommendation="依存のライセンスを確認してください。"
                    ))
            else:
                found = [k for k in self.known_gpl_like if k in text.lower()]
                if found:
                    alerts.append(make_alert(
                        rule="DEP-GPL-01",
                        analyzer=self.name,
                        severity="high",
                        message=f"composer ファイルに疑わしい文字列が見つかりました: {', '.join(found)}",
                        file_path=fp,
                        evidence=text[:800],
                        recommendation="ライセンス調査を行ってください。"
                    ))

        # 5) general heuristic: direct binary/git URL dependencies
        if re.search(r"(git\+https?|https?://.*(github|gitlab|bitbucket).*(\.git)?)", text, flags=re.I):
            alerts.append(make_alert(
                rule="DEP-UNSAFE-SOURCE-03",
                analyzer=self.name,
                severity="medium",
                message="依存に git/url 指定が見つかる可能性があります。レジストリに存在しない依存はライセンス調査が難しくなります。",
                file_path=fp,
                evidence=text[:800],
                recommendation="外部リポジトリ指定の依存については当該リポジトリの LICENSE を確認してください。"
            ))

        # 6) registry lookup (optional)
        if self.enable_registry_lookup:
            # example pass: check package.json dependencies
            try:
                if fp.endswith("package.json"):
                    pj = self._ensure_dict(content) or json.loads(text)
                    deps = self._parse_package_json_deps(pj) if pj else {}
                    for pkg in list(deps.keys())[:50]:
                        lic = self._query_registry_license(pkg, ecosystem="npm")
                        if lic:
                            low = lic.lower()
                            if any(k in low for k in self.non_permissive_license_keywords):
                                alerts.append(make_alert(
                                    rule="DEP-GPL-01",
                                    analyzer=self.name,
                                    severity="high",
                                    message=f"レジストリ照合により依存 {pkg} のライセンスは {lic} です（非許諾性/注意）。",
                                    file_path=fp,
                                    evidence=f"{pkg}: license={lic}",
                                    recommendation="法務と相談してください。"
                                ))
            except Exception as e:
                logger.exception("registry lookup error: %s", e)
                # do not fail analyzer

        return alerts

# Example usage:
if __name__ == "__main__":
    # quick self-test
    da = DependencyAnalyzer()
    sample_pkg = {
        "file_path": "path/to/package.json",
        "content": {
            "name": "sample",
            "version": "0.1.0",
            "dependencies": {
                "express": "^4.17.1",
                "pyqt5": "^5.15.0"
            }
        }
    }
    res = da.detect(sample_pkg)
    print(json.dumps(res, ensure_ascii=False, indent=2))