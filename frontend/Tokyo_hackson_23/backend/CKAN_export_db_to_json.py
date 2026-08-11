#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CKAN_export_db_to_json.py
─────────────────────────
SQLiteキュー(DB)に登録済みの未処理データを取得し、
ダウンロード → ライセンス判定 → 施設正規化(DB永続化) → %内訳JSON出力
までを一気通貫で実行するランチャー。

実体処理は orchestrator/opendata_workflow.py と orchestrator/normalize_schema.py に委譲する。

使い方:
  python CKAN_export_db_to_json.py --theme childcare
  python CKAN_export_db_to_json.py --theme aed --batch-size 200
  python CKAN_export_db_to_json.py --theme park --output-dir output/opendata_jsons/park
  python CKAN_export_db_to_json.py --theme library --skip-breakdown
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML が必要です。`pip install pyyaml` を実行してください。")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
ORCHESTRATOR_DIR = BASE_DIR / "orchestrator"
THEMES_DIR = BASE_DIR / "themes"
WORKFLOW_SCRIPT = ORCHESTRATOR_DIR / "opendata_workflow.py"

# orchestrator配下のモジュール（normalize_schema等）を直接importできるようにパスを通す
sys.path.append(str(ORCHESTRATOR_DIR))


def run_step(step_name: str, command: list[str]) -> None:
    print(f"\n{step_name}")
    print(f"▶ 実行コマンド: {' '.join(command)}")
    try:
        subprocess.run(command, cwd=str(BASE_DIR), check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ エラーが発生しました。処理を中断します。 (終了コード: {e.returncode})")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ 実行ファイルが見つかりません。パスを確認してください。")
        sys.exit(1)
    print("✅ 完了！")


def load_theme_config(theme_name: str) -> dict:
    theme_path = THEMES_DIR / f"{theme_name}.yaml"
    if not theme_path.exists():
        print(f"❌ テーマ設定ファイルが見つかりません: {theme_path}")
        sys.exit(1)

    with theme_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cfg.setdefault("name", theme_name)
    cfg.setdefault("batch_size", 100)
    cfg.setdefault("output_dir", f"output/opendata_jsons/{theme_name}")
    cfg.setdefault("metric_key", theme_name)

    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="CKANデータのDB→JSON変換ランチャー")
    parser.add_argument("--theme", required=True, help="themes/<theme>.yaml の <theme> 名")
    parser.add_argument("--batch-size", type=int, default=None, help="1回の処理件数（theme設定を上書き）")
    parser.add_argument("--output-dir", type=str, default=None, help="JSON出力先（theme設定を上書き）")
    parser.add_argument("--db-path", type=str, default="data/opendata_queue.db", help="SQLite DBパス")
    parser.add_argument("--timeout", type=int, default=20, help="HTTPタイムアウト秒")
    parser.add_argument("--skip-breakdown", action="store_true", help="%%内訳JSON出力をスキップする")
    parser.add_argument("--skip-facilities", action="store_true", help="施設正規化(DB書き込み)をスキップする")
    args = parser.parse_args()

    if not WORKFLOW_SCRIPT.exists():
        print(f"❌ ワークフロースクリプトが見つかりません: {WORKFLOW_SCRIPT}")
        sys.exit(1)

    cfg = load_theme_config(args.theme)

    theme_name = str(cfg["name"])
    batch_size = int(args.batch_size if args.batch_size is not None else cfg.get("batch_size", 100))
    output_dir = str(args.output_dir if args.output_dir is not None else cfg.get("output_dir", f"output/opendata_jsons/{theme_name}"))
    metric_key = str(cfg.get("metric_key", theme_name))

    print("===================================================")
    print("📦 CKAN DB → JSON 変換ランチャー")
    print("===================================================")
    print(f"Theme      : {theme_name}")
    print(f"Batch Size : {batch_size}")
    print(f"Output Dir : {output_dir}")
    print(f"DB Path    : {args.db_path}")

    # ── ① ダウンロード＆JSON変換（opendata_workflow.py downloadを委譲実行）──
    run_step(
        step_name="[1/4] DBの未処理データをダウンロード＆JSON変換します...",
        command=[
            sys.executable,
            str(WORKFLOW_SCRIPT),
            "download",
            "--theme", theme_name,
            "--batch-size", str(batch_size),
            "--output-dir", output_dir,
            "--db-path", args.db_path,
            "--timeout", str(args.timeout),
        ],
    )

    # normalize_schema.py はここでimport（①のdownloadが終わってからで十分なため）
    from normalize_schema import (
        backfill_license_status,
        normalize_and_persist_facilities,
        build_theme_snapshot,
    )

    # ── ② ライセンス判定のバックフィル ──
    print("\n[2/4] ライセンス判定を実行します...")
    updated = backfill_license_status(db_path=args.db_path, theme=theme_name)
    print(f"✅ ライセンス判定完了: {updated} 件を判定")

    # ── ②.5 施設データの正規化 → normalized_facilities へ永続化 ──
    if not args.skip_facilities:
        print("\n[3/4] 施設データを正規化してDBへ保存します...")
        facility_result = normalize_and_persist_facilities(db_path=args.db_path, theme=theme_name)
        print(
            f"✅ 施設正規化完了: {facility_result['inserted']}/{facility_result['total_candidates']} 件を登録 "
            f"（うち座標欠損 {facility_result['skipped_no_coords']} 件）"
        )
        if facility_result["total_candidates"] == 0:
            print("⚠️ license_status='OK'かつstatus='DOWNLOADED'のデータが0件です。①②のステップ結果を確認してください。")
    else:
        print("\n[3/4] 施設正規化はスキップされました（--skip-facilities指定）")

    # ── ③ %内訳スナップショットのエクスポート ──
    if not args.skip_breakdown:
        print("\n[4/4] %内訳スナップショットをエクスポートします...")
        snapshot = build_theme_snapshot(db_path=args.db_path, theme=theme_name, metric_key=metric_key)

        if snapshot:
            out_path = Path(output_dir) / "breakdown_snapshot.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump({"theme": theme_name, "items": snapshot}, f, ensure_ascii=False, indent=2)
            print(f"✅ 内訳スナップショット出力: {out_path} ({len(snapshot)}件)")
        else:
            print("⚠️ license_status='OK'のデータが無いため、内訳スナップショットは生成されませんでした。")
    else:
        print("\n[4/4] 内訳スナップショット出力はスキップされました（--skip-breakdown指定）")

    print("\n===================================================")
    print("🎉 DB → JSON 変換・正規化・内訳エクスポートが完了しました！")
    print("===================================================")


if __name__ == "__main__":
    main()