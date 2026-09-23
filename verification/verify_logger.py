"""Verify logger wiring inside real IDA (Task 11).

Loads the plugin via its entry, then checks:
  1. root logger level is DEBUG (from HCLI setting)
  2. a handler with the [HexRaysPyTools] format is installed
  3. logging.debug() reaches the IDA Output window (idaapi.msg) —
     captured by monkeypatching idaapi.msg for the duration.
"""
import json
import logging
from pathlib import Path

_RESULTS = Path(__file__).resolve().parent / "logs" / "logger_verify.json"


def main() -> None:
    import idaapi  # type: ignore[import-not-found]

    res: dict = {}

    # 1. init plugin exactly like IDA does
    import hexrays_pytools_entry  # type: ignore[import-not-found]

    plugin = hexrays_pytools_entry.PLUGIN_ENTRY()
    keep = plugin.init()
    res["plugin_keep"] = keep == int(idaapi.PLUGIN_KEEP)

    root = logging.getLogger()
    res["root_level"] = root.level
    res["root_level_is_debug"] = root.level == logging.DEBUG

    fmts = [h.formatter._fmt for h in root.handlers if h.formatter]  # type: ignore[attr-defined]
    res["formats"] = fmts
    res["has_hexrays_prefix"] = any("[HexRaysPyTools]" in f for f in fmts)

    # 3. capture idaapi.msg
    captured: list[str] = []
    orig_msg = idaapi.msg

    def _cap(s):
        captured.append(str(s))
        return orig_msg(s)

    idaapi.msg = _cap  # type: ignore[assignment]
    try:
        logging.getLogger("hexrays_pytools.test").debug("LOGGER_VERIFY_MARKER")
    finally:
        idaapi.msg = orig_msg  # type: ignore[assignment]

    joined = "".join(captured)
    res["marker_in_output"] = "LOGGER_VERIFY_MARKER" in joined
    res["prefix_in_output"] = "[HexRaysPyTools][DEBUG]" in joined
    res["captured_sample"] = [c for c in captured if "MARKER" in c][:1]

    plugin.term()
    _RESULTS.parent.mkdir(parents=True, exist_ok=True)
    _RESULTS.write_text(json.dumps(res, indent=2, default=str))
    print("LOGGER VERIFY:", json.dumps(res, indent=1, default=str))
    idaapi.qexit(0 if all([
        res["plugin_keep"], res["root_level_is_debug"],
        res["has_hexrays_prefix"], res["marker_in_output"], res["prefix_in_output"],
    ]) else 1)


if __name__ == "__main__":
    main()
