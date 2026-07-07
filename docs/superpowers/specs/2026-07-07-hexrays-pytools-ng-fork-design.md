# HexRaysPyTools-ng v1.0.0 — Fork + Architecture Fixes

**Date**: 2026-07-07
**Branch target**: `master` (this is a fresh fork starting point)
**Status**: Approved (pending writing-plans)

---

## Overview

Fork `HexRaysPyTools` thành `HexRaysPyTools-ng`, reset version về `1.0.0`, đồng thời fix toàn bộ 6 findings từ architecture review trước đó (F1–F6). Plugin giữ nguyên Python package name (`hexrays_pytools`) để tránh vỡ hàng loạt internal imports — chỉ đổi các identifier mà user nhìn thấy (plugin ID, display name, zip output, README, netnode storage key).

`CHANGELOG.md` bị xóa hoàn toàn. Bug ID references trong code source (B10, B11, B12) được rewrite thành inline comment giải thích behavior, không trỏ đến file không tồn tại. CHANGELOG sẽ được viết lại sau khi port xong toàn bộ chức năng plugin gốc.

---

## Decisions (locked)

| Aspect | Value |
|---|---|
| Repo folder | `D:\re_dev_projects\ida-plugins\HexRaysPyTools-ng\` |
| Plugin display name | `HexRaysPyTools-ng` |
| Plugin ID (`ida-plugin.json`) | `hexrays_pytools_ng` |
| Python package name | `hexrays_pytools` (UNCHANGED — internal, user không thấy) |
| Plugin zip output | `hexrays_pytools_ng-1.0.0.zip` |
| Version semantic | v1.0.0 = fresh fork start (không phải kế thừa semantic từ upstream 2.0.0) |
| Netnode key (xref storage) | `$hexrays_pytools_ng/xref_storage` |
| Legacy array name (xref) | `$HexRaysPyTools-ng:XrefStorage` |
| CHANGELOG.md | Xóa hoàn toàn |
| `refs/HexRaysPyTools/` | Giữ nguyên tên (upstream legacy, không thuộc fork này) |
| `docs/superpowers/specs/2026-06-18-...` | Không đụng (lịch sử upstream rewrite design) |
| Fix scope | F1, F2, F3, F4, F5, F6 (tất cả 6 findings) |

---

## Section 1 — Rename + Version Bump + CHANGELOG Removal

### Filesystem

- Rename folder `D:\re_dev_projects\ida-plugins\HexRaysPyTools` → `HexRaysPyTools-ng`. Git không bị ảnh hưởng (folder name ≠ git internals). Cần đóng IDE/editor trước khi rename.

### Files modified

| File | Change |
|---|---|
| `pyproject.toml` | `name = "hexrays_pytools"` → `"hexrays_pytools_ng"`, `version = "2.0.0"` → `"1.0.0"` |
| `ida-plugin.json` | `plugin.name` → `"hexrays_pytools_ng"`, `plugin.version` → `"1.0.0"` |
| `tools/build_plugin.py` | Output zip name → `hexrays_pytools_ng-1.0.0.zip` |
| `README.md` | Update title, install path; xóa dòng `See [CHANGELOG.md]` |
| `CLAUDE.md` | Xóa reference đến CHANGELOG khỏi danh sách tài liệu tham chiếu |
| `src/hexrays_pytools/domain/xrefs/xref_storage.py` | `NODE_NAME` → `"$hexrays_pytools_ng/xref_storage"`, `OLD_ARRAY_NAME` → `"$HexRaysPyTools-ng:XrefStorage"` |
| `src/hexrays_pytools/domain/actions/registry.py` (line 48) | Comment `(B10 fix)` → inline giải thích `Ctrl+Alt+N` để tránh đụng `RenameOther` |
| `src/hexrays_pytools/domain/const.py` (line 4) | Comment `(B11 bug — re-initialized via const.init() at ...)` → inline giải thích `init_consts()` chạy lúc `Session.open()` |
| `src/hexrays_pytools/domain/ctree/swap_if.py` (line 12) | Comment `(B12 fix)` → inline giải thích netnode thay `idc.create_array` |

### Files deleted

- `CHANGELOG.md` — xóa hoàn toàn. Không thay bằng file rỗng.

### Files NOT changed (deliberate)

- `src/hexrays_pytools/` Python package name (lý do: ~50 import sites trong src/ + ~30 trong tests/ + ~10 trong docs sẽ vỡ; package name là internal — user không thấy)
- `src/hexrays_pytools/plugin.py` Plugin class name `HexRaysPyToolsPlugin` (internal)
- `refs/HexRaysPyTools/` (upstream legacy reference)
- `docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md` (lịch sử)
- `hexrays_pytools_entry.py` (entry file name có thể giữ; sẽ check khi implement)

### Rationale (package name giữ nguyên)

Đổi `hexrays_pytools` → `hexrays_pytools_ng` đồng nghĩa update ~50 import statements trong src/ + ~30 trong tests/ + ~10 trong docs. Rủi ro typo cao, lợi ích thấp (package name là internal — user không thấy). Plugin ID, display name, zip name, README là những gì user thấy trong IDA Plugins menu và khi cài qua `hcli`. Đó là điểm cần đổi.

---

## Section 2 — Architecture Fixes (F1–F6)

### F1 — Layer integrity: 8 domain→ui upward imports

**Hiện trạng**: CLAUDE.md ghi "không import ngược lên layer trên", nhưng grep trả 8 sites vi phạm:

| File:line | Imported from `ui/` | Note |
|---|---|---|
| `domain/actions/form_requests.py:15-17` | `ClassViewer`, `StructureGraphViewer`, `StructureBuilder` | Real Qt widgets — high-impact violation |
| `domain/actions/guess_allocation.py:23` | `MyChoose` | Mis-location (no Qt, just `idaapi.Choose`) |
| `domain/actions/struct_xref.py:15` | `MyChoose` | Mis-location |
| `domain/actions/structs_by_size.py:13` | `MyChoose` | Mis-location |
| `domain/ctree/negative_offsets.py:21` | `MyChoose` | Mis-location |
| `domain/til/type_library.py:17` | `MyChoose` | Mis-location |

**Cách làm**:

#### F1.a — Di chuyển `MyChoose` từ `ui/` về `domain/`

1. Tạo file mới `src/hexrays_pytools/domain/chooser.py` chứa class `MyChoose` (copy nguyên từ `ui/chooser.py`).
2. Xóa class `MyChoose` khỏi `src/hexrays_pytools/ui/chooser.py` (giữ lại các widget imports khác nếu có).
3. Update 5 import sites:
   - `domain/actions/guess_allocation.py:23`: `from ...ui.chooser import MyChoose` → `from ..chooser import MyChoose`
   - `domain/actions/struct_xref.py:15`: same
   - `domain/actions/structs_by_size.py:13`: same
   - `domain/ctree/negative_offsets.py:21`: same
   - `domain/til/type_library.py:17`: same
4. Verify `grep -rn "from hexrays_pytools\.ui\|from \.\.\.ui\|from \.\.ui" src/hexrays_pytools/domain/` còn duy nhất `form_requests.py` (sẽ fix ở F1.b).

#### F1.b — Widget factory injection qua Session

1. Thêm 3 field vào `Session` dataclass (`src/hexrays_pytools/domain/session.py`):
   ```python
   # Default factories: None at construction time. Plugin entry populates
   # these after Session is created (so plugin layer wires UI layer into
   # session — the only legal UI→session wiring point in 5-layer arch).
   class_viewer_factory: Callable[[StructureModel], ClassViewer] | None = None
   structure_graph_viewer_factory: Callable[[ReconWorkspace], StructureGraphViewer] | None = None
   structure_builder_factory: Callable[[ReconWorkspace], StructureBuilder] | None = None
   ```
   Type imports cho 3 widget class đặt trong `TYPE_CHECKING` block (chỉ cho type hints, không runtime) — đây là exception được phép vì session.py là layer 4 (root), nơi UI imports hợp lệ.

   Action activate() guard trước khi gọi factory:
   ```python
   if self._session.class_viewer_factory is None:
       raise RuntimeError("class_viewer_factory not wired; plugin init incomplete")
   viewer = self._session.class_viewer_factory(model)
   ```

2. `domain/actions/form_requests.py:15-17`:
   - Bỏ 3 widget import.
   - Trong các action `activate()` (ShowGraph, ShowClasses, ShowStructureBuilder), thay `_import_widget().show()` bằng `self._session.<factory>(<model>)`.
   - Cần verify các action nào reference widget cụ thể — sẽ đọc chi tiết khi implement.

3. **Inject default factories** tại plugin entry — đây là điểm layer 5 wire vào layer 4 hợp lệ:
   - Trong `plugin.py` (chỗ tạo `Session` hoặc `init` lifecycle, **không** trong `hexrays_pytools_entry.py` vì entry file chạy trong synthetic namespace), set:
     ```python
     # Layer 4 (root/plugin) wiring UI layer factories into Session.
     # This is the ONLY place UI imports are legal in plugin architecture.
     from hexrays_pytools.ui.widgets.class_viewer import ClassViewer
     from hexrays_pytools.ui.widgets.graph_viewer import StructureGraphViewer
     from hexrays_pytools.ui.widgets.structure_builder import StructureBuilder
     session.class_viewer_factory = ClassViewer
     session.structure_graph_viewer_factory = StructureGraphViewer
     session.structure_builder_factory = StructureBuilder
     ```
   - Trong test (mock environment), inject mock factory qua `Session(class_viewer_factory=mock_factory, ...)`.

4. Tests mới:
   - `tests/domain/actions/test_form_requests.py`: verify 3 action activate gọi đúng factory method trên Session, không import widget trực tiếp.

### F2 — XrefStorage migration: atomic + correct comment

**Hiện trạng** (`src/hexrays_pytools/domain/xrefs/xref_storage.py:74-83`):
- Comment nói "legacy takes precedence" nhưng code cho netnode thắng (dùng `setdefault` + `if not in`).
- `idc.delete_array(array_id)` chạy **trước** khi dữ liệu merged được flush xuống netnode. Nếu IDA crash giữa 2 bước → data loss irrecoverable.

**Cách làm**:

#### F2.a — Đổi thứ tự: flush trước, delete sau

```python
# 1. Merge: netnode wins on ordinal/func_offset conflicts.
#    If the user already has stored xrefs in the new format, legacy data
#    is dropped for matching keys. (See F2.b for semantic.)
for ord_key, funcs in old.items():
    ord_key = int(ord_key)
    self._storage.setdefault(ord_key, {})
    for func_off, fields in funcs.items():
        func_off = int(func_off)
        if func_off not in self._storage[ord_key]:
            self._storage[ord_key][func_off] = fields
