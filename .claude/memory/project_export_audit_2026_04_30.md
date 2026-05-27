---
name: Export pipeline deep audit (2026-04-30)
description: 5-pass audit of FilterMate export pipeline — 5 confirmed shipping bugs, ~900 LOC dead code, 6 latent risks, 4 test gaps. Use when working on any export-related code or tickets.
type: project
originSessionId: b6056b23-a957-460a-bc4c-1351b977cd20
---
# Export pipeline audit — 2026-04-30 (post-v4.7.1)

5-pass code review of `core/export/*`, `core/tasks/export_handler.py`, `infrastructure/streaming/result_streaming.py`, `ui/managers/export_dialog_manager.py`, `ui/controllers/exporting_controller.py`, `core/services/export_service.py`, `adapters/qgis/tasks/export_task.py`. ~6000 LOC reviewed. Ran on `main` at commit `6dac9f12` (release v4.7.1). Recent hardening commit `ad54833b` (12 fixes) is solid; gaps below are what's left.

## Status (post-2026-04-30 follow-up session)

**Tier 1 (all silent shipping bugs)** + **Tier 2 (cleanup)** complete in 8 commits on `main`:

| # | Issue | Commit | Status |
|---|---|---|---|
| 1 | **B-bug** — current_layer guard | `124bc34f` | ✅ FIXED |
| 2 | **B3-leak** — warnings dropped at handler boundary | `224639f0` | ✅ FIXED |
| 3 | **B3-leak-batch** — batch failures dropped | `224639f0` | ✅ FIXED (same commit) |
| 4 | Dead `core/services/export_service.py` | `bcc1eb92` | ✅ DELETED (-422 LOC) |
| 5 | Dead `adapters/qgis/tasks/export_task.py` | `e18d4e53` | ✅ DELETED (-348 LOC net) |
| 6 | Stub `ExportingController.execute_export` chain | `f3aa3a50` | ✅ DELETED (-131 LOC) |
| 7 | Dead `BatchExporter._cancel_requested`/`request_cancel` | `442f47e3` | ✅ DELETED + contract documented |
| 8 | Ornamental `StreamingConfig.memory_limit_mb` | `550e78cc` | ✅ DELETED + dead `should_use_streaming` removed |
| 9 | **H1** — GPKG + reprojection drops save_styles | `6868bcd1` | ✅ FIXED (new write_layer_styles_to_gpkg helper) |
| 10 | **H2** — streaming + GPKG writes .qml sidecar | `6868bcd1` | ✅ FIXED (same commit) |
| 11 | Empty-layer streaming raises FileNotFoundError | `c0616875` | ✅ FIXED (early-return with empty_layer=True flag) |
| 12 | Misleading post-write cancel check | `c0616875` | ✅ FIXED (post-write check removed; standard write is uninterruptible by design) |
| 13 | Partial files left on disk after write failure | `2b6492bc` | ✅ FIXED (new cleanup_partial_export helper + 3 wire-points + 11 tests) |
| 14 | 3× drifting driver/extension maps (H4) | `cd6adaf1` | ✅ FIXED (single _FORMAT_REGISTRY; both dicts derived; streaming local map deleted; 9 new tests) |

Net: ~+130 LOC tests, ~-1030 LOC dead code. Every silent UX bug + 5 data-fidelity bugs from the original audit are now closed; ~1031 LOC of dead code removed; 78 export-related tests on `main` (1461 in full unit suite).

Still open from the original audit (Tier 3 robustness + Tier 4 architecture + Tier 5 tests):
- Single-layer non-streaming export uninterruptible (writer is synchronous).
- No transactional writes (`.tmp` + rename) on any path.
- 3× drifting `ExportConfig`/`ExportFormat`/`ExportResult` dataclasses (only one duplicate removed; controller still has its own).
- 3× drifting driver/extension maps.
- `mapLayersByName` from worker thread (CLAUDE.md violation).
- Hardcoded UTF-8 encoding (no override).
- Test gaps: `write_layer_tree_to_gpkg` (older 744 LOC path), `kml_folder_writer`, LYRX JSON contents.

