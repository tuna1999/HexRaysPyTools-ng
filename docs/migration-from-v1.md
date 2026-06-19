# Migration from v1.x

v2.0.0 is a complete rewrite. Most user-facing functionality is preserved, but with a few changes:

## Settings
- Settings are now stored via HCLI ida-settings (no more `.cfg` file)
- 5 settings with same keys: `log_level`, `propagate_through_all_names`, `store_xrefs`, `scan_any_type`, `templated_types_file`
- Configure via `hcli plugin config` instead of editing the `.cfg` file

## Hotkeys
- One hotkey change: `RenameMemberFromFunctionName` moved from `Ctrl+N` to `Ctrl+Alt+N` to avoid collision with `RenameOther` (which still uses `Ctrl+N`)

## Storage
- Struct field xrefs are now stored in IDA netnodes (not `idc.create_array`)
- Auto-migrate from v1.x format on first load (one-time)

## No code changes required for end users
If you just use the plugin interactively, no code changes are needed.
