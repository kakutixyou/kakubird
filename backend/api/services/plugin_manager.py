# python id="x1oq7v"
# jimdo_studio_react/backend/api/services/plugin_manager.py

import importlib
import os
import traceback
from dataclasses import dataclass
from typing import Dict, Any, Optional, List


# =========================================================
# Constants
# =========================================================

PLUGIN_ROOT = "plugins"

MANIFEST_FILENAME = "plugin.json"


# =========================================================
# Data Classes
# =========================================================

@dataclass
class PluginManifest:
    """
    plugin metadata
    """

    name: str

    version: str

    description: str

    entrypoint: str

    enabled: bool = True

    plugin_type: str = "generic"

    trigger_keywords: Optional[List[str]] = None


# =========================================================
# Plugin Registry
# =========================================================

PLUGIN_REGISTRY: Dict[str, PluginManifest] = {}


# =========================================================
# Utility
# =========================================================

def safe_import_module(
    module_path: str
):
    """
    安全import
    """

    try:

        return importlib.import_module(
            module_path
        )

    except Exception:

        traceback.print_exc()

        return None


# =========================================================
# Manifest Loader
# =========================================================

def load_manifest_file(
    plugin_dir: str
) -> Optional[PluginManifest]:
    """
    plugin.json 読み込み

    Example:
        plugins/recruit/plugin.json
    """

    import json

    manifest_path = os.path.join(
        plugin_dir,
        MANIFEST_FILENAME
    )

    if not os.path.exists(
        manifest_path
    ):
        return None

    try:

        with open(
            manifest_path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return PluginManifest(
            name=data.get("name", "unknown"),

            version=data.get(
                "version",
                "0.0.0"
            ),

            description=data.get(
                "description",
                ""
            ),

            entrypoint=data.get(
                "entrypoint",
                ""
            ),

            enabled=data.get(
                "enabled",
                True
            ),

            plugin_type=data.get(
                "plugin_type",
                "generic"
            ),

            trigger_keywords=data.get(
                "trigger_keywords",
                []
            ),
        )

    except Exception:

        traceback.print_exc()

        return None


# =========================================================
# Plugin Discovery
# =========================================================

def discover_plugins() -> Dict[str, PluginManifest]:
    """
    plugins/* 自動探索
    """

    global PLUGIN_REGISTRY

    PLUGIN_REGISTRY = {}

    if not os.path.exists(
        PLUGIN_ROOT
    ):
        return PLUGIN_REGISTRY

    try:

        for plugin_name in os.listdir(
            PLUGIN_ROOT
        ):

            plugin_dir = os.path.join(
                PLUGIN_ROOT,
                plugin_name
            )

            if not os.path.isdir(
                plugin_dir
            ):
                continue

            manifest = load_manifest_file(
                plugin_dir
            )

            if not manifest:
                continue

            if not manifest.enabled:
                continue

            PLUGIN_REGISTRY[
                manifest.name
            ] = manifest

    except Exception:

        traceback.print_exc()

    return PLUGIN_REGISTRY


# =========================================================
# Plugin Lookup
# =========================================================

def get_plugin(
    plugin_name: str
) -> Optional[PluginManifest]:
    """
    registry lookup
    """

    return PLUGIN_REGISTRY.get(
        plugin_name
    )


def list_plugins() -> List[str]:
    """
    plugin name list
    """

    return list(
        PLUGIN_REGISTRY.keys()
    )


# =========================================================
# Trigger Matching
# =========================================================

def detect_triggered_plugins(
    user_message: str
) -> List[PluginManifest]:
    """
    keywordベース plugin判定
    """

    triggered = []

    msg_lower = user_message.lower()

    for plugin in PLUGIN_REGISTRY.values():

        keywords = (
            plugin.trigger_keywords
            or []
        )

        if any(
            keyword.lower() in msg_lower
            for keyword in keywords
        ):

            triggered.append(
                plugin
            )

    return triggered


# =========================================================
# Plugin Entrypoint Execution
# =========================================================

async def execute_plugin(
    plugin_name: str,
    payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    plugin entrypoint実行

    plugin.json:
    {
      "entrypoint":
        "plugins.recruit.main"
    }

    main.py:
        async def run(payload):
            ...
    """

    try:

        manifest = get_plugin(
            plugin_name
        )

        if not manifest:
            return None

        module = safe_import_module(
            manifest.entrypoint
        )

        if not module:
            return None

        if not hasattr(
            module,
            "run"
        ):
            return None

        result = await module.run(
            payload
        )

        return result

    except Exception:

        traceback.print_exc()

        return {
            "error": True,
            "message":
                f"{plugin_name} plugin execution failed"
        }


# =========================================================
# Bulk Plugin Execution
# =========================================================

async def execute_triggered_plugins(
    user_message: str,
    payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    trigger plugin 一括実行
    """

    results = []

    plugins = detect_triggered_plugins(
        user_message
    )

    for plugin in plugins:

        result = await execute_plugin(
            plugin.name,
            payload
        )

        if result:

            results.append(result)

    return results


# =========================================================
# Plugin Context Builder
# =========================================================

def build_plugin_context_text() -> str:
    """
    LLM prompt用 plugin情報
    """

    if not PLUGIN_REGISTRY:

        return ""

    lines = [
        "\n【利用可能なプラグイン】"
    ]

    for plugin in PLUGIN_REGISTRY.values():

        lines.append(
            f"- {plugin.name}: "
            f"{plugin.description}"
        )

    return "\n".join(lines)


# =========================================================
# Plugin Health Check
# =========================================================

async def health_check_plugins(
) -> Dict[str, Any]:
    """
    plugin health確認
    """

    result = {}

    for plugin_name in PLUGIN_REGISTRY:

        try:

            manifest = get_plugin(
                plugin_name
            )

            module = safe_import_module(
                manifest.entrypoint
            )

            result[plugin_name] = {
                "healthy":
                    module is not None
            }

        except Exception:

            result[plugin_name] = {
                "healthy": False
            }

    return result


# =========================================================
# Plugin Reload
# =========================================================

def reload_plugins():
    """
    registry reload
    """

    return discover_plugins()


# =========================================================
# Boot Initialization
# =========================================================

discover_plugins()


# =========================================================
# Future Expansion Notes
# =========================================================

"""
将来的な拡張ポイント

1. Sandboxed Runtime
--------------------------------------------------------
plugin isolation

2. Plugin Permissions
--------------------------------------------------------
filesystem
network
db

3. Marketplace
--------------------------------------------------------
online plugin store

4. Dependency Injection
--------------------------------------------------------
service container

5. Plugin Lifecycle
--------------------------------------------------------
on_load
on_unload

6. Hot Reload
--------------------------------------------------------
runtime refresh

7. Plugin Config UI
--------------------------------------------------------
settings panel

8. Event Bus
--------------------------------------------------------
plugin hooks

9. Tool Calling Integration
--------------------------------------------------------
LLM tool auto registration

10. WASM Plugins
--------------------------------------------------------
secure runtime
"""

