"""Headless wrapper: run verify_parity.py test functions under idalib.

The functions were written for the -S script harness (idaapi available via
IDA's interpreter). This runner imports them into a real idalib session so
the new paths can be validated without launching the GUI.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

import idapro  # type: ignore[import-not-found]

BIN = HERE / "test_patterns.exe"


def main() -> int:
    rc = idapro.open_database(str(BIN), True)
    if rc != 0:
        print(f"open_database rc={rc}")
        return 1
    import verify_parity as vp
    vp.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
