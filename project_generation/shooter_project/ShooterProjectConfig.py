"""Configuration objects for generated shooter projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ShooterProjectConfig:
    """Project-level config loaded from JSON templates."""

    project_name: str = "shooter_boss_trial"
    drop_interval_sec: float = 3.0
    player_lives: int = 2
    player_base_hp: int = 100
    player_max_hp: int = 100
    player_base_attack: int = 10
    boss_name: str = "Trial Boss"
    boss_max_hp: int = 200
    boss_damage_per_hit: int = 12
    item_ids: List[str] = field(default_factory=lambda: ["attack_plus_3", "damage_nullify_10s"])
    asset_manifest_path: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ShooterProjectConfig":
        player = payload.get("player", {})
        boss = payload.get("boss", {})
        return cls(
            project_name=str(payload.get("project_name") or "shooter_boss_trial"),
            drop_interval_sec=float(payload.get("drop_interval_sec") or 3.0),
            player_lives=int(player.get("lives") or 2),
            player_base_hp=int(player.get("base_hp") or 100),
            player_max_hp=int(player.get("max_hp") or (player.get("base_hp") or 100)),
            player_base_attack=int(player.get("base_attack") or 10),
            boss_name=str(boss.get("name") or "Trial Boss"),
            boss_max_hp=int(boss.get("max_hp") or 200),
            boss_damage_per_hit=int(boss.get("damage_per_hit") or 12),
            item_ids=list(payload.get("items") or ["attack_plus_3", "damage_nullify_10s"]),
            asset_manifest_path=str(payload.get("asset_manifest_path") or "project_generation/shooter_templates/asset_manifest.json"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "drop_interval_sec": self.drop_interval_sec,
            "player": {
                "lives": self.player_lives,
                "base_hp": self.player_base_hp,
                "max_hp": self.player_max_hp,
                "base_attack": self.player_base_attack,
            },
            "boss": {
                "name": self.boss_name,
                "max_hp": self.boss_max_hp,
                "damage_per_hit": self.boss_damage_per_hit,
            },
            "items": list(self.item_ids),
        }


__all__ = ["ShooterProjectConfig"]
