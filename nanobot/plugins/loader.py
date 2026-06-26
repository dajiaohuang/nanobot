"""Plugin manifest definition and loader."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# Entry-point group for external plugins.
ENTRY_POINT_GROUP = "nanobot.plugins"

# Directory name for user-installed plugins under the nanobot data dir.
USER_PLUGINS_DIR = "plugins"


@dataclass
class PluginTool:
    """A tool contributed by a plugin."""

    name: str
    module: str  # Python import path to the Tool subclass
    description: str = ""


@dataclass
class PluginSkill:
    """A skill (SKILL.md) contributed by a plugin."""

    name: str
    path: str  # Relative path within the plugin dir


@dataclass
class PluginMcpServer:
    """An MCP server config contributed by a plugin."""

    name: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginManifest:
    """Contents of a plugin's ``plugin.json``."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    tools: list[PluginTool] = field(default_factory=list)
    skills: list[PluginSkill] = field(default_factory=list)
    mcp_servers: list[PluginMcpServer] = field(default_factory=list)
    # Path to the plugin directory (set by loader, not from JSON).
    directory: Path | None = field(default=None, repr=False)

    @classmethod
    def from_json(cls, path: Path) -> PluginManifest | None:
        """Load a plugin manifest from a ``plugin.json`` file."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read plugin manifest {}: {}", path, exc)
            return None
        if not isinstance(data, dict):
            return None
        tools = [
            PluginTool(**t) for t in data.get("tools", [])
            if isinstance(t, dict) and "name" in t and "module" in t
        ]
        skills = [
            PluginSkill(**s) for s in data.get("skills", [])
            if isinstance(s, dict) and "name" in s and "path" in s
        ]
        mcp_servers = [
            PluginMcpServer(**m) for m in data.get("mcpServers", [])
            if isinstance(m, dict) and "name" in m
        ]
        return cls(
            name=data.get("name", path.parent.name),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            tools=tools,
            skills=skills,
            mcp_servers=mcp_servers,
            directory=path.parent.resolve(),
        )


def discover_plugin_manifests(data_dir: Path | None = None) -> list[PluginManifest]:
    """Discover plugins from user dir and entry-points.

    Returns a list of validated ``PluginManifest`` objects.
    """
    manifests: list[PluginManifest] = []

    # 1. User plugins directory
    if data_dir is not None:
        user_dir = data_dir / USER_PLUGINS_DIR
        if user_dir.is_dir():
            for entry in sorted(user_dir.iterdir()):
                if entry.is_dir():
                    manifest_path = entry / "plugin.json"
                    if manifest_path.is_file():
                        manifest = PluginManifest.from_json(manifest_path)
                        if manifest:
                            manifests.append(manifest)

    # 2. Entry-point plugins
    if sys.version_info >= (3, 9):
        from importlib.metadata import entry_points
        try:
            eps = entry_points(group=ENTRY_POINT_GROUP)
        except TypeError:
            eps = ()
        for ep in eps:
            try:
                plugin_mod = ep.load()
                plugin_dir = Path(plugin_mod.__file__).parent if hasattr(plugin_mod, "__file__") else None
                manifest_path = plugin_dir / "plugin.json" if plugin_dir else None
                if manifest_path and manifest_path.is_file():
                    manifest = PluginManifest.from_json(manifest_path)
                    if manifest:
                        manifests.append(manifest)
            except Exception as exc:
                logger.warning("Failed to load plugin entry-point {}: {}", ep.name, exc)

    return manifests