Reusable helper introduced this session: `write_layer_styles_to_gpkg(gpkg_path, [(layer, table_name)])` in `core/export/gpkg_layer_tree_writer.py`. Idempotent, never raises into caller, mirrors `processing.run('qgis:package', SAVE_STYLES=True)`. Available for any future export path that bypasses qgis:package.



## Scope

The live export path is: `pushButton_action_export` → `FilterEngineTask(task_action='export')` → `ExportHandler.execute_exporting` → `LayerExporter | BatchExporter | StreamingExporter`. Three other "entry-points" (`ExportService`, `ExportingController._execute_*_export`, `adapters/qgis/tasks/ExportTask`) are dead/stub.

## Confirmed shipping bugs (priority-ordered)

**B-bug** — `filter_mate_app.py:1145` rejects export when `dockwidget.current_layer is None` (silent log-only error). Repro: open Export tab without picking layer in Exploring, click Export → nothing happens. Verified via AST check 2026-04-30. **Why it matters:** export is documented as "INDEPENDENT from exploring" in 4 docstrings, but the dispatcher contradicts this. **Fix sketch:** scope guard with `if task_name != 'export'` + add `iface.messageBar().pushWarning()` for the cases that DO need current_layer.

**H1** — `_export_to_gpkg_reproject` (`layer_exporter.py:539`) silently drops `save_styles`. The reprojection branch bypasses `processing.run("qgis:package", SAVE_STYLES=...)` and never re-implements style writing. Triggered when user picks GPKG + target CRS that differs from any source CRS. **Fix sketch:** after the writeAsVectorFormatV3 loop, sqlite3 INSERT into `layer_styles` table (helpers exist in `gpkg_layer_tree_writer.py`).

**H2** — Streaming + GPKG export writes `.qml` sidecar instead of embedding in `layer_styles`. `export_handler.py:598` calls `save_layer_style` (sidecar writer) without GPKG-aware branch. Inconsistent with non-streaming GPKG path which embeds.

**B3-leak** — SHP DBF pre-flight warnings (B3 fix from `ad54833b`) are computed in `LayerExporter` (`layer_exporter.py:438` populates `result.warnings`) but `ExportHandler.execute_exporting` returns a 3-tuple `(success, message, error_details)` that **drops the warnings**. They never reach `messageBar`. User truncating `verylongfieldname` to `verylongfi` sees no indication.

**B3-leak-batch** — Same pattern: `error_details` (per-layer batch failure summary) is set by handler at `export_handler.py:219, 236` but `FinishedHandler:429-436` only renders `task_message`, never `error_details`. Partial batch failures (e.g. 7/10 success) display as full success.

## Dead/stub code (~900 LOC, safe to delete)

| File | Status | Why dead |
|---|---|---|
| `core/services/export_service.py` (422 LOC) | **Broken** — 3 imports for module-level functions that don't exist (`export_single_layer`, `export_batch_layers`, `export_to_geopackage`). Verified via AST check 2026-04-30. Zero callers outside its own file. |
| `adapters/qgis/tasks/export_task.py` (`ExportTask`, `BatchExportTask`, ~340 LOC) | Exported from `__init__.py` but instantiated nowhere. Missing all `ad54833b` hardening (no CSV options, no SHP pre-flight, no name disambiguation). |
| `ui/controllers/exporting_controller.py::_execute_*_export` (~100 LOC) | Stubs with explicit `# Simulate successful export` comments. Plumbing wired into orchestrator but never called. |
| `BatchExporter.request_cancel` / `_cancel_requested` | Dead because `export_handler.py:196` monkey-patches `batch_exporter.is_canceled = is_canceled` (verified 2026-04-30 — confirmed at line 196). |
| `StreamingConfig.memory_limit_mb` | Field exists with factories (`for_memory_constrained`, `for_large_dataset`) but no code reads it. Pure ornament. |

## Latent risks

