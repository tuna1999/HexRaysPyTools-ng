# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan

Plugin IDA Pro (Python) hỗ trợ Hex-Rays decompiler: tái cấu trúc struct, quản lý class/vtable, thao tác code (recast/rename/swap if-else), và theo dõi field cross-reference. Phân phối dưới dạng HCLI archive. Phiên bản 2.0.0 là bản viết lại hoàn toàn từ v1.x, dùng Python 3.11+, PySide6, IDA 9.0–9.3.

## Lệnh thường dùng

```bash
# Cài đặt môi trường dev
pip install -e ".[dev]"

# Chạy toàn bộ test + coverage gate (80%)
pytest -v

# Một file test cụ thể
pytest tests/domain/test_session.py -v
pytest tests/domain/actions/test_recast_action.py -v

# Một test function
pytest tests/domain/actions/test_registry.py::test_registry_count -v

# Type check (strict mode)
mypy --strict src/hexrays_pytools/

# Lint
ruff check src/hexrays_pytools/ tests/ tools/
ruff check --fix <file>  # auto-fix

# Build HCLI archive (output: dist/hexrays_pytools_ng-1.0.0.zip)
python tools/build_plugin.py

# Test trong IDA thật (headless) — cho các module đã omit khỏi coverage
# KHÔNG có script tự động; cần tay cài đặt qua hcli và mở một IDB test
hcli plugin install dist/hexrays_pytools_ng-1.0.0.zip
```

`pytest` chạy được hoàn toàn không cần IDA nhờ `tools/mock_ida.py` (cài đặt qua `tests/conftest.py`).

## Kiến trúc 5-layer

Thư mục `src/hexrays_pytools/` chia theo layer, phụ thuộc chỉ đi xuống:

| Layer | Thư mục | Phụ thuộc | Mục đích |
|-------|---------|-----------|----------|
| 1 | `pure/` | (không) | Logic Python thuần, không IDA: `name_mangle`, `scoring`, `toml_template`, `result` |
| 2 | `infra/` | IDA | Wrapper mỏng có thể mock: `arch/arch.py`, `idb/netnode.py` |
| 3 | `domain/` | IDA, có thể Qt | Business logic (sub-packages: `types/`, `scanner/`, `recon/`, `xrefs/`, `templated/`, `til/`, `graph/`, `ctree/`, `browser/`, `actions/`) |
| 4 | (root) | mọi thứ | Plugin entry: `plugin.py`, `session.py`, `settings.py`, `__main__.py` |
| 5 | `ui/` | mọi thứ | Widget Qt (PySide6): `widgets/`, `chooser.py`, `widgets_common.py` |

Quy tắc bất di bất dịch: **không có import ngược lên layer trên**. Khi sửa module, hãy xác nhận trước khi viết bất kỳ `from domain...` nào từ `pure/`, hoặc `from ui...` từ `domain/`.

## Vòng đời plugin

`plugin.py:HexRaysPyToolsPlugin` (subclass `idaapi.plugin_t`) quản lý init/run/term. `Session` dataclass (`domain/session.py`) là container cho mọi state mutable, thay thế hoàn toàn biến toàn cục module-level từ bản gốc.

**Trình tự init** (`plugin.py:57`):
1. `idaapi.init_hexrays_plugin()` — nếu fail trả `PLUGIN_SKIP`.
2. `Session().open()` → load HCLI settings, init caches (`Consts`), init workspaces (`ReconWorkspace`, `XrefStorage`).
3. `HxCallbackManager.install()` rồi đăng ký 4 handler: `MemberDoubleClick` (hxe_double_click), `PotentialNegativeCollector`, `StructXrefCollector`, `SilentIfSwapper` (3 cái sau cho hxe_maturity).
4. `ActionRegistry.register_all()` đăng ký 27 actions với IDA.

**Trình tự term** làm ngược lại: unregister actions → detach callbacks → `Session.close()` (flush xrefs nếu `store_xrefs=true`) → `idaapi.term_hexrays_plugin()`.

## Hợp đồng plugin IDA 9.x (rất dễ vỡ)

Ba quy tắc này đã từng gây native crash — được guard bởi `tests/test_plugin.py`:

1. **`init`/`run`/`term` PHẢI là instance methods** (có `self`), KHÔNG được `@classmethod`/`@staticmethod`. SWIG virtual-method binding của IDA 9.x yêu cầu descriptor instance.
2. **`PLUGIN_ENTRY` PHẢI là function** trả về instance mới. Trong `plugin.py:116`, function này **resolve class qua import tại call-time** (`from hexrays_pytools.plugin import HexRaysPyToolsPlugin`) vì IDA exec entry file trong synthetic namespace `__plugins__<name>` và re-bind `PLUGIN_ENTRY` vào đó — globals ở call-time không chứa class.
3. **`hexrays_pytools_entry.py`** ở repo root có dual-mode path resolution: hoạt động cho cả layout release (flat) và dev (src-layout). Nó cũng **inject `PySide6.QtGui` vào `sys.modules['__main__']`** trước khi IDA 9.3 gọi `TWidgetToPySideWidget` (cần thiết cho `PluginForm.FromCapsule` lookup).

## ActionRegistry — 27 actions tường minh

`domain/actions/registry.py` liệt kê **tất cả 27 action class theo tên** trong `ACTION_CLASSES` tuple, sau đó `_build_actions()` lazy-import theo spec order. Đây là sự thay thế cho pattern side-effect import của bản gốc — KHÔNG thêm action mới qua monkey-patching; phải khai báo trong tuple này.

