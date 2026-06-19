# Task 3.6 Brief: ui/widgets (3 forms)

## Files (5 — 3 widgets + 2 widget files)
1. `src/hexrays_pytools/ui/widgets/__init__.py` (empty)
2. `src/hexrays_pytools/ui/widgets/structure_builder.py`
3. `src/hexrays_pytools/ui/widgets/class_viewer.py`
4. `src/hexrays_pytools/ui/widgets/graph_viewer.py`
5. `tests/ui/__init__.py` (empty) — test dir
6. `tests/ui/widgets/__init__.py` (empty)
7. `tests/ui/widgets/test_structure_builder.py`
8. `tests/ui/widgets/test_class_viewer.py`
9. `tests/ui/widgets/test_graph_viewer.py`

## `structure_builder.py` (verbatim — minimal Qt form for the builder)

```python
"""Structure Builder widget — the dock form for the temp struct model."""
from __future__ import annotations
from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]


class StructureBuilder(idaapi.PluginForm):  # type: ignore[misc]
    """Dock form wrapping a Qt table view for the structure builder."""

    def __init__(self, structure_model: Any) -> None:
        super().__init__()
        self.structure_model = structure_model
        self.parent: QtWidgets.QWidget | None = None  # noqa: N806 - Qt naming

    def OnCreate(self, form: Any) -> None:  # noqa: N802, N806
        self.parent = self.FormToPySideWidget(form)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        self.struct_view = QtWidgets.QTableView()
        self.struct_view.setModel(self.structure_model)
        layout.addWidget(self.struct_view)
        # Finalize button
        btn_finalize = QtWidgets.QPushButton("Finalize")
        btn_finalize.clicked.connect(self._on_finalize)
        layout.addWidget(btn_finalize)
        self.parent.setLayout(layout)

    def _on_finalize(self) -> None:
        if hasattr(self.structure_model, "finalize"):
            self.structure_model.finalize()

    @staticmethod
    def FormToPySideWidget(form: Any) -> QtWidgets.QWidget:  # noqa: N802, N806
        """Convert IDA form HWND to PySide6 widget. FIX B1: was PyQt5."""
        return idaapi.PluginForm.FormToPySideWidget(form)
```

## `class_viewer.py` (verbatim)

```python
"""Class Viewer widget — the dock form for the class browser."""
from __future__ import annotations
from typing import Any

import idaapi  # type: ignore[import-not-found]
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]


class ClassViewer(idaapi.PluginForm):  # type: ignore[misc]
    """Dock form for the class browser tree view."""

    def __init__(self, proxy_model: Any, class_model: Any) -> None:
        super().__init__()
        self.proxy_model = proxy_model
        self.class_model = class_model
        self.parent: QtWidgets.QWidget | None = None  # noqa: N806

    def OnCreate(self, form: Any) -> None:  # noqa: N802, N806
        self.parent = self.FormToPySideWidget(form)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        # Filter line edit
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_edit)
        # Tree view
        self.class_tree = QtWidgets.QTreeView()
        self.class_tree.setModel(self.proxy_model)
        layout.addWidget(self.class_tree)
        self.parent.setLayout(layout)
        self.proxy_model.setSourceModel(self.class_model)

    def _on_filter_changed(self, text: str) -> None:
        if hasattr(self.proxy_model, "set_regexp_filter"):
            self.proxy_model.set_regexp_filter(text)

    @staticmethod
    def FormToPySideWidget(form: Any) -> QtWidgets.QWidget:  # noqa: N802, N806
        return idaapi.PluginForm.FormToPySideWidget(form)
```

## `graph_viewer.py` (verbatim)

```python
"""Structure Graph viewer widget — graph of type dependencies."""
from __future__ import annotations
from typing import Any

import idaapi  # type: ignore[import-not-found]


class StructureGraphViewer(idaapi.GraphViewer):  # type: ignore[misc]
    """Graph viewer for structure_graph.StructureGraph."""

    def __init__(self, title: str, graph: Any) -> None:
        super().__init__(title)
        self._graph = graph

    def OnRefresh(self) -> None:  # noqa: N802, N806
        self.Clear()
        nodes = self._graph.get_nodes() if hasattr(self._graph, "get_nodes") else set()
        node_to_id: dict[Any, int] = {}
        for node in nodes:
            nid = self.AddNode(node)
            node_to_id[node] = nid
        for src, dst in self._graph.get_edges() if hasattr(self._graph, "get_edges") else []:
            if src in node_to_id and dst in node_to_id:
                self.AddEdge(node_to_id[src], node_to_id[dst])

    def OnGetText(self, node_id: int) -> str:  # noqa: N802, N806
        node = self[node_id]
        if hasattr(node, "name"):
            return str(node.name)
        return str(node)

    def OnHint(self, node_id: int) -> str:  # noqa: N802, N806
        node = self[node_id]
        if hasattr(node, "tooltip"):
            return node.tooltip()
        return ""

    def OnDblClick(self, node_id: int) -> None:  # noqa: N802, N806
        node = self[node_id]
        if hasattr(self._graph, "change_selected") and hasattr(node, "name"):
            self._graph.change_selected({node})
            self.Refresh()
```

## Tests (3 files, minimal smoke tests)

```python
# tests/ui/widgets/test_structure_builder.py
"""Smoke test: StructureBuilder instantiates and accepts a model."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_structure_builder_init() -> None:
    """StructureBuilder accepts a model and exposes it."""
    from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder
    model = MagicMock()
    sb = StructureBuilder(model)
    assert sb.structure_model is model
```

```python
# tests/ui/widgets/test_class_viewer.py
"""Smoke test: ClassViewer accepts proxy + class models."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_class_viewer_init() -> None:
    from hexrays_pytools.ui.widgets.class_viewer import ClassViewer
    proxy = MagicMock()
    cls_model = MagicMock()
    cv = ClassViewer(proxy, cls_model)
    assert cv.proxy_model is proxy
    assert cv.class_model is cls_model
```

```python
# tests/ui/widgets/test_graph_viewer.py
"""Smoke test: StructureGraphViewer builds."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_graph_viewer_init() -> None:
    from hexrays_pytools.ui.widgets.graph_viewer import StructureGraphViewer
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    assert gv._graph is graph
```

Add `from unittest.mock import MagicMock` to each test.

## Verification
```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/ui/ -v
python -m mypy --strict src/hexrays_pytools/ui/
python -m ruff check src/hexrays_pytools/ui/ tests/ui/
```

## Commit
```bash
git add src/hexrays_pytools/ui/widgets/ tests/ui/
git commit -m "feat(ui): add 3 widgets (StructureBuilder, ClassViewer, GraphViewer) — B1 fix: FormToPySideWidget"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-3.6-report.md`