# 2. Flush merged data to netnode BEFORE deleting legacy array.
#    Order matters: a crash before flush loses nothing (legacy still on disk);
#    a crash after delete but before flush loses data. Always flush first.
self._write_to_netnode()  # actual method name TBD at impl time — see note below
# 3. Only now delete legacy array.
idc.delete_array(array_id)
```

**Implementation note**: Spec assumes a `flush()` / `_write_to_netnode()` method exists on `XrefStorage`. Verify actual method name during implementation; if absent, add a thin `flush()` wrapper around the existing netnode write path. Order in code is the contract; exact method name is incidental.

#### F2.b — Comment đúng semantic

Đổi line 74 comment từ `# Merge: legacy takes precedence for matching ordinals` → `# Merge: netnode wins on (ord, func_off) conflicts. If both legacy and netnode have an entry for the same key, the netnode value is kept (legacy entry dropped).`

#### F2.c — Tests mới

`tests/domain/xrefs/test_xref_storage_migration.py` — file mới:

1. `test_migrate_from_legacy_when_netnode_empty`: legacy array có data, netnode rỗng → sau migrate netnode chứa legacy data, legacy array bị xóa.
2. `test_migrate_netnode_wins_on_conflict`: cả 2 đều có data với cùng `(ord, func_off)` key → netnode value được giữ, legacy bị drop.
3. `test_migrate_noop_when_legacy_absent`: `idc.get_array_id` trả `BADORD` → không có gì xảy ra, không delete.
4. `test_flush_before_delete`: verify khi `idc.delete_array` được gọi, `set_string` đã được gọi trước (sử dụng mock order check).

