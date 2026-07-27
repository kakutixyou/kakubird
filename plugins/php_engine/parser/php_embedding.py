"""
plugins/php_engine/parser/php_embedding.py

knowledgeフォルダーのJSONをベクトル化し、
ユーザー入力に最も近いルール・パターンを検索するRAGモジュール。

依存: sentence-transformers, numpy, scikit-learn
インストール: pip install sentence-transformers numpy scikit-learn
"""

from __future__ import annotations

import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────
# 設定
# ────────────────────────────────────────────

KNOWLEDGE_DIR  = Path(__file__).parent.parent / "knowledge"
CACHE_DIR      = Path(__file__).parent.parent / "generated" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 使用するEmbeddingモデル（ローカル・無料）
# 日本語混じりのテキストにも対応
EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"

# 検索時に返す最大件数のデフォルト値
DEFAULT_TOP_K = 5

# knowledgeファイル一覧
KNOWLEDGE_FILES = {
    "security": "php_security.json",
    "patterns": "php_patterns.json",
    "basics":   "php_basics.json",
    "sql":      "php_sql_examples.json",
}


# ────────────────────────────────────────────
# ドキュメント展開
# ────────────────────────────────────────────

def _flatten_security(data: dict) -> list[dict]:
    """
    php_security.jsonの構造をフラットなドキュメントリストに展開する。
    各ルールを1つのドキュメントとして扱う。
    """
    docs = []
    for domain_key, domain in data.items():
        if domain_key in ("meta", "scoring_guide"):
            continue
        domain_label = domain.get("label", domain_key)
        for rule in domain.get("rules", []):
            # 検索用テキスト: タイトル・説明・badパターンを連結
            bad_text  = " ".join(rule.get("bad_patterns", []))
            good_text = " ".join(rule.get("good_patterns", []))
            search_text = (
                f"{rule.get('title', '')} "
                f"{rule.get('description', '')} "
                f"{bad_text} {good_text}"
            ).strip()

            docs.append({
                "id":          rule.get("id", ""),
                "domain":      domain_label,
                "domain_key":  domain_key,
                "severity":    rule.get("severity", "medium"),
                "title":       rule.get("title", ""),
                "description": rule.get("description", ""),
                "bad_patterns":  rule.get("bad_patterns", []),
                "check_absence_of": rule.get("check_absence_of", []),
                "good_patterns": rule.get("good_patterns", []),
                "fix_template":  rule.get("fix_template", ""),
                "references":    rule.get("references", []),
                "source_file": "php_security.json",
                "search_text": search_text,
            })
    return docs


def _flatten_generic(data: dict | list, source_file: str) -> list[dict]:
    """
    php_patterns.json / php_basics.json / php_sql_examples.json など
    汎用的な構造をフラット化する。
    トップレベルがlist / dict どちらでも対応。
    """
    docs = []
    items: list[Any] = data if isinstance(data, list) else list(data.values())

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        # title/name/labelのいずれかをタイトルとして使う
        title = (
            item.get("title")
            or item.get("name")
            or item.get("label")
            or f"item_{i}"
        )
        description = (
            item.get("description")
            or item.get("summary")
            or item.get("content")
            or ""
        )
        example = item.get("example") or item.get("code") or item.get("sql") or ""
        if isinstance(example, list):
            example = " ".join(str(e) for e in example)

        search_text = f"{title} {description} {example}".strip()

        docs.append({
            "id":          item.get("id", f"{source_file}_{i}"),
            "title":       title,
            "description": description,
            "example":     example,
            "tags":        item.get("tags", []),
            "source_file": source_file,
            "search_text": search_text,
            **{k: v for k, v in item.items()
               if k not in ("id", "title", "description", "example", "tags")},
        })
    return docs


def load_knowledge_docs() -> list[dict]:
    """
    knowledgeフォルダーの全JSONを読み込み、フラットなdocリストとして返す。
    ファイルが存在しない場合はスキップする。
    """
    all_docs: list[dict] = []

    for key, filename in KNOWLEDGE_FILES.items():
        path = KNOWLEDGE_DIR / filename
        if not path.exists():
            logger.warning(f"[php_embedding] {filename} が見つかりません。スキップします。")
            continue

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if key == "security":
            docs = _flatten_security(data)
        else:
            docs = _flatten_generic(data, filename)

        logger.info(f"[php_embedding] {filename}: {len(docs)} ドキュメントを読み込みました")
        all_docs.extend(docs)

    return all_docs


# ────────────────────────────────────────────
# キャッシュ管理
# ────────────────────────────────────────────

def _cache_key(docs: list[dict]) -> str:
    """ドキュメントリストのMD5をキャッシュキーとして使う。"""
    content = json.dumps([d["search_text"] for d in docs], ensure_ascii=False)
    return hashlib.md5(content.encode()).hexdigest()


def _cache_path(cache_key: str) -> Path:
    return CACHE_DIR / f"embeddings_{cache_key}.npz"


