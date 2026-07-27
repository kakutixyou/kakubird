"""
huggingface_collector.py
========================
Hugging Face APIを使ってモデルカード（README.md）と
Spaces の app.py などを収集する Collector。

収集対象:
  - モデルカード（README.md：ライセンス・タグ・使用方法）
  - Spaces のソースコード（app.py 等）
  - モデル/Space のメタ情報（タグ・ライセンス・ダウンロード数）

出力: dict（github_collector と同じ形式 — orchestrator が同じ口で受け取れる）
"""

from __future__ import annotations

import os
import re
import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

REQUEST_INTERVAL = 0.3
MAX_FILE_BYTES   = 50_000


class HuggingFaceCollector:
    """
    使い方:
        collector = HuggingFaceCollector()

        # モデルの場合
        collected = collector.collect("https://huggingface.co/bert-base-uncased")

        # Spaceの場合
        collected = collector.collect("https://huggingface.co/spaces/gradio/hello_world")

        # どちらも同じキーで返る
        collected["file_tree"]        # ["README.md", "app.py", ...]
        collected["license_files"]    # {"README.md": "..."}
        collected["source_files"]     # {"app.py": "..."}
        collected["repo_meta"]        # {"name": "...", "pipeline_tag": "...", ...}
    """

    HF_API = "https://huggingface.co/api"
    HF_RAW = "https://huggingface.co"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("HF_TOKEN")
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    # ─────────────────────────────────────────────────────
    # パブリックメソッド
    # ─────────────────────────────────────────────────────

    def collect(self, url: str) -> dict:
        """
        Hugging Face の URL から全情報を収集。
        モデル / Space を自動判別する。
        """
        repo_type, repo_id = self._parse_url(url)
        logger.info(f"[HuggingFace] 収集開始: type={repo_type} id={repo_id}")

        if repo_type == "space":
            return self._collect_space(repo_id)
        else:
            return self._collect_model(repo_id)

    # ─────────────────────────────────────────────────────
    # モデル収集
    # ─────────────────────────────────────────────────────

    def _collect_model(self, repo_id: str) -> dict:
        meta     = self._fetch_model_meta(repo_id)
        file_tree = self._fetch_model_tree(repo_id)

        # ライセンス情報はモデルカード（README.md）に埋め込まれている
        readme_content = self._fetch_raw(repo_id, "README.md", repo_type="model")
        license_files = {}
        if readme_content:
            license_files["README.md"] = readme_content

        # 追加ライセンスファイル
        for fname in ["LICENSE", "LICENSE.md", "LICENCE", "利用規約.md", "TERMS.md"]:
            if fname in file_tree:
                content = self._fetch_raw(repo_id, fname, repo_type="model")
                if content:
                    license_files[fname] = content

        # Pythonソースファイル（config・モデル定義等）
        source_files = {}
        py_candidates = [f for f in file_tree if f.endswith(".py")][:10]
        for fname in py_candidates:
            content = self._fetch_raw(repo_id, fname, repo_type="model")
            if content:
                source_files[fname] = content

        return {
            "file_tree":        file_tree,
            "license_files":    license_files,
            "source_files":     source_files,
            "requirements_txt": self._fetch_raw(repo_id, "requirements.txt", "model"),
            "repo_meta":        meta,
        }

    def _fetch_model_meta(self, repo_id: str) -> dict:
        try:
            time.sleep(REQUEST_INTERVAL)
            resp = self.session.get(f"{self.HF_API}/models/{repo_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "name":           data.get("id"),
                "source":         "huggingface_model",
                "pipeline_tag":   data.get("pipeline_tag"),
                "tags":           data.get("tags", []),
                "license":        self._extract_license_tag(data.get("tags", [])),
                "downloads":      data.get("downloads"),
                "likes":          data.get("likes"),
                "last_modified":  data.get("lastModified"),
                "library_name":   data.get("library_name"),
                "language":       data.get("cardData", {}).get("language") if data.get("cardData") else None,
            }
        except Exception as e:
            logger.warning(f"[HuggingFace] モデルメタ取得失敗: {e}")
            return {"name": repo_id, "source": "huggingface_model"}

    def _fetch_model_tree(self, repo_id: str) -> list[str]:
        try:
            time.sleep(REQUEST_INTERVAL)
            resp = self.session.get(
                f"{self.HF_API}/models/{repo_id}",
                params={"blobs": "true"},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            siblings = data.get("siblings", [])
            return [s["rfilename"] for s in siblings if "rfilename" in s]
        except Exception as e:
            logger.warning(f"[HuggingFace] モデルツリー取得失敗: {e}")
            return []

    # ─────────────────────────────────────────────────────
    # Space 収集
    # ─────────────────────────────────────────────────────

    def _collect_space(self, repo_id: str) -> dict:
        meta      = self._fetch_space_meta(repo_id)
        file_tree = self._fetch_space_tree(repo_id)

        # Spaceのライセンスも README.md に記載されることが多い
        license_files = {}
        readme = self._fetch_raw(repo_id, "README.md", repo_type="space")
        if readme:
            license_files["README.md"] = readme
        for fname in ["LICENSE", "LICENSE.md", "利用規約.md"]:
            if fname in file_tree:
                c = self._fetch_raw(repo_id, fname, "space")
                if c:
                    license_files[fname] = c

        # Spaceのメインファイル（app.py が最重要）
        PRIORITY = ["app.py", "main.py", "server.py"]
        source_files = {}

        # 優先ファイルを先に取得
        for fname in PRIORITY:
            if fname in file_tree:
                content = self._fetch_raw(repo_id, fname, "space")
                if content:
                    source_files[fname] = content

        # 残りのPythonファイルも取得（上限あり）
        remaining = [
            f for f in file_tree
            if f.endswith(".py") and f not in source_files
        ]
        for fname in remaining[:8]:
            content = self._fetch_raw(repo_id, fname, "space")
            if content:
                source_files[fname] = content

        return {
            "file_tree":        file_tree,
            "license_files":    license_files,
            "source_files":     source_files,
            "requirements_txt": self._fetch_raw(repo_id, "requirements.txt", "space"),
            "repo_meta":        meta,
        }

    def _fetch_space_meta(self, repo_id: str) -> dict:
        try:
            time.sleep(REQUEST_INTERVAL)
            resp = self.session.get(f"{self.HF_API}/spaces/{repo_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "name":          data.get("id"),
                "source":        "huggingface_space",
                "sdk":           data.get("cardData", {}).get("sdk") if data.get("cardData") else None,
                "tags":          data.get("tags", []),
                "license":       self._extract_license_tag(data.get("tags", [])),
                "likes":         data.get("likes"),
                "last_modified": data.get("lastModified"),
                "runtime":       data.get("runtime", {}).get("stage") if data.get("runtime") else None,
            }
        except Exception as e:
            logger.warning(f"[HuggingFace] Spaceメタ取得失敗: {e}")
            return {"name": repo_id, "source": "huggingface_space"}

    def _fetch_space_tree(self, repo_id: str) -> list[str]:
        try:
            time.sleep(REQUEST_INTERVAL)
            resp = self.session.get(f"{self.HF_API}/spaces/{repo_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            siblings = data.get("siblings", [])
            return [s["rfilename"] for s in siblings if "rfilename" in s]
        except Exception as e:
            logger.warning(f"[HuggingFace] Spaceツリー取得失敗: {e}")
            return []

    # ─────────────────────────────────────────────────────
    # 共通ユーティリティ
    # ─────────────────────────────────────────────────────

    def _parse_url(self, url: str) -> tuple[str, str]:
        """
        https://huggingface.co/spaces/owner/repo → ("space", "owner/repo")
        https://huggingface.co/owner/model        → ("model", "owner/model")
        """
        m = re.match(r"https?://huggingface\.co/spaces/([^/\s]+/[^/\s]+)", url)
        if m:
            return "space", m.group(1)
        m = re.match(r"https?://huggingface\.co/([^/\s]+/[^/\s]+)", url)
        if m:
            return "model", m.group(1)
        raise ValueError(f"無効なHugging Face URL: {url}")

    def _fetch_raw(self, repo_id: str, filename: str, repo_type: str = "model") -> Optional[str]:
        """HuggingFace の resolve エンドポイントからファイル本文を取得"""
        try:
            time.sleep(REQUEST_INTERVAL)
            if repo_type == "space":
                url = f"{self.HF_RAW}/spaces/{repo_id}/resolve/main/{filename}"
            else:
                url = f"{self.HF_RAW}/{repo_id}/resolve/main/{filename}"

            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.text
                if len(content.encode()) > MAX_FILE_BYTES:
                    content = content[:MAX_FILE_BYTES] + "\n...[サイズ制限により省略]"
                return content
        except Exception as e:
            logger.debug(f"[HuggingFace] {filename} 取得失敗: {e}")
        return None

    @staticmethod
    def _extract_license_tag(tags: list[str]) -> Optional[str]:
        """タグリストからライセンス情報を抽出 (例: "license:mit" → "MIT")"""
        for tag in tags:
            if tag.startswith("license:"):
                return tag.replace("license:", "").upper()
        return None