### F3 — ActionRegistry count mismatch → RuntimeError

**Hiện trạng** (`src/hexrays_pytools/domain/actions/registry.py:132-133`):
```python
if len(all_classes) != 27:
    logger.warning("Expected 27 action classes, found %d", len(all_classes))
```
Silent failure — CI không bắt được nếu class bị quên.

**Cách làm**: đổi 2 dòng thành:
```python
if len(all_classes) != 27:
    raise RuntimeError(
        f"ActionRegistry: expected 27 action classes, got {len(all_classes)}. "
        "Did you forget to add a class to both ACTION_CLASSES and _build_actions?"
    )
```

Test `tests/domain/actions/test_registry.py::test_registry_count` đã có — sẽ pass với count=27, nhưng giờ failure sẽ loud thay vì silent.

### F4 — HxCallbackManager expose errors qua Session

**Hiện trạng** (`src/hexrays_pytools/domain/actions/hx_callback.py:30-36`): handler raise → log → return 0. Failure invisible.

**Cách làm** (scope hợp lý, không over-engineer):

#### F4.a — Thêm errors list vào HxCallbackManager

```python
class HxCallbackManager:
    def __init__(self) -> None:
        self._handlers: dict[int, list[Handler]] = {}
        self.errors: list[tuple[int, Exception]] = []  # NEW: (event_id, exception)

    def dispatch(self, event_id: int, *args: Any) -> int:
        for handler in self._handlers.get(event_id, ()):
            try:
                handler.handle(event_id, *args)
            except Exception as exc:  # noqa: BLE001 — intentional swallow
                logger.exception("Callback handler %r raised", handler)
                self.errors.append((event_id, exc))  # NEW
        return 0
```

