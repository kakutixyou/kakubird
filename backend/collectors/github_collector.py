"""
github_collector.py
=
GitHub APIを使ってリポジトリの全情報を収集する Collector。
AIのRAG（検索拡張生成）データ構築に向けた「黄金ルート」を採用。

収集対象:
  1. README / CONTRIBUTING / docs 等（プロジェクトの顔・小ネタ）
  2. ファイルツリー（フォルダ構成・全体マップ）
  3. requirements.txt / package.json 等（技術スタック）
  4. 主要なソースコード（.py, .sh, フロントエンド言語など）
  5. 解決済みのIssues（エラー解決策・トラブルシューティングの宝庫）

出力: dict（orchestrator.py が受け取る collected オブジェクト）
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

# GitHub APIのレート制限対策: リクエスト間のスリープ（秒）
REQUEST_INTERVAL = 0.3
# 取得するソースファイルの最大件数（トークン節約のため制限）
MAX_SOURCE_FILES = 30
# 取得するIssueの最大件数
MAX_ISSUES = 10
# 1ファイルの最大取得サイズ（バイト）
MAX_FILE_BYTES = 50_000


class GitHubCollector:
    # ── 取得ターゲットのファイル名定義 ──
    LICENSE_FILENAMES = {
        "LICENSE", "LICENSE.txt", "LICENSE.md",
        "LICENCE", "LICENCE.txt", "LICENCE.md",
        "COPYING", "COPYING.txt",
    }
    README_FILENAMES = {
        "README.md", "README.txt", "README.rst", "README",
        "readme.md", "readme.txt",
    }
    CONTRIBUTING_FILENAMES = {
        "CONTRIBUTING.md", "CONTRIBUTING.txt", "CONTRIBUTING",
    }
    TERMS_FILENAMES = {
        "TERMS.md", "TERMS_OF_SERVICE.md", "利用規約.md",
    }
    # ★追加: 技術スタック（依存関係）を特定するファイル
    DEPENDENCY_FILENAMES = {
        "requirements.txt", "package.json", "Cargo.toml", 
        "go.mod", "pom.xml", "Gemfile", "Pipfile"
    }
# 収集対象の拡張子に、Sass/SCSS を追加！
    TARGET_EXTENSIONS = (
        ".py", ".sh", ".bash", ".zsh", ".js", ".jsx", ".ts", ".tsx", ".css", ".sass", ".scss"
    )

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    # ─────────────────────────────────────────────────────
    # パブリックメソッド
    # ─────────────────────────────────────────────────────

    def collect(self, url: str) -> dict:
        owner, repo = self._parse_url(url)
        print(f"\n🚀 [GitHub Collector] ターゲット到達: {owner}/{repo}")

        # 1. メタ情報取得
        repo_meta = self._fetch_repo_meta(owner, repo)

        # ✨【追加】プログラミング言語の割合を取得
        print("📊 [新機能] プログラミング言語の構成比を計算中...")
        languages_percentage = self._fetch_repo_languages(owner, repo)
        
        # repo_meta の中に「languages_percentage」として混ぜ込んでおくと、後でAIが見やすくなります
        repo_meta["languages_percentage"] = languages_percentage

        # 2. ファイルツリー（既存のまま）
        print("🗺️  [ルート 1/4] フォルダー構成（ファイルツリー）を解析中...")
        file_tree = self._fetch_file_tree(owner, repo)
        # 3. ライセンス・ドキュメント系ファイル（README等）
        print("📖 [ルート 2/4] プロジェクトの顔（README・ドキュメント）を探索中...")
        license_files = self._fetch_docs_and_licenses(owner, repo, file_tree)
        for path in license_files.keys():
            print(f"   => 発見: {path}")

        # 4. 依存関係ファイル（package.json / requirements.txt 等）
        print("⚙️  [ルート 3/4] 技術スタック（package.json / requirements.txt）を特定中...")
        dependency_files = self._fetch_dependency_files(owner, repo, file_tree)
        for path in dependency_files.keys():
            print(f"   => 発見: {path}")
        # 5. ソースファイル
        target_paths = self._filter_source_files(file_tree)
        source_files = self._fetch_source_files(owner, repo, target_paths)

        # 6. ★追加: 解決済みIssues（エラー解決の宝庫）
        issues_data = self._fetch_closed_issues(owner, repo)

        logger.info(f"[GitHub] 収集完了: Docs {len(license_files)}件, Deps {len(dependency_files)}件, ソース {len(source_files)}件, Issues {len(issues_data)}件")

        print("✨ [GitHub Collector] 全ルートの探索が完了しました！\n")

        return {
            "repo_meta":        repo_meta,
            "file_tree":        file_tree,
            "license_files":    license_files,
            "dependency_files": dependency_files,
            "source_files":     source_files,
            "issues_data":      issues_data,
        }

    # ─────────────────────────────────────────────────────
    # 内部メソッド（API通信系）
    # ─────────────────────────────────────────────────────

    def _parse_url(self, url: str) -> tuple[str, str]:
        """https://github.com/owner/repo → (owner, repo)"""
        import re
        m = re.match(r"https?://github\.com/([^/]+)/([^/\s#?]+)", url)
        if not m:
            raise ValueError(f"無効なGitHub URL: {url}")
        return m.group(1), m.group(2).rstrip("/")

    def _get(self, url: str, **kwargs) -> dict | list:
        time.sleep(REQUEST_INTERVAL)
        resp = self.session.get(url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _fetch_repo_meta(self, owner: str, repo: str) -> dict:
        """
        リポジトリの基本的なメタ情報を取得して返す
        """
        try:
            data = self._get(f"https://api.github.com/repos/{owner}/{repo}")
            
            if not isinstance(data, dict):
                return {"name": repo, "full_name": f"{owner}/{repo}"}

            return {
                "name":          data.get("name"),
                "full_name":     data.get("full_name"),
                "description":   data.get("description"),
                "stars":         data.get("stargazers_count"),
                "forks":         data.get("forks_count"),
                "open_issues":   data.get("open_issues_count"),
                "language":      data.get("language"),
                "license":       data.get("license", {}).get("spdx_id") if isinstance(data.get("license"), dict) else None,
                "last_commit":   data.get("pushed_at"),
                "created_at":    data.get("created_at"),
                "topics":        data.get("topics", []),
                "default_branch":data.get("default_branch", "main"),
            }
        except Exception as e:
            logger.warning(f"[GitHub] メタ情報取得失敗: {e}")
            return {"name": repo, "full_name": f"{owner}/{repo}"}

    def _fetch_repo_languages(self, owner: str, repo: str) -> dict[str, float]:
        """
        リポジトリで使用されているプログラミング言語の割合（%）を計算して返す
        """
        try:
            # GitHub公式の言語専用APIを叩く
            data = self._get(f"https://api.github.com/repos/{owner}/{repo}/languages")
            if not isinstance(data, dict) or not data:
                return {}

            total_bytes = sum(data.values())
            if total_bytes == 0:
                return {}

            # バイト数をパーセンテージ（%）に変換して、小数点1桁で丸める
            languages_percentage = {
                lang: round((bytes_count / total_bytes) * 100, 1)
                for lang, bytes_count in data.items()
            }
            return languages_percentage
            
        except Exception as e:
            logger.warning(f"[GitHub] 言語割合の取得失敗: {e}")
            return {}

    def _fetch_file_tree(self, owner: str, repo: str) -> list[str]:
        try:
            data = self._get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD",
                params={"recursive": "1"}
            )
            
            if not isinstance(data, dict):
                return []

            return [
                item["path"]
                for item in data.get("tree", [])
                if isinstance(item, dict) and item.get("type") == "blob"
            ]
        except Exception as e:
            logger.error(f"[GitHub] ファイルツリー取得失敗: {e}")
            return []

    # ─────────────────────────────────────────────────────
    # 内部メソッド（ファイル取得・フィルタリング系）
    # ─────────────────────────────────────────────────────

    def _fetch_docs_and_licenses(self, owner: str, repo: str, file_tree: list[str]) -> dict[str, str]:
        """README等のドキュメントとライセンスを収集"""
        target_names = (
            self.LICENSE_FILENAMES
            | self.README_FILENAMES
            | self.CONTRIBUTING_FILENAMES
            | self.TERMS_FILENAMES
        )
        result = {}
        for path in file_tree:
            fname = path.split("/")[-1]
            if fname in target_names:
                content = self._fetch_raw(owner, repo, path)
                if content:
                    result[path] = content
        return result

    def _fetch_dependency_files(self, owner: str, repo: str, file_tree: list[str]) -> dict[str, str]:
        """package.json や requirements.txt などの依存関係ファイルを収集"""
        result = {}
        for path in file_tree:
            fname = path.split("/")[-1]
            # ルートディレクトリまたは直下の依存関係ファイルのみを狙う
            if fname in self.DEPENDENCY_FILENAMES and len(path.split("/")) <= 2:
                content = self._fetch_raw(owner, repo, path)
                if content:
                    result[path] = content
        return result

    def _filter_source_files(self, file_tree: list[str]) -> list[str]:
        """
        AIの学習用として、主要なソースコードやスクリプトを優先度順に並べて抽出。
        ※docsフォルダは学習の宝庫なので除外しない。
        """
        EXCLUDE_DIRS = {"test", "tests", "migrations", "alembic", "node_modules", ".git", "venv", "dist", "build"}
        EXCLUDE_FILES = {"setup.py", "setup.cfg", "conf.py", "package-lock.json", "yarn.lock"}

        scored = []
        for path in file_tree:
            if not path.endswith(self.TARGET_EXTENSIONS):
                continue
            parts = path.split("/")
            
            # 除外ディレクトリをスキップ
            if any(p.lower() in EXCLUDE_DIRS for p in parts[:-1]):
                continue
            if parts[-1] in EXCLUDE_FILES:
                continue
                
            # 優先度スコア（浅いディレクトリにあるものほど高いスコアにする）
            score = -len(parts)
            scored.append((score, path))

        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored]

    def _fetch_source_files(self, owner: str, repo: str, target_paths: list[str]) -> dict[str, str]:
        """ソースファイルをまとめて取得（上限あり）"""
        result = {}
        for path in target_paths[:MAX_SOURCE_FILES]:
            content = self._fetch_raw(owner, repo, path)
            if content:
                result[path] = content
        return result

    def _fetch_raw(self, owner: str, repo: str, path: str) -> Optional[str]:
        """raw.githubusercontent.com からファイル本文を取得"""
        try:
            time.sleep(REQUEST_INTERVAL)
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.text
                # サイズ制限
                if len(content.encode()) > MAX_FILE_BYTES:
                    content = content[:MAX_FILE_BYTES] + "\n...[サイズ制限により省略]"
                return content
        except Exception as e:
            logger.debug(f"[GitHub] {path} 取得失敗: {e}")
        return None

    # ─────────────────────────────────────────────────────
    # ★追加: Issue収集機能（AIの実践知識・小ネタ抽出用）
    # ─────────────────────────────────────────────────────
    
    def _fetch_closed_issues(self, owner: str, repo: str) -> dict[str, str]:
        """
        解決済みのIssue（バグ対応やQ&A）を取得する。
        AIが「こういうエラーが起きた時はこう直す」というTipsを学ぶための最高のエサ。
        """
        try:
            time.sleep(REQUEST_INTERVAL)
            # state=closed (解決済み) で sort=comments (議論が活発なもの) を取得
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            params = {
                "state": "closed",
                "sort": "comments",
                "direction": "desc",
                "per_page": MAX_ISSUES
            }
            resp = self.session.get(url, params=params, timeout=10)
            
            if resp.status_code != 200:
                return {}
                
            issues = resp.json()
            result = {}
            
            for issue in issues:
                # PR（Pull Request）はノイズになりやすいので除外
                if "pull_request" in issue:
                    continue
                    
                title = issue.get("title", "")
                body = issue.get("body", "")
                
                # タイトルと本文を結合（トークン節約のため文字数制限）
                content = f"【Issue: {title}】\n{body}"
                if len(content) > 3000:
                    content = content[:3000] + "\n...[省略]"
                    
                # IssueのURLをキーにして保存
                result[issue.get("html_url", f"issue_{issue.get('number')}")] = content
                
            return result
        except Exception as e:
            logger.warning(f"[GitHub] Issues取得失敗: {e}")
            return {}
    # ─────────────────────────────────────────────────────
    # ★新規追加: 検索・フィルタリング機能（ノイズ除去）
    # ─────────────────────────────────────────────────────

    def search_repos(self, query: str, max_results: int = 5) -> list[dict]:
        """GitHub Search APIを使ってリポジトリを検索する"""
        url = "https://api.github.com/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": max_results}
        try:
            time.sleep(REQUEST_INTERVAL)
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            
            # 必要なメタデータだけ抽出して返す
            return [
                {
                    "url": item["html_url"],
                    "owner": item["owner"]["login"],
                    "repo": item["name"],
                    "description": item.get("description") or "",
                    "topics": item.get("topics") or [],
                    "stars": item.get("stargazers_count", 0),
                }
                for item in items
            ]
        except Exception as e:
            logger.error(f"[GitHub Search] 検索失敗: {e}")
            return []

    def filter_video_dev_repos(self, repos: list[dict]) -> list[dict]:
        """
        取得したリポジトリ一覧から、動画開発に関係ないノイズ（ゲーム、アニメ等）を除外する。
        ここを通ったエリートURLだけを collect() に渡す仕組み。
        """
        # 歓迎するキーワード（これらが含まれていれば加点・優先）
        POSITIVE_KEYWORDS = {"video", "editor", "timeline", "ffmpeg", "caption", "canvas", "webgl", "media"}
        
        # 除外するキーワード（これらが含まれていたら問答無用で弾く）
        NEGATIVE_KEYWORDS = {"game", "minecraft", "anime", "discord", "bot", "course", "tutorial", "book", "pokemon", "vtuber"}

        filtered = []
        seen_urls = set()

        print(f"🧹 [Filter] {len(repos)}件のリポジトリのノイズ判定を開始...")

        for repo in repos:
            # 重複除外
            if repo["url"] in seen_urls:
                continue
            seen_urls.add(repo["url"])

            # 判定用に説明文とトピックを小文字にして結合
            text_to_check = (repo["description"] + " " + " ".join(repo["topics"])).lower()
            
            # 1. ネガティブチェック（1つでも含まれていたら除外）
            if any(neg in text_to_check for neg in NEGATIVE_KEYWORDS):
                print(f" 🚫 [NGワード検知] 除外: {repo['owner']}/{repo['repo']}")
                continue
                
            # 2. ポジティブチェック（動画開発に関するワードが含まれているか）
            if not any(pos in text_to_check for pos in POSITIVE_KEYWORDS):
                print(f"  [関連ワードなし] 除外: {repo['owner']}/{repo['repo']}")
                continue
                
            print(f" ✅ [合格] 採用: {repo['owner']}/{repo['repo']} (★{repo['stars']})")
            filtered.append(repo)
            
        return filtered