def _load_cache(cache_key: str) -> np.ndarray | None:
    path = _cache_path(cache_key)
    if path.exists():
        logger.info(f"[php_embedding] キャッシュを使用: {path.name}")
        data = np.load(path)
        return data["embeddings"]
    return None


def _save_cache(cache_key: str, embeddings: np.ndarray) -> None:
    path = _cache_path(cache_key)
    np.savez(path, embeddings=embeddings)
    logger.info(f"[php_embedding] キャッシュを保存: {path.name}")


# ────────────────────────────────────────────
# Embeddingエンジン
# ────────────────────────────────────────────

class PhpEmbeddingEngine:
    """
    knowledgeのRAG検索エンジン。

    使い方:
        engine = PhpEmbeddingEngine()
        results = engine.search("パスワードをmd5でハッシュ化しています", top_k=3)
        for r in results:
            print(r["score"], r["doc"]["title"])
    """

    def __init__(self, model_name: str = EMBED_MODEL_NAME):
        self._model_name   = model_name
        self._model        = None   # 遅延ロード
        self._docs:        list[dict]   = []
        self._embeddings:  np.ndarray | None = None
        self._cache_key:   str = ""

    # ── モデルの遅延ロード ──────────────────────

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"[php_embedding] モデルをロード中: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
                logger.info("[php_embedding] モデルロード完了")
            except ImportError:
                raise ImportError(
                    "sentence-transformers が必要です。\n"
                    "pip install sentence-transformers"
                )
        return self._model

    # ── ベクトル化 ─────────────────────────────

    def _embed(self, texts: list[str]) -> np.ndarray:
        """
        multilingual-e5シリーズはクエリに"query: "、
        コーパスに"passage: "プレフィックスを付けると精度が上がる。
        """
        model = self._get_model()
        prefixed = [f"passage: {t}" for t in texts]
        vecs = model.encode(prefixed, show_progress_bar=False, normalize_embeddings=True)
        return np.array(vecs, dtype=np.float32)

    def _embed_query(self, query: str) -> np.ndarray:
        model = self._get_model()
        vec = model.encode(
            [f"query: {query}"],
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.array(vec, dtype=np.float32)

    # ── インデックス構築 ───────────────────────

    def build_index(self, force: bool = False) -> None:
        """
        knowledgeを読み込んでEmbeddingインデックスを構築する。
        キャッシュが存在すれば再計算しない（force=Trueで強制再構築）。
        """
        self._docs = load_knowledge_docs()
        if not self._docs:
            logger.warning("[php_embedding] ドキュメントが0件です。knowledgeフォルダーを確認してください。")
            return

        texts = [d["search_text"] for d in self._docs]
        self._cache_key = _cache_key(self._docs)

        if not force:
            cached = _load_cache(self._cache_key)
            if cached is not None:
                self._embeddings = cached
                return

        logger.info(f"[php_embedding] {len(texts)} 件のドキュメントをベクトル化中...")
        t0 = time.time()
        self._embeddings = self._embed(texts)
        elapsed = time.time() - t0
        logger.info(f"[php_embedding] ベクトル化完了: {elapsed:.1f}秒")

        _save_cache(self._cache_key, self._embeddings)

    def _ensure_index(self) -> None:
        if self._embeddings is None:
            self.build_index()

    # ── 検索 ──────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        domain_filter: str | None = None,
        severity_filter: list[str] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """
        クエリに近いドキュメントをコサイン類似度で検索する。

        Args:
            query:            検索クエリ（ユーザー入力やコード片）
            top_k:            返す件数
            domain_filter:    "sql_injection" など特定ドメインに絞る
            severity_filter:  ["critical", "high"] など重要度で絞る
            score_threshold:  この類似度以下は除外（0.0〜1.0）

        Returns:
            [{"score": float, "doc": dict}, ...] を類似度降順で返す
        """
        self._ensure_index()

        if not self._docs:
            return []

        # クエリをベクトル化
        q_vec = self._embed_query(query)  # shape: (1, dim)

        # コサイン類似度（正規化済みなので内積=コサイン類似度）
        scores: np.ndarray = (self._embeddings @ q_vec.T).flatten()

        # フィルタリング対象インデックスを絞る
        indices = list(range(len(self._docs)))
        if domain_filter:
            indices = [
                i for i in indices
                if self._docs[i].get("domain_key") == domain_filter
                or self._docs[i].get("domain") == domain_filter
            ]
        if severity_filter:
            indices = [
                i for i in indices
                if self._docs[i].get("severity") in severity_filter
            ]

        # スコア降順ソート
        sorted_indices = sorted(indices, key=lambda i: scores[i], reverse=True)

        results = []
        for i in sorted_indices[:top_k]:
            score = float(scores[i])
            if score < score_threshold:
                continue
            results.append({
                "score": round(score, 4),
                "doc":   self._docs[i],
            })

        return results

    # ── ルールベース採点との併用 ───────────────

    def review_code(
        self,
        code: str,
        top_k: int = 5,
    ) -> dict:
        """
        PHPコードをレビューし、関連するセキュリティルールと
        類似スコアをまとめて返す。
        Phase Aの補助として使う。

        Returns:
            {
                "query": str,
                "hits": [{"score": float, "doc": dict}],
                "critical_hits": [{"score": float, "doc": dict}],
                "summary": str,
            }
        """
        hits = self.search(
            query=code,
            top_k=top_k,
            domain_filter=None,
        )

        critical_hits = [
            h for h in hits
            if h["doc"].get("severity") == "critical" and h["score"] >= 0.5
        ]

        # サマリー文字列（AIプロンプトに渡す用）
        lines = []
        for h in hits:
            doc = h["doc"]
            lines.append(
                f"[{doc.get('severity','?').upper()}] {doc.get('title','')} "
                f"(score={h['score']}) — {doc.get('fix_template','')}"
            )
        summary = "\n".join(lines) if lines else "関連するセキュリティルールは見つかりませんでした。"

        return {
            "query":         code[:200] + "..." if len(code) > 200 else code,
            "hits":          hits,
            "critical_hits": critical_hits,
            "summary":       summary,
        }

    # ── テンプレート選択支援 ───────────────────

    def suggest_template(self, user_input: str) -> str | None:
        """
        ユーザー入力からtemplatesフォルダーの最適なテンプレートを推薦する。
        chat_orchestratorのPhase Bで呼び出す用。

        Returns: "crud" | "api" | "login" | None
        """
        keywords_map = {
            "crud":  ["一覧", "登録", "編集", "削除", "CRUD", "管理画面", "データ操作"],
            "api":   ["API", "REST", "JSON", "エンドポイント", "fetch", "axios"],
            "login": ["ログイン", "認証", "セッション", "パスワード", "サインイン", "sign in"],
        }
        scores_map: dict[str, int] = {k: 0 for k in keywords_map}
        text_lower = user_input.lower()

        for tmpl, keywords in keywords_map.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    scores_map[tmpl] += 1

        best = max(scores_map, key=lambda k: scores_map[k])
        return best if scores_map[best] > 0 else None

    # ── キャッシュ操作 ─────────────────────────

    def clear_cache(self) -> None:
        """生成済みキャッシュファイルをすべて削除する。"""
        for f in CACHE_DIR.glob("embeddings_*.npz"):
            f.unlink()
            logger.info(f"[php_embedding] キャッシュ削除: {f.name}")
        self._embeddings = None
        self._cache_key  = ""

    def rebuild_index(self) -> None:
        """knowledgeが更新されたとき、キャッシュを無視して再構築する。"""
        self.build_index(force=True)

    # ── デバッグ用 ─────────────────────────────

    def stats(self) -> dict:
        """インデックスの統計情報を返す。"""
        return {
            "total_docs":   len(self._docs),
            "embed_shape":  list(self._embeddings.shape) if self._embeddings is not None else None,
            "cache_key":    self._cache_key,
            "model":        self._model_name,
            "sources":      list({d.get("source_file", "") for d in self._docs}),
        }


# ────────────────────────────────────────────
# シングルトン
# ────────────────────────────────────────────

_engine: PhpEmbeddingEngine | None = None


def get_engine() -> PhpEmbeddingEngine:
    """
    アプリ起動時に一度だけ初期化するシングルトンを返す。
    php_loader.pyからはこれを呼び出す。
    """
    global _engine
    if _engine is None:
        _engine = PhpEmbeddingEngine()
        _engine.build_index()
    return _engine


# ────────────────────────────────────────────
# CLI（動作確認用）
# ────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="php_embedding 動作確認ツール")
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("search", help="クエリで検索")
    s.add_argument("query", help="検索クエリ")
    s.add_argument("--top-k", type=int, default=5)
    s.add_argument("--domain", default=None)
    s.add_argument("--severity", nargs="*", default=None)

    sub.add_parser("stats",   help="インデックス統計を表示")
    sub.add_parser("rebuild", help="キャッシュを再構築")

    r = sub.add_parser("review", help="コードスニペットをレビュー")
    r.add_argument("code", help="レビュー対象のPHPコード")

    args = parser.parse_args()
    engine = get_engine()

    if args.cmd == "search":
        results = engine.search(
            args.query,
            top_k=args.top_k,
            domain_filter=args.domain,
            severity_filter=args.severity,
        )
        for res in results:
            doc = res["doc"]
            print(f"\n[{res['score']:.3f}] [{doc.get('severity','?').upper()}] {doc.get('title','')}")
            print(f"  {doc.get('description','')}")
            if doc.get("fix_template"):
                print(f"  修正: {doc['fix_template']}")

    elif args.cmd == "stats":
        import pprint
        pprint.pprint(engine.stats())

    elif args.cmd == "rebuild":
        engine.rebuild_index()
        print("再構築完了")

    elif args.cmd == "review":
        result = engine.review_code(args.code)
        print("\n=== レビュー結果 ===")
        print(result["summary"])
        if result["critical_hits"]:
            print("\n⚠ CRITICAL ヒット:")
            for h in result["critical_hits"]:
                print(f"  {h['doc']['title']}")

    else:
        parser.print_help()