#### F4.b — Expose qua Session

Trong `Session` dataclass (`src/hexrays_pytools/domain/session.py`):
```python
@property
def recent_callback_errors(self) -> list[tuple[int, Exception]]:
    """Last 10 errors from HxCallbackManager (read-only snapshot)."""
    if self.hx_callbacks is None:
        return []
    return list(self.hx_callbacks.errors[-10:])
```

#### F4.c — KHÔNG render trong UI

Spec này không bao gồm UI rendering. Mục tiêu chỉ là expose qua Session để UI code tương lai có thể poll. Render là follow-up scope.

#### F4.d — Test mới

`tests/domain/actions/test_hx_callback.py` — bổ sung:

1. `test_handler_exception_recorded`: install handler raises `ValueError` → `manager.errors` chứa `(event_id, exc)`.
2. `test_session_recent_callback_errors`: khi Session có `hx_callbacks`, `recent_callback_errors` trả snapshot.

### F5 — Per-module coverage floor cho widgets (soft target)

**Hiện trạng**:
- `ui/widgets/class_viewer.py`: 50% coverage, chỉ có smoke test
- `ui/widgets/structure_builder.py`: 50% coverage, chỉ có smoke test

**Cách làm**:

#### F5.a — Bổ sung widget tests

`tests/ui/widgets/test_class_viewer.py` — thêm test cho:
- `OnCreate` form binding (verify `self.form` được set)
- `columnCount` / `rowCount` cho model bound (kiểm tra propagation từ `StructureModel`)
- `data()` cho `Qt.DisplayRole` và `Qt.UserRole` 
- `_init_ui` không raise với valid model

`tests/ui/widgets/test_structure_builder.py` — thêm test tương tự:
- `OnCreate` binding
- `columnCount` / `rowCount`
- `data()` cho các role
- `_init_ui` không raise

Lưu ý: tests này cần real PySide6 importable. `tools/mock_ida.py` đã có logic skip mock khi real PySide6 có sẵn — không cần thay đổi mock infrastructure.

#### F5.b — KHÔNG thêm per-module coverage floor vào gate

Lý do: widget tests phụ thuộc PySide6 thật. Nếu env test không có PySide6 (CI minimal), smoke test phải đủ. Enforce floor cần hạ tầng test riêng (marker riêng cho widget tests). Follow-up scope.

**Mục tiêu mềm**: widget coverage tăng từ 50% → 70%+ mà không cần đổi gate config.

### F6 — ReconWorkspace lazy model

**Hiện trạng** (`src/hexrays_pytools/domain/recon/workspace.py:37-42`):
- `ReconWorkspace.__init__` gọi `_create_empty_model()` → import `StructureModel` → `from PySide6 import QtCore`
- Ép PySide6 importable ở init time, kể cả khi UI không dùng
- Comment ở line 86-95 nói "lazy" nhưng thực tế eager — comment overstates

**Cách làm**:

#### F6.a — Property accessor

```python
class ReconWorkspace:
    def __init__(self) -> None:
        self._model: StructureModel | None = None
        # Other init...

    @property
    def model(self) -> StructureModel:
        if self._model is None:
            from .structure_model import StructureModel
            self._model = StructureModel(...)
        return self._model
```

#### F6.b — Update call sites

Tìm và sửa tất cả code site dùng `workspace.model` hoặc `workspace._model`:
- Nếu dùng `workspace._model` (private) → đổi thành `workspace.model` (property).
- Nếu dùng `workspace.model` như attribute (không phải property) → giữ nguyên syntax (property syntax-compatible).

Cần grep toàn bộ `src/hexrays_pytools/` cho `.model` và `._model` access trên `ReconWorkspace` instances.

#### F6.c — Comment sửa

`workspace.py:86-95` — đổi từ "avoids circular import" / "lazy" → ghi rõ: "True lazy: `StructureModel` (Qt-dependent) is constructed on first `.model` access, not at workspace init time. This keeps `Session.open()` PySide6-free so unit tests can construct a `ReconWorkspace` without Qt available."

#### F6.d — Test mới

`tests/domain/recon/test_workspace.py` — bổ sung:

1. `test_workspace_init_does_not_import_pyside6`: `mock_ida.install()` + mock `PySide6` absent → `ReconWorkspace()` succeeds without import error.
2. `test_model_constructed_on_first_access`: first `.model` access triggers `StructureModel` construction; subsequent accesses return cached instance.
3. `test_model_is_singleton_per_workspace`: `ws1.model is ws1.model` (cached), `ws1.model is not ws2.model` (per-instance).

---

## Section 3 — Test Plan & Acceptance Criteria

### Test plan

Mỗi lệnh phải pass sau khi implement:

1. `pytest -v` — tất cả tests pass, total coverage ≥ 80%.
2. `pytest tests/domain/actions/test_registry.py::test_registry_count -v` — pass với count=27.
3. `pytest tests/domain/xrefs/ -v` — gồm cả test migration mới.
4. `pytest tests/domain/actions/test_hx_callback.py -v` — gồm cả test exception recording.
5. `pytest tests/domain/recon/test_workspace.py -v` — gồm cả test lazy model.
6. `pytest tests/ui/widgets/test_class_viewer.py tests/ui/widgets/test_structure_builder.py -v` — coverage mới cho widget methods.
7. `pytest tests/domain/actions/test_form_requests.py -v` — verify 3 factory calls.
8. `mypy --strict src/hexrays_pytools/` — clean.
9. `ruff check src/hexrays_pytools/ tests/ tools/` — clean.
10. `python tools/build_plugin.py` — tạo `dist/hexrays_pytools_ng-1.0.0.zip` thành công.

### Acceptance criteria

Verify sau khi implement (dùng grep / file system):

