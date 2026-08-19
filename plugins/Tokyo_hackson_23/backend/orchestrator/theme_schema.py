#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theme_schema.py
────────────────
themes/*.yaml の共通スキーマ定義とバリデーション。
23区おすすめ診断アプリ(PILLAR_META)および研究モード(分析・スコアリング)の
データ構造に対応し、typoや値の範囲外を実行前に厳密検出します。
"""

from __future__ import annotations
from pathlib import Path

# 許可されるグループ（基礎インフラ／暮らし・商業／地域単位）
ALLOWED_GROUPS = {"all", "base", "livability", "都", "区", "市町村"}

# スコア計算時の分母（標準化の単位）
ALLOWED_DENOMINATORS = {
    "population_10k",  # 人口1万人あたり
    "area_sqkm",       # 面積1km²あたり
    "children_0_5",    # 0〜5歳人口あたり (子育て等)
    "none",            # 生データ・絶対数
}

# スナップショット取得対象
ALLOWED_SNAPSHOT_TARGETS = {"metadata", "download_url", "web_page"}

# 必須キー
REQUIRED_KEYS = {"name", "label", "queries", "formats"}

# オプションキーとデフォルト値
OPTIONAL_KEYS_WITH_DEFAULTS = {
    "description": "",
    "emoji": "📌",
    # "emoji" は "emoji" の別名として過去のテーマ定義(disaster.yaml等)との互換のために受け付ける。
    # 新規テーマは "emoji" を使うこと。両方指定された場合は emoji を優先する。
    "emoji": None,
    # normalize_schema.build_theme_snapshot() に渡す metric のキー。
    # None の場合は呼び出し側で theme 名をそのまま使う。
    "metric_key": None,
    # metric_key に対応する数値フィールドの候補カラム名（例: ["公園面積", "面積"]）。
    # services/field_mapper.py がデフォルト候補より優先して検索する。
    "metric_fields": None,
    "group": "all",
    "chip": True,                      # フロントのファーストビュー(チップ)に表示するか
    "denominator": "population_10k",   # スコア計算時の分母
    "weight": 1.0,                     # 分析時のデフォルト重み (0.0〜2.0)
    "maps_query_template": "{city} {keyword}",  # Google Maps検索用テンプレート
    "rows": 200,
    "max_packages": 2000,
    "batch_size": 100,
    "output_dir": None,
    # 証跡・スナップショット設定
    "enable_snapshot": False,
    "snapshot_targets": ["metadata"],
}


class ThemeConfigError(ValueError):
    """テーマ設定(yaml)が不正な場合に送出する例外。issues に全不備を格納する。"""

    def __init__(self, theme_name: str, issues: list[str]):
        self.theme_name = theme_name
        self.issues = issues
        message = f"テーマ設定が不正です (theme={theme_name}):\n" + "\n".join(f"  - {i}" for i in issues)
        super().__init__(message)


def resolve_effective_emoji(cfg: dict) -> str:
    """emoji と emoji の両方が定義されている場合の解決規則を一箇所にまとめる。"""
    emoji = cfg.get("emoji")
    if emoji:
        return emoji
    emoji = cfg.get("emoji")
    if emoji:
        return emoji
    return OPTIONAL_KEYS_WITH_DEFAULTS["emoji"]


def resolve_effective_metric_key(theme_name: str, cfg: dict) -> str:
    """metric_key が未指定なら theme 名をそのまま使う。"""
    return cfg.get("metric_key") or theme_name


def validate_theme_config(theme_name: str, cfg: dict) -> None:
    """型・値の範囲を厳密にチェックする。不備は集約して一度にまとめて報告する。"""
    issues: list[str] = []

    # 未知のキー検出
    known_keys = REQUIRED_KEYS | set(OPTIONAL_KEYS_WITH_DEFAULTS.keys())
    unknown = set(cfg.keys()) - known_keys
    if unknown:
        issues.append(f"未知のキーがあります(typoの可能性): {sorted(unknown)}")

    # 必須キー存在チェック
    for key in REQUIRED_KEYS:
        if key not in cfg:
            issues.append(f"必須キー '{key}' がありません")

    # name / label (文字列チェック)
    for str_key in ["name", "label"]:
        val = cfg.get(str_key)
        if val is not None and (not isinstance(val, str) or not val.strip()):
            issues.append(f"'{str_key}' は空でない文字列である必要があります")

    # emoji / emoji (絵文字・記号チェック。どちらか一方が有効な文字列であればOK)
    effective_emoji = resolve_effective_emoji(cfg)
    if not isinstance(effective_emoji, str) or not effective_emoji.strip():
        issues.append("'emoji'（または互換キー 'emoji'）は1文字以上の文字列である必要があります")

    # metric_key (指定されている場合のみ文字列チェック)
    metric_key = cfg.get("metric_key")
    if metric_key is not None and (not isinstance(metric_key, str) or not metric_key.strip()):
        issues.append(f"'metric_key' は空でない文字列である必要があります(値: {metric_key!r})")

    # metric_fields (指定されている場合のみリスト検証)
    metric_fields = cfg.get("metric_fields")
    if metric_fields is not None:
        if not isinstance(metric_fields, list) or not metric_fields:
            issues.append("'metric_fields' は1件以上を含むリストである必要があります")
        else:
            for i, mf in enumerate(metric_fields):
                if not isinstance(mf, str) or not mf.strip():
                    issues.append(f"'metric_fields[{i}]' は空でない文字列である必要があります(値: {mf!r})")

    # queries (リスト検証)
    queries = cfg.get("queries")
    if queries is not None:
        if not isinstance(queries, list) or not queries:
            issues.append("'queries' は1件以上を含むリストである必要があります")
        else:
            for i, q in enumerate(queries):
                if not isinstance(q, str) or not q.strip():
                    issues.append(f"'queries[{i}]' は空でない文字列である必要があります(値: {q!r})")

    # formats (リスト検証 & ASCIIチェック)
    formats = cfg.get("formats")
    if formats is not None:
        if not isinstance(formats, list) or not formats:
            issues.append("'formats' は1件以上を含むリストである必要があります")
        else:
            for i, f in enumerate(formats):
                if not isinstance(f, str) or not f.strip():
                    issues.append(f"'formats[{i}]' は空でない文字列である必要があります(値: {f!r})")
                elif not f.strip().isascii():
                    issues.append(f"'formats[{i}]' はASCII表記(CSV, XLSX, JSONなど)である必要があります(値: {f!r})")

    # group (グループ検証)
    group = cfg.get("group", "all")
    if group not in ALLOWED_GROUPS:
        issues.append(f"'group' は {sorted(ALLOWED_GROUPS)} のいずれかである必要があります(値: {group!r})")

    # denominator (評価分母の検証)
    denominator = cfg.get("denominator", "population_10k")
    if denominator not in ALLOWED_DENOMINATORS:
        issues.append(f"'denominator' は {sorted(ALLOWED_DENOMINATORS)} のいずれかである必要があります(値: {denominator!r})")

    # chip / enable_snapshot (ブール値検証)
    for bool_key in ["chip", "enable_snapshot"]:
        val = cfg.get(bool_key)
        if val is not None and not isinstance(val, bool):
            issues.append(f"'{bool_key}' は真偽値(True/False)である必要があります")

    # weight (重み付け 0.0 〜 2.0 の数値検証)
    weight = cfg.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not (0.0 <= weight <= 2.0):
        issues.append(f"'weight' は 0.0〜2.0 の数値である必要があります(値: {weight!r})")

    # 数値範囲チェック (rows, max_packages, batch_size)
    rows = cfg.get("rows", 200)
    if not isinstance(rows, int) or isinstance(rows, bool) or not (1 <= rows <= 1000):
        issues.append(f"'rows' は 1〜1000 の整数である必要があります(値: {rows!r})")

    max_packages = cfg.get("max_packages", 2000)
    if not isinstance(max_packages, int) or isinstance(max_packages, bool) or max_packages < 1:
        issues.append(f"'max_packages' は1以上の整数である必要があります(値: {max_packages!r})")

    batch_size = cfg.get("batch_size", 100)
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or not (1 <= batch_size <= 5000):
        issues.append(f"'batch_size' は 1〜5000 の整数である必要があります(値: {batch_size!r})")

    # snapshot_targets (リストおよび許容値チェック)
    snapshot_targets = cfg.get("snapshot_targets", ["metadata"])
    if not isinstance(snapshot_targets, list) or not set(snapshot_targets).issubset(ALLOWED_SNAPSHOT_TARGETS):
        issues.append(f"'snapshot_targets' は {sorted(ALLOWED_SNAPSHOT_TARGETS)} の部分集合である必要があります")

    if issues:
        raise ThemeConfigError(theme_name, issues)


def validate_all_themes(themes_dir: str | Path) -> dict[str, list[str]]:
    """themes/*.yaml を全件検証し、エラーが発生したテーマと不備内容の辞書を返す。"""
    import yaml

    results: dict[str, list[str]] = {}
    for path in sorted(Path(themes_dir).glob("*.yaml")):
        theme_name = path.stem
        try:
            with path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            validate_theme_config(theme_name, cfg)
        except ThemeConfigError as e:
            results[theme_name] = e.issues
        except Exception as e:
            results[theme_name] = [f"YAML読み込み自体に失敗: {e}"]
    return results