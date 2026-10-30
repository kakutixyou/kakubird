"""Helpers for creating a generated shooter project from the configured template."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .ShooterProjectConfig import ShooterProjectConfig


class ShooterProjectBuilder:
    """Build project metadata and a human-readable config artifact for the shooter model."""

    def __init__(self, config: ShooterProjectConfig):
        self.config = config

    def build_manifest(self) -> Dict[str, Any]:
        return {
            "project_name": self.config.project_name,
            "version": "0.1.0",
            "drop_interval_sec": self.config.drop_interval_sec,
            "player": {
                "lives": self.config.player_lives,
                "base_hp": self.config.player_base_hp,
                "max_hp": self.config.player_max_hp,
                "base_attack": self.config.player_base_attack,
            },
            "boss": {
                "name": self.config.boss_name,
                "max_hp": self.config.boss_max_hp,
                "damage_per_hit": self.config.boss_damage_per_hit,
            },
            "items": list(self.config.item_ids),
        }

    def write_manifest(self, target_dir: str | Path) -> Path:
        root = Path(target_dir)
        root.mkdir(parents=True, exist_ok=True)
        file_path = root / "shooter_project_manifest.json"
        file_path.write_text(json.dumps(self.build_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return file_path


__all__ = ["ShooterProjectBuilder"]