| ID | Criterion | Verify command |
|---|---|---|
| AC-1 | Repo folder tên `HexRaysPyTools-ng` | filesystem |
| AC-2 | `ida-plugin.json` `plugin.name = "hexrays_pytools_ng"` | `grep` |
| AC-3 | `ida-plugin.json` `plugin.version = "1.0.0"` | `grep` |
| AC-4 | `pyproject.toml` `name = "hexrays_pytools_ng"` | `grep` |
| AC-5 | `pyproject.toml` `version = "1.0.0"` | `grep` |
| AC-6 | File `CHANGELOG.md` không tồn tại | filesystem |
| AC-7 | Không có bug ID ref `B10\|B11\|B12\|B14` trong source comments | `grep` |
| AC-8 | `domain/` không import từ `ui/` | `grep -rn "from hexrays_pytools\.ui\|from \.\.\.ui\|from \.\.ui" src/hexrays_pytools/domain/` returns 0 lines |
| AC-9 | `registry.py` không có `logger.warning.*27 action` | `grep` |
| AC-10 | Netnode key mới: `$hexrays_pytools_ng/xref_storage` | `grep` |
| AC-11 | `xref_storage.py` migration flush trước delete | `grep` order check, hoặc test `test_flush_before_delete` |
| AC-12 | `xref_storage.py:74` comment mô tả đúng "Netnode wins" | `grep` |
| AC-13 | `HxCallbackManager.errors` list tồn tại | code review |
| AC-14 | `Session.recent_callback_errors` property tồn tại | code review |
| AC-15 | Widget test coverage tăng (target 70%+) | `pytest --cov` |
| AC-16 | `ReconWorkspace()` không import PySide6 ở `__init__` | `test_workspace_init_does_not_import_pyside6` pass |
| AC-17 | Build artifact `dist/hexrays_pytools_ng-1.0.0.zip` tồn tại | filesystem |
| AC-18 | All tests pass, coverage ≥ 80% | `pytest` |

### Out of scope (follow-up)

- Thêm per-module coverage floor vào gate config (cần test infrastructure cho widget-only marker)
- Render callback errors trong UI (status bar / log action)
- Di chuyển `domain/actions/hx_events.py` ra khỏi omit list (cần test infra cho ctree dispatch)
- Migration từ netnode key cũ `$hexrays_pytools/xref_storage` (đã quyết định: KHÔNG migration, fresh start)
- CHANGELOG.md (sẽ viết khi port xong chức năng plugin gốc)

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Folder rename làm IDE index lại / extensions reload | Đóng IDE trước khi rename; sau rename mở lại và đợi index hoàn tất trước khi commit |
| `form_requests.py` refactor đụng 3 actions đang hotkey-bound | Verify test `test_form_requests` covers tất cả 3 actions; integration test (nếu có) trong `tests/domain/actions/` |
| Netnode key đổi → user cũ mất xref data khi upgrade từ upstream 2.0.0 | Document trong README: "Netnode storage key changed. Users upgrading from upstream HexRaysPyTools 2.0.0 will start with empty xref storage." |
| `ReconWorkspace.model` property refactor có thể break scanner-action code dùng `_model` private | Grep toàn bộ `src/hexrays_pytools/` cho `.model` / `._model` access trước khi implement; cover bằng integration test |
| Widget tests cần PySide6 thật; CI minimal có thể không có | Mock_ida đã có logic skip — verify trước khi implement; nếu PySide6 absent, tests skip (không fail) |

---

## Implementation order

Thứ tự đề xuất (mỗi bước verify được):

1. **Section 1 — Rename + version bump + CHANGELOG removal** (smallest, isolated)
2. **F3 — ActionRegistry RuntimeError** (1 file, 1 line change)
3. **F2 — XrefStorage migration atomic + comment** (1 file, 4-5 tests)
4. **F1.a — Move MyChoose to domain** (1 file move + 5 import updates)
5. **F1.b — Widget factory via Session** (touches Session, form_requests, plugin entry, tests)
6. **F4 — HxCallbackManager errors list** (1 file edit + 1 Session property + 2 tests)
7. **F6 — ReconWorkspace lazy model** (1 file edit + grep call sites + 3 tests)
8. **F5 — Widget tests** (2 test files extended)

Final: full `pytest` + `mypy` + `ruff` + `build_plugin.py` smoke.

---

## References

- Architecture review: chat session trước (findings F1–F8)
- `docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md` — upstream rewrite design (lịch sử, không tham chiếu implementation)
- `CLAUDE.md` — project-specific guidance (sẽ update nhỏ: bỏ CHANGELOG ref)