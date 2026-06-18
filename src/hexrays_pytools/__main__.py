"""HexRaysPyTools main entry — exports PLUGIN_ENTRY for IDA.

HCLI/IDA expects `PLUGIN_ENTRY` (or a callable returning a plugin_t instance)
in the entry file referenced by `ida-plugin.json`'s `entryPoint`.
"""
from .plugin import HexRaysPyToolsPlugin

PLUGIN_ENTRY = HexRaysPyToolsPlugin