- **Thread-safety**: `mapLayersByName` called from worker thread at `export_handler.py:96` and `layer_exporter.py:739`. Violates project's own pattern from CLAUDE.md ("store URI in __init__, recreate in run()"). Race vs main-thread layer add/remove.
- **Encoding**: 5 hardcoded `options.fileEncoding = "UTF-8"` with no override. Risk of mojibake for Latin-1/CP1252 SHP sources where the layer's dataProvider encoding wasn't set correctly upstream.
- **Single-layer non-streaming export is uninterruptible**. `writeAsVectorFormatV3` blocks. The post-write `is_canceled()` check at `export_handler.py:339` is misleading — fires after the file is already written.
- **No transactional writes** — partial files left on disk after disk-full / mid-write failure. Affects all paths.
- **3× `ExportConfig`/`ExportFormat`/`ExportResult` dataclasses** drift between `core/export/`, `core/services/export_service.py`, `ui/controllers/exporting_controller.py`. Same for 3× driver/extension maps (`OGR_EXTENSION_MAP`, `LayerExporter.DRIVER_MAP`, `StreamingExporter.driver_map`).
- **Side-effect on PG**: `FinishedHandler:175` cleans up materialized views on every export, even if no filter active.

## Test gaps

- 24 tests in `tests/unit/core/export/test_export_bugfix.py` are mock-heavy (every `QgsVectorFileWriter` is stubbed). No real GDAL roundtrip.
- B2 streaming reprojection test only checks param passing; doesn't verify `feature.geometry().transform()` actually ran.
- Zero coverage: `gpkg_layer_tree_writer.py` (744 LOC sqlite3+xml), `kml_folder_writer.py` (208 LOC), LYRX JSON contents, H1, H2, B-bug, B3-leak, empty-layer behavior, `_pending_layer_tree_write`/`_pending_kml_merge` lifecycle.

## Recommended PR sequence

1. **PR 1** (Tier 1) — B-bug + B3-leak + B3-leak-batch + error_details routing. ~5h. Closes all silent UX gaps.
2. **PR 2** (Tier 1) — H1 + H2 (GPKG style preservation across reprojection and streaming). ~5h.
3. **PR 3** (Tier 2 cleanup) — Delete `export_service.py`, `export_task.py`, controller stubs, `request_cancel`/`memory_limit_mb` ornaments. Single PR, zero behavioral risk, ~900 LOC delete. ~3.5h.
4. **PR 4** (Tier 3 robustness) — Atomic writes, empty-layer short-circuit, cancel-before-write, UI lockout during export. ~5h.
5. **PR 5+** — Tier 4 dataclass/registry consolidation + Tier 5 test backfill.

Total to fully harden: ~30-35h. Tier 1 (PRs 1-2): ~10h closes every silent failure mode found.

## Why these aren't derivable from code/git alone

- The dead-code triplet (`ExportService` / `ExportTask` / `_execute_*_export` stubs) duplicates the live API surface convincingly enough that grep/blame alone won't tell you which is canonical.
- B-bug is a cross-file interaction: the dockwidget validates one way, the dispatcher validates another, the handler design assumes neither. Following any single file misses it.
- The B3-leak family is a "data exists but is dropped at boundary" pattern across 3 layers (LayerExporter populates → ExportHandler flattens → FinishedHandler ignores). Each layer in isolation looks correct.
- The `BatchExporter` monkey-patch is a 1-line side effect at `export_handler.py:196` whose impact (entire `request_cancel` mechanism becomes dead) is invisible without tracing both classes together.

## Key code references

- Live export entry: `pushButton_action_export` → `filter_mate_dockwidget.py:6580` (special-case branch with group-recap dialog) → `launchingTask.emit` → `TaskOrchestrator._handle_filter_task` → `filter_mate_app.py:1139` (B-bug guard) → `FilterEngineTask` → `ExportHandler.execute_exporting`.
- Pre-export dialog uses `dialog.open()` not `exec()` because of QGIS 3.44 access violation in `QgsCustomization::preNotify` — comment at `filter_mate_dockwidget.py:6592`.
- Deferred main-thread embedding (`_pending_layer_tree_write`, `_pending_kml_merge`) consumed in `filter_task.py:2937-2966`. Implicit single-producer-single-consumer via Qt task signal serialization — no lock, no test.