Các nhóm action: 3 form-request (ShowGraph/Classes/StructureBuilder), 3 function-signature (ConvertToUsercall/AddRemoveReturn/RemoveArgument), 5 scanner (Shallow/Deep/RecognizeShape/DeepScanReturn/DeepScanFunctions), 4 struct (FindFieldXrefs/CreateNewField/CreateVtable/GetStructureBySize), 2 misc (GuessAllocation/SwapThenElse), 2 recast (Shift+L/R), 6 rename (Ctrl+N các loại), 2 containing-structure.

**Quy ước hotkey quan trọng**: `RenameMemberFromFunctionName` dùng `Ctrl+Alt+N` (không phải `Ctrl+N` như bản gốc) để tránh đụng `RenameOther`. Đây là hotkey collision fix, có thể gây tranh cãi với người dùng cũ.

**Popup attachment**: Khi đăng ký một `HexRaysPopupAction` (subclass của `Action` có `menu_path`), `registry.py:152` tự động bọc nó trong `HexRaysPopupRequestHandler` và đăng ký cho `hxe_populating_popup`. Hotkey vẫn hoạt động nếu không làm bước này, nhưng action sẽ không xuất hiện trong menu chuột phải.

## HxCallbackManager

`domain/actions/hx_callback.py` cài đặt một dispatcher duy nhất qua `idaapi.install_hexrays_callback`, dispatch tới các handler theo `event_id`. Handler chỉ là object có method `handle(event, *args)` — KHÔNG phải subclass `idaapi.hxe_callback_t`. Mọi exception trong handler bị log và nuốt (không crash IDA).

## Lưu trữ & Settings

**Xref storage** dùng netnode (`infra/idb/netnode.py`) thay cho `idc.create_array`. `XrefStorage` ở `domain/xrefs/xref_storage.py` tự động migrate dữ liệu từ array cũ `$HexRaysPyTools-ng:XrefStorage` sang netnode mới `$hexrays_pytools_ng/xref_storage` trên first load.

**Settings** (5 cái) đọc qua `ida_settings.get_current_plugin_setting` trong `domain/settings.py`, map vào `Session`. Khai báo trong `ida-plugin.json` dưới `plugin.settings`. Set qua `hcli plugin config`, không sửa file `.cfg` như v1.x.

## Ctree walking — không mock được

Các file `domain/ctree/{recast,rename,swap_if,negative_offsets}.py` thao tác trực tiếp trên live Hex-Rays ctree object (`citem_t`, `cexpr_t`). Mock của `tools/mock_ida.py` không reproduce được dispatch của `ctree_parentee_t`, nên:

- `visit_expr`/`leave_expr`/`_check_call`/`_recursive_process` không reachable từ unit test.
- `pyproject.toml` (tool.coverage.report.omit) liệt kê các module này + `domain/scanner/visitor_base.py` + tất cả `domain/actions/*activate()` paths làm omit.
- Phần Python-level control flow vẫn được test trực tiếp.
- End-to-end verification yêu cầu IDA thật (idat headless) + manual right-click testing. **KHÔNG thêm unit test mới cho các module này** — chúng sẽ luôn pass với mock và tạo ảo giác coverage.

## Module phụ thuộc khác đáng biết

- `domain/scanner/helpers.py` — `decompile_function` (guard `DecompilationFailure`) + `FunctionTouchVisitor` (pre-decompile callees để Hex-Rays cache arg types). KHÔNG bị omit, có unit test cho control flow.
- `domain/recon/workspace.py:ReconWorkspace` lazily constructs `StructureModel` rỗng on first `.model` access (post-F6) để scanner actions ghi được mà không cần mở Structure Builder widget trước.
- `domain/actions/swap_if_action.py` + `hx_events.py:SilentIfSwapper` dùng `SpaghettiVisitor`/`SwapThenElseVisitor` để tự động swap nhánh if-else.
- `ui/widgets_common.py:form_to_pyside_widget` — IDA 9.4 workaround: `PluginForm.FormToPySideWidget` bị hỏng (tìm `QWidget` trong `QtGui` thay vì `QtWidgets`); dùng `TWidgetToQtPythonWidget` thay thế.

## Build & phân phối

`tools/build_plugin.py` đóng gói thành `dist/hexrays_pytools-X.Y.Z.zip` chứa: `ida-plugin.json`, `hexrays_pytools_entry.py`, package, `LICENSE`, `README.md`. Layout trong ZIP là flat (`hexrays_pytools/` ngang hàng với entry file) — khác với src-layout dev checkout. Entry file detect cả hai layout qua path check.

Để install local: `hcli plugin install dist/hexrays_pytools_ng-1.0.0.zip`.

## Trước khi commit

- `pytest` pass, coverage ≥ 80% (gate enforce qua `pyproject.toml`).
- `mypy --strict` clean.
- `ruff check` clean.
- Nếu đụng vào `plugin.py`/`hexrays_pytools_entry.py`, xác nhận `tests/test_plugin.py` vẫn pass — đây là guard cho các IDA 9.x contract bugs đã từng crash native.
- Nếu thêm action mới: thêm vào `ACTION_CLASSES` + `_build_actions()` trong `registry.py`, đảm bảo count = 27 cập nhật nếu cần.

## Tài liệu tham chiếu nội bộ

- `docs/architecture.md` — module map + session lifecycle (ngắn, đã tóm tắt ở trên).
- `docs/superpowers/specs/2026-06-18-hexrays-pytools-rewrite-design.md` — design rationale đầy đủ cho v2.0.0 rewrite.
- `docs/superpowers/plans/2026-06-18-hexrays-pytools-rewrite.md` — task breakdown.
- `refs/HexRaysPyTools/` — bản v1.x gốc (legacy) để tham khảo khi cần so sánh.