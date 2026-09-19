from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDomain:
    """Knowledge 1件分の検索用メタデータ。JSON本文は保持しない。"""

    name: str
    description: str
    file_paths: list[str]
    keywords: list[str]
    searchable_text: str = ""
    weight: float = 1.0
    domain_id: str = ""
    category: str = ""
    intents: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    message_examples: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    project_types: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    knowledge_types: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    priority: float = 0.0


@dataclass
class RouteResult:
    """KnowledgeRouter.route() の結果。"""

    file_paths: list[str]
    matched_domains: list[str]
    scores: dict[str, float] = field(default_factory=dict)
    score_details: dict[str, dict[str, float]] = field(default_factory=dict)

    def __iter__(self):
        return iter(self.file_paths)

    @property
    def matched_files(self) -> list[str]:
        """既存ChatOrchestratorとの互換名。"""

        return self.file_paths


class KnowledgeRouter:
    """
    ユーザー入力とIntent signalsから、関連Knowledgeを決定的に選択する。

    責務は「候補ファイルの選択」だけ。JSON本文のロード、プロンプト生成、
    Intent再解析、LLM実行は行わない。

    対応する主なJSON形式:
      - トップレベル: keywords / intent(s) / tags / message_examples
      - retrieval: keywords / intent(s) / tags / actions / targets ...
      - search_metadata: keywords / intents / tags / message_examples
      - domain: "react" または {"primary": "...", "secondary": [...]}
      - project_type / features / technologies
    """

    INDEX_FILES = {"index.json", "registry.json"}

    # これだけで選択が決まると誤判定しやすい語。完全に無視せず低く採点する。
    GENERIC_TERMS = {
        "ai",
        "app",
        "application",
        "code",
        "data",
        "json",
        "help",
        "アプリ",
        "コード",
        "データ",
        "作る",
        "作成",
        "生成",
        "教えて",
        "質問",
    }

    def __init__(
        self,
        knowledge_dir: str | Path,
        threshold: float = 1.0,
        top_k: int | None = 5,
    ) -> None:
        self.knowledge_dir = Path(knowledge_dir).expanduser().resolve()
        self.threshold = max(0.0, self._safe_float(threshold, 1.0))
        self.top_k = None if top_k is None else max(1, int(top_k))
        self.domains: list[KnowledgeDomain] = []
        self._load_knowledge_files()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self) -> None:
        logger.info(
            "🔄 [KnowledgeRouter] Knowledgeを再読み込みします: %s",
            self.knowledge_dir,
        )
        self._load_knowledge_files()

    def route(
        self,
        message: str,
        signals: dict[str, Any] | None = None,
    ) -> RouteResult:
        normalized_message = self._normalize_text(message)
        normalized_signals = self._normalize_signals(signals)

        all_scores: dict[str, float] = {}
        all_details: dict[str, dict[str, float]] = {}

        for domain in self.domains:
            score, details = self._score_domain(
                normalized_message,
                normalized_signals,
                domain,
            )
            all_scores[domain.domain_id] = round(score, 4)
            all_details[domain.domain_id] = details

        ranked = [
            domain
            for domain in self.domains
            if all_scores.get(domain.domain_id, 0.0) >= self.threshold
        ]
        ranked.sort(
            key=lambda domain: (
                -all_scores[domain.domain_id],
                domain.name.casefold(),
                domain.domain_id,
            )
        )

        # top_kは「ドメイン数」ではなく実際にロードするファイル数に適用する。
        selected: list[KnowledgeDomain] = []
        selected_path_count = 0
        seen_for_limit: set[str] = set()

        for domain in ranked:
            new_paths = [
                path for path in domain.file_paths if path not in seen_for_limit
            ]
            if not new_paths:
                continue
            if self.top_k is not None and selected_path_count >= self.top_k:
                break

            selected.append(domain)
            for path in new_paths:
                if self.top_k is not None and selected_path_count >= self.top_k:
                    break
                seen_for_limit.add(path)
                selected_path_count += 1

        file_paths: list[str] = []
        seen_paths: set[str] = set()
        matched_domains: list[str] = []
        seen_names: set[str] = set()

        for domain in selected:
            for file_path in domain.file_paths:
                if file_path in seen_paths:
                    continue
                if self.top_k is not None and len(file_paths) >= self.top_k:
                    break
                seen_paths.add(file_path)
                file_paths.append(file_path)

            if domain.name not in seen_names:
                seen_names.add(domain.name)
                matched_domains.append(domain.name)

        ranked_scores = {
            domain.domain_id: all_scores[domain.domain_id] for domain in selected
        }
        ranked_details = {
            domain.domain_id: all_details[domain.domain_id] for domain in selected
        }

        logger.info(
            "🎯 [KnowledgeRouter] message=%r matched=%s paths=%s scores=%s",
            message,
            matched_domains,
            file_paths,
            ranked_scores,
        )

        return RouteResult(
            file_paths=file_paths,
            matched_domains=matched_domains,
            scores=ranked_scores,
            score_details=ranked_details,
        )

    async def route_async(
        self,
        message: str,
        signals: dict[str, Any] | None = None,
    ) -> RouteResult:
        return self.route(message, signals)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _load_knowledge_files(self) -> None:
        self.domains = []

        if not self.knowledge_dir.exists():
            logger.warning(
                "⚠️ [KnowledgeRouter] Knowledgeディレクトリが存在しません: %s",
                self.knowledge_dir,
            )
            return

        if not self.knowledge_dir.is_dir():
            logger.warning(
                "⚠️ [KnowledgeRouter] knowledge_dirにはフォルダを指定してください: %s",
                self.knowledge_dir,
            )
            return

        loaded_files = 0
        skipped_files = 0

        for file_path in sorted(self.knowledge_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.name.casefold() in self.INDEX_FILES:
                continue

            suffix = file_path.suffix.casefold()
            if suffix not in {".json", ".md", ".mdx"}:
                continue

            before_count = len(self.domains)
            if suffix == ".json":
                self._parse_json_file(file_path)
            else:
                self._parse_markdown_frontmatter(file_path)

            if len(self.domains) > before_count:
                loaded_files += 1
            else:
                skipped_files += 1

        logger.info(
            "📚 [KnowledgeRouter] 登録完了: files=%d domains=%d skipped=%d dir=%s",
            loaded_files,
            len(self.domains),
            skipped_files,
            self.knowledge_dir,
        )

    def _parse_json_file(self, file_path: Path) -> None:
        try:
            with file_path.open("r", encoding="utf-8-sig") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            logger.warning(
                "❌ [KnowledgeRouter] JSON破損: %s / %s",
                file_path,
                error,
            )
            return
        except (OSError, UnicodeError) as error:
            logger.warning(
                "⚠️ [KnowledgeRouter] JSON読み込みエラー: %s / %s",
                file_path,
                error,
            )
            return

        if isinstance(data, dict):
            entries = [data]
        elif isinstance(data, list):
            entries = [item for item in data if isinstance(item, dict)]
        else:
            logger.debug("⏭ [KnowledgeRouter] dict/listではない: %s", file_path)
            return

        for index, entry in enumerate(entries):
            domain = self._build_json_domain(entry, file_path, index, len(entries))
            if domain is not None:
                self.domains.append(domain)

    def _build_json_domain(
        self,
        data: dict[str, Any],
        file_path: Path,
        entry_index: int,
        entry_count: int,
    ) -> KnowledgeDomain | None:
        retrieval = self._as_dict(data.get("retrieval"))
        search_metadata = self._as_dict(data.get("search_metadata"))
        routing = self._as_dict(data.get("routing"))

        rel_path = self._relative_path(file_path)
        raw_name = (
            data.get("name")
            or data.get("title")
            or data.get("id")
            or file_path.stem
        )
        name = str(raw_name).strip()
        if not name:
            return None

        domains = self._merge_unique(
            self._extract_domain_values(data.get("domain")),
            self._ensure_list(data.get("domains")),
            self._ensure_list(retrieval.get("domains")),
            self._ensure_list(search_metadata.get("domains")),
            self._ensure_list(routing.get("recommended_router_domains")),
        )

        category = str(
            data.get("category")
            or retrieval.get("category")
            or (domains[0] if domains else "")
        ).strip()
        description = str(
            data.get("description")
            or data.get("summary")
            or ""
        ).strip()

        keywords = self._merge_unique(
            self._ensure_list(data.get("keywords")),
            self._ensure_list(data.get("aliases")),
            self._ensure_list(data.get("topics")),
            self._ensure_list(retrieval.get("keywords")),
            self._ensure_list(search_metadata.get("keywords")),
        )
        intents = self._merge_unique(
            self._ensure_list(data.get("intent")),
            self._ensure_list(data.get("intents")),
            self._ensure_list(retrieval.get("intent")),
            self._ensure_list(retrieval.get("intents")),
            self._ensure_list(search_metadata.get("intent")),
            self._ensure_list(search_metadata.get("intents")),
        )
        tags = self._merge_unique(
            self._ensure_list(data.get("tags")),
            self._ensure_list(retrieval.get("tags")),
            self._ensure_list(search_metadata.get("tags")),
        )
        message_examples = self._merge_unique(
            self._ensure_list(data.get("message_examples")),
            self._ensure_list(retrieval.get("message_examples")),
            self._ensure_list(search_metadata.get("message_examples")),
        )
        actions = self._merge_unique(
            self._ensure_list(data.get("actions")),
            self._ensure_list(retrieval.get("actions")),
            self._ensure_list(search_metadata.get("actions")),
        )
        targets = self._merge_unique(
            self._ensure_list(data.get("targets")),
            self._ensure_list(retrieval.get("targets")),
            self._ensure_list(search_metadata.get("targets")),
        )
        project_types = self._merge_unique(
            self._ensure_list(data.get("project_type")),
            self._ensure_list(data.get("project_types")),
            self._ensure_list(retrieval.get("project_type")),
            self._ensure_list(retrieval.get("project_types")),
        )
        features = self._merge_unique(
            self._ensure_list(data.get("features")),
            self._ensure_list(retrieval.get("features")),
            self._ensure_list(search_metadata.get("features")),
        )
        technologies = self._merge_unique(
            self._ensure_list(data.get("technologies")),
            self._ensure_list(data.get("frameworks")),
            self._ensure_list(retrieval.get("technologies")),
            self._ensure_list(retrieval.get("frameworks")),
            self._ensure_list(search_metadata.get("technologies")),
        )
        knowledge_types = self._merge_unique(
            self._ensure_list(data.get("knowledge_type")),
            self._ensure_list(data.get("knowledge_types")),
            self._ensure_list(retrieval.get("knowledge_type")),
            self._ensure_list(search_metadata.get("knowledge_type")),
        )
        negative_keywords = self._merge_unique(
            self._ensure_list(data.get("negative_keywords")),
            self._ensure_list(data.get("exclude_keywords")),
            self._ensure_list(retrieval.get("negative_keywords")),
            self._ensure_list(retrieval.get("exclude_keywords")),
            self._ensure_list(search_metadata.get("negative_keywords")),
        )

        # name/category/domainはkeywordsへ混ぜず、別の重みで採点する。
        # これにより、同じ語が複数欄にあるだけで点数が水増しされない。
        searchable_text = " ".join(
            self._merge_unique(
                [name, category, description],
                keywords,
                domains,
                intents,
                tags,
                message_examples,
                actions,
                targets,
                project_types,
                features,
                technologies,
                knowledge_types,
            )
        )

        if not searchable_text.strip():
            logger.debug("⏭ [KnowledgeRouter] 検索対象なし: %s", file_path)
            return None

        raw_weight = data.get("weight", retrieval.get("weight", 1.0))
        raw_priority = data.get("priority", retrieval.get("priority", 0.0))
        weight = min(10.0, max(0.1, self._safe_float(raw_weight, 1.0)))
        priority = min(10.0, max(0.0, self._safe_float(raw_priority, 0.0)))
        domain_id = rel_path if entry_count == 1 else f"{rel_path}#{entry_index}"

        return KnowledgeDomain(
            name=name,
            description=description,
            file_paths=[rel_path],
            keywords=keywords,
            searchable_text=searchable_text,
            weight=weight,
            domain_id=domain_id,
            category=category,
            intents=intents,
            tags=tags,
            message_examples=message_examples,
            domains=domains,
            actions=actions,
            targets=targets,
            project_types=project_types,
            features=features,
            technologies=technologies,
            knowledge_types=knowledge_types,
            negative_keywords=negative_keywords,
            priority=priority,
        )

    # ------------------------------------------------------------------
    # Markdown frontmatter
    # ------------------------------------------------------------------

    def _parse_markdown_frontmatter(self, file_path: Path) -> None:
        try:
            content = file_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            logger.warning(
                "⚠️ [KnowledgeRouter] Markdown読み込みエラー: %s / %s",
                file_path,
                error,
            )
            return

        match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
        if not match:
            return

        metadata = self._parse_simple_frontmatter(match.group(1))
        # JSONと同じ変換器を使い、採点ルールの差をなくす。
        domain = self._build_json_domain(metadata, file_path, 0, 1)
        if domain is not None:
            self.domains.append(domain)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_domain(
        self,
        normalized_message: str,
        signals: dict[str, list[str]],
        domain: KnowledgeDomain,
    ) -> tuple[float, dict[str, float]]:
        details: dict[str, float] = {}

        message_groups: list[tuple[str, Iterable[str], float]] = [
            ("keyword", domain.keywords, 2.0),
            ("domain", domain.domains, 2.2),
            ("category", [domain.category], 1.8),
            ("tag", domain.tags, 1.2),
            ("intent_text", domain.intents, 1.4),
            ("action_text", domain.actions, 1.3),
            ("target_text", domain.targets, 1.3),
            ("project_type_text", domain.project_types, 1.5),
            ("feature_text", domain.features, 1.4),
            ("technology_text", domain.technologies, 1.6),
            ("knowledge_type_text", domain.knowledge_types, 1.2),
        ]

        # 同じ語がkeywordsとtagsの両方にあっても、最大の係数だけを採用する。
        best_term_factors: dict[str, tuple[str, float]] = {}
        for label, terms, factor in message_groups:
            for term in terms:
                normalized_term = self._normalize_text(term)
                if not normalized_term:
                    continue
                previous = best_term_factors.get(normalized_term)
                if previous is None or factor > previous[1]:
                    best_term_factors[normalized_term] = (label, factor)

        for term, (label, factor) in best_term_factors.items():
            if self._term_matches(normalized_message, term):
                value = factor * self._specificity(term) * domain.weight
                details[label] = details.get(label, 0.0) + value

        normalized_name = self._normalize_text(domain.name)
        if normalized_name and self._term_matches(normalized_message, normalized_name):
            details["name"] = 2.5 * self._specificity(normalized_name) * domain.weight
        elif normalized_name:
            # 「業績低下株の投資判断」というタイトルに対し、
            # 「業績低下株を買いたい」のような部分的な題名一致を救済する。
            overlap_length = self._longest_common_substring_length(
                normalized_message,
                normalized_name,
            )
            if overlap_length >= 3:
                details["name_overlap"] = (
                    min(2.0, overlap_length * 0.25) * domain.weight
                )

        for example in domain.message_examples:
            example_score = self._example_similarity(normalized_message, example)
            if example_score > 0:
                details["message_example"] = (
                    details.get("message_example", 0.0)
                    + example_score * domain.weight
                )

        signal_pairs = [
            ("intent", signals.get("intents", []), domain.intents, 3.0),
            ("domain_signal", signals.get("domains", []), domain.domains, 2.5),
            ("action_signal", signals.get("actions", []), domain.actions, 2.0),
            ("target_signal", signals.get("targets", []), domain.targets, 2.0),
            (
                "project_type_signal",
                signals.get("project_types", []),
                domain.project_types,
                2.5,
            ),
            ("feature_signal", signals.get("features", []), domain.features, 1.8),
            (
                "technology_signal",
                signals.get("technologies", []),
                domain.technologies,
                2.2,
            ),
            (
                "knowledge_type_signal",
                signals.get("knowledge_types", []),
                domain.knowledge_types,
                2.0,
            ),
            (
                "active_context",
                signals.get("active_context", []),
                self._merge_unique(domain.domains, [domain.category, domain.name]),
                2.0,
            ),
        ]

        for label, signal_values, knowledge_values, factor in signal_pairs:
            match_count = self._intersection_count(signal_values, knowledge_values)
            if match_count:
                details[label] = factor * min(match_count, 3) * domain.weight

        negative_hits = sum(
            1
            for term in domain.negative_keywords
            if self._term_matches(normalized_message, self._normalize_text(term))
        )
        if negative_hits:
            details["negative"] = -4.0 * negative_hits * domain.weight

        subtotal = sum(details.values())
        if subtotal > 0 and domain.priority:
            # priorityだけで無関係なKnowledgeがthresholdを超えないよう、関連時のみ加点。
            details["priority"] = min(domain.priority, 3.0) * 0.25

        score = max(0.0, sum(details.values()))
        rounded_details = {
            key: round(value, 4)
            for key, value in details.items()
            if value != 0
        }
        return score, rounded_details

    # ------------------------------------------------------------------
    # Signal normalization
    # ------------------------------------------------------------------

    def _normalize_signals(
        self,
        signals: dict[str, Any] | None,
    ) -> dict[str, list[str]]:
        if not isinstance(signals, dict):
            return {}

        intent_analysis = self._as_dict(signals.get("intent_analysis"))
        project_context = self._as_dict(signals.get("project_context"))
        sources = [signals, intent_analysis, project_context]

        aliases: dict[str, tuple[str, ...]] = {
            "intents": ("intent", "intents", "current_intent"),
            "domains": (
                "domain",
                "domains",
                "matched_domains",
                "target_categories",
            ),
            "actions": ("action", "actions"),
            "targets": ("target", "targets"),
            "project_types": ("project_type", "project_types"),
            "features": ("feature", "features"),
            "technologies": ("technology", "technologies", "framework"),
            "knowledge_types": ("knowledge_type", "knowledge_types"),
            "active_context": ("active_context", "current_topic"),
        }

        result: dict[str, list[str]] = {}
        for output_key, input_keys in aliases.items():
            values: list[str] = []
            for source in sources:
                for input_key in input_keys:
                    raw_value = source.get(input_key)
                    if input_key in {"domain", "domains"}:
                        values.extend(self._extract_domain_values(raw_value))
                    else:
                        values.extend(self._ensure_list(raw_value))
            result[output_key] = self._merge_unique(values)

        return result

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _extract_domain_values(self, value: Any) -> list[str]:
        if isinstance(value, dict):
            return self._merge_unique(
                self._ensure_list(value.get("primary")),
                self._ensure_list(value.get("secondary")),
                self._ensure_list(value.get("name")),
                self._ensure_list(value.get("id")),
            )
        return self._ensure_list(value)

    def _relative_path(self, file_path: Path) -> str:
        return str(file_path.relative_to(self.knowledge_dir)).replace("\\", "/")

    def _normalize_text(self, text: Any) -> str:
        if text is None:
            return ""
        value = unicodedata.normalize("NFKC", str(text)).casefold()
        value = value.replace("\u3000", " ")
        return re.sub(r"\s+", " ", value).strip()

    def _ensure_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.strip()
            return [value] if value else []
        if isinstance(value, (list, tuple, set)):
            result: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    # signalの要素が {"name": "react"} 形式でも扱う。
                    item = item.get("name") or item.get("id") or item.get("value")
                text = str(item).strip() if item is not None else ""
                if text:
                    result.append(text)
            return result
        if isinstance(value, dict):
            candidate = value.get("name") or value.get("id") or value.get("value")
            return self._ensure_list(candidate)
        text = str(value).strip()
        return [text] if text else []

    def _merge_unique(self, *lists: Iterable[Any]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for values in lists:
            for value in values:
                text = str(value).strip()
                normalized = self._normalize_text(text)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                result.append(text)
        return result

    @staticmethod
    def _safe_float(value: Any, default: float = 1.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _term_matches(self, normalized_text: str, normalized_term: str) -> bool:
        if not normalized_text or not normalized_term:
            return False

        # ASCIIの短語は部分一致にすると、go が django / logo に誤爆する。
        if re.fullmatch(r"[a-z0-9_+#.\-]+", normalized_term):
            pattern = rf"(?<![a-z0-9_+#]){re.escape(normalized_term)}(?![a-z0-9_+#])"
            return re.search(pattern, normalized_text) is not None

        return normalized_term in normalized_text

    def _specificity(self, normalized_term: str) -> float:
        compact = re.sub(r"[\s_\-./]+", "", normalized_term)
        length = len(compact)
        if normalized_term in self.GENERIC_TERMS:
            return 0.25
        if length <= 1:
            return 0.2
        if length == 2:
            return 0.65
        if length <= 4:
            return 1.0
        if length <= 10:
            return 1.25
        return 1.5

    def _example_similarity(self, normalized_message: str, example: Any) -> float:
        normalized_example = self._normalize_text(example)
        if not normalized_message or not normalized_example:
            return 0.0
        if normalized_example in normalized_message:
            return 3.0
        if len(normalized_message) >= 6 and normalized_message in normalized_example:
            return 2.0

        message_tokens = self._tokens(normalized_message)
        example_tokens = self._tokens(normalized_example)
        if not message_tokens or not example_tokens:
            return 0.0

        overlap = len(message_tokens & example_tokens)
        ratio = overlap / max(1, min(len(message_tokens), len(example_tokens)))
        return 1.5 * ratio if overlap >= 2 and ratio >= 0.4 else 0.0

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token
            for token in re.findall(
                r"[a-z0-9_+#.\-]+|[一-龯々ぁ-んァ-ヶー]{2,}",
                text,
            )
            if len(token) >= 2
        }

    def _intersection_count(
        self,
        left: Iterable[Any],
        right: Iterable[Any],
    ) -> int:
        left_values = {
            self._normalize_text(value) for value in left if self._normalize_text(value)
        }
        right_values = {
            self._normalize_text(value) for value in right if self._normalize_text(value)
        }
        return len(left_values & right_values)

    @staticmethod
    def _longest_common_substring_length(left: str, right: str) -> int:
        """短いタイトル用。連続して共通する文字列の最大長を返す。"""

        if not left or not right:
            return 0

        # タイトルは短いが、入力が極端に長い場合にも計算量を抑える。
        left = left[:1000]
        right = right[:200]
        previous = [0] * (len(right) + 1)
        longest = 0

        for left_char in left:
            current = [0]
            for index, right_char in enumerate(right, start=1):
                if left_char == right_char:
                    value = previous[index - 1] + 1
                    current.append(value)
                    longest = max(longest, value)
                else:
                    current.append(0)
            previous = current

        return longest

    def _parse_simple_frontmatter(self, text: str) -> dict[str, Any]:
        """依存ライブラリ不要の最小frontmatter parser。"""

        metadata: dict[str, Any] = {}
        lines = text.splitlines()
        index = 0

        while index < len(lines):
            line = lines[index].rstrip()
            if not line.strip() or line.strip().startswith("#") or ":" not in line:
                index += 1
                continue

            key, raw_value = line.split(":", 1)
            key = key.strip()
            raw_value = raw_value.strip()

            if not raw_value:
                items: list[str] = []
                cursor = index + 1
                while cursor < len(lines):
                    next_line = lines[cursor].strip()
                    if not next_line.startswith("- "):
                        break
                    item = next_line[2:].strip().strip("'\"")
                    if item:
                        items.append(item)
                    cursor += 1
                metadata[key] = items if items else ""
                index = cursor
                continue

            if raw_value.startswith("[") and raw_value.endswith("]"):
                inner = raw_value[1:-1].strip()
                metadata[key] = (
                    [item.strip().strip("'\"") for item in inner.split(",")]
                    if inner
                    else []
                )
            else:
                value = raw_value.strip("'\"")
                try:
                    metadata[key] = float(value) if "." in value else int(value)
                except ValueError:
                    metadata[key] = value
            index += 1

        return metadata


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KnowledgeRouter debug")
    parser.add_argument("knowledge_dir", type=Path)
    parser.add_argument("message")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=1.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    router = KnowledgeRouter(
        args.knowledge_dir,
        threshold=args.threshold,
        top_k=args.top_k,
    )
    result = router.route(args.message)
    print(json.dumps({
        "file_paths": result.file_paths,
        "matched_domains": result.matched_domains,
        "scores": result.scores,
        "score_details": result.score_details,
    }, ensure_ascii=False, indent=2))
