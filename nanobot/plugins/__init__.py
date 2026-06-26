"""Plugin system for agent extensibility.

Plugins are directories containing a ``plugin.json`` manifest and optional
Python modules.  They can register custom tools, skills, hooks, and MCP
server configs.

Plugins are discovered from:
- ``~/.nanobot/plugins/`` (user plugins)
- Python entry_points group ``nanobot.plugins``
"""
