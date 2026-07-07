"""Build HCLI-installable ZIP archive of the plugin."""
from __future__ import annotations

import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "hexrays_pytools"
DIST = ROOT / "dist"
ENTRY_FILE = ROOT / "hexrays_pytools_entry.py"


def main() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version = pyproject["project"]["version"]
    archive = DIST / f"hexrays_pytools_ng-{version}.zip"
    DIST.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(ROOT / "ida-plugin.json", "ida-plugin.json")
        zf.write(ENTRY_FILE, "hexrays_pytools_entry.py")
        zf.write(ROOT / "LICENSE", "LICENSE")
        zf.write(ROOT / "README.md", "README.md")
        for f in SRC.rglob("*"):
            if not f.is_file():
                continue
            if "__pycache__" in f.parts:
                continue
            arcname = "hexrays_pytools" / f.relative_to(SRC)
            zf.write(f, arcname)
    print(f"Built: {archive}  ({archive.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
