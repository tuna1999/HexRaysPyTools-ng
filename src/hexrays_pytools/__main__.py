"""HexRaysPyTools main entry — exports PLUGIN_ENTRY for IDA.

HCLI/IDA expects `PLUGIN_ENTRY` (a callable returning a `plugin_t` instance)
in the entry file referenced by `ida-plugin.json`'s `entryPoint`.
"""

from .plugin import PLUGIN_ENTRY

__all__ = ["PLUGIN_ENTRY"]
