"""Smoke test: StructureBuilder instantiates and accepts a model."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock


def test_structure_builder_init() -> None:
    """StructureBuilder accepts a model and exposes it."""
    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder
    model = MagicMock()
    sb = StructureBuilder(model)
    assert sb.structure_model is model
