"""Minimal asset resolver for game scene objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class AssetHandler:
    """Resolve model-defined asset ids to concrete asset paths."""

    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            return {"backgrounds": [], "enemies": [], "allies": [], "items": []}
        with self.manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def resolve_background(self, asset_id: str) -> str | None:
        for item in self.manifest.get("backgrounds", []):
            if item.get("id") == asset_id:
                return item.get("path")
        return None

    def resolve_enemy(self, asset_id: str) -> str | None:
        for item in self.manifest.get("enemies", []):
            if item.get("id") == asset_id:
                return item.get("path")
        return None

    def resolve_ally(self, asset_id: str) -> str | None:
        for item in self.manifest.get("allies", []):
            if item.get("id") == asset_id:
                return item.get("path")
        return None

    def resolve_item(self, asset_id: str) -> str | None:
        for item in self.manifest.get("items", []):
            if item.get("id") == asset_id:
                return item.get("path")
        return None


__all__ = ["AssetHandler"]
