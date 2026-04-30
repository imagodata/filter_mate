# Export Pipeline Checkpoint — 2026-04-30

**Audience**: any developer about to touch `core/export/`, `core/tasks/export_handler.py`, `infrastructure/streaming/result_streaming.py`, or `ui/controllers/exporting_controller.py`.

**Status at HEAD `cd6adaf1`** on `main`: every silent shipping bug from the deep audit is closed, ~943 LOC of dead code is removed, the format registry is drift-proof, and the partial-file-on-failure UX is fixed. **90 export-specific tests** (1481 in full unit suite), all green.

---

## Quick orientation

The live export path is the **only** one in this codebase. Everything else was dead code that has been deleted.

```
pushButton_action_export
  → filter_mate_dockwidget.launchTaskEvent('export')
    → [optional ExportGroupRecapDialog for GPKG/KML preserve_groups]
      → emit launchingTask
        → TaskOrchestrator.dispatch_task('export')
          → FilterMateApp._execute_filter_task('export', params)   ← was the B-bug site
            → FilterEngineTask(task_action='export')                (worker thread)
              → ExportHandler.execute_exporting()                   [core/tasks/export_handler.py]
                ├── validate_export_parameters                      [core/export/export_validator.py]
                ├── BatchExporter (folder/zip)                      [core/export/batch_exporter.py]
                ├── LayerExporter (single, multi-to-dir, GPKG)      [core/export/layer_exporter.py]
                ├── StreamingExporter (large datasets)              [infrastructure/streaming/result_streaming.py]
                ├── StyleExporter (QML/SLD/LYRX sidecar)            [core/export/style_exporter.py]
                ├── (deferred) write_layer_tree_to_gpkg             [core/export/gpkg_layer_tree_writer.py]
                ├── (deferred) write_layer_styles_to_gpkg           [same file — added in this session for H1/H2]
                └── (deferred) merge_kml_with_folders               [core/export/kml_folder_writer.py]
```

The deferred steps run on the **main thread** in `FilterEngineTask.finished()` because they need QGIS object access that's unsafe from the worker thread.

---

## What was fixed in this session (10 commits, `124bc34f..cd6adaf1`)

### Tier 1 — silent shipping bugs (all 5 closed)

| Bug | Symptom | Commit |
|---|---|---|
| **B-bug** | Click Export with no current_layer → silent log-only error, no UI feedback | `124bc34f` |
| **B3-leak** | SHP DBF field truncation warnings logged but never shown to user | `224639f0` |
| **B3-leak-batch** | Partial batch export (7/10 layers) shown as full success | `224639f0` |
| **H1** | GPKG + reprojection silently dropped `save_styles` | `6868bcd1` |
| **H2** | Streaming + GPKG wrote `.qml` sidecar instead of embedded | `6868bcd1` |

### Tier 2 — dead code removed (~943 LOC)

| Target | LOC | Commit |
|---|---|---|
| `core/services/export_service.py` (3 broken imports, zero callers) | -422 | `bcc1eb92` |
| `adapters/qgis/tasks/export_task.py` (`ExportTask`, `BatchExportTask`, never wired, missing all hardening) | -348 | `e18d4e53` |
| `ExportingController.execute_export()` chain (stubs that "simulated" success) | -131 | `f3aa3a50` |
| `BatchExporter.request_cancel`/`_cancel_requested` (overwritten by monkey-patch) | -14 | `442f47e3` |
| `StreamingConfig.memory_limit_mb` + dead `should_use_streaming(layer)` | -28 | `550e78cc` |

### Tier 3 — robustness (3 of 4 closed)

| Issue | Fix | Commit |
|---|---|---|
| Empty-layer streaming raised `FileNotFoundError` | Early-return at top of `export_layer_streaming` with `empty_layer=True` flag | `c0616875` |
| Misleading post-write cancel message | Removed the unreachable check (standard write is uninterruptible by design) | `c0616875` |
| Partial files left on disk after writer failure | New `cleanup_partial_export(path, datatype)` helper + 3 wire-points | `2b6492bc` |
| Single-layer non-streaming export uninterruptible | **DEFERRED** — needs API design (cancel callback to writer) | — |

### Tier 4 — architecture (1 of 4 closed)

| Issue | Fix | Commit |
|---|---|---|
| 3× drifting driver/extension maps | Single `_FORMAT_REGISTRY`; both lookup dicts derived; streaming local map deleted | `cd6adaf1` |
| 3× drifting `ExportConfig` dataclasses | **DEFERRED** — controller's `ExportConfiguration` has different fields | — |
| `mapLayersByName` from worker thread | **DEFERRED** — needs URI-store-recreate refactor per CLAUDE.md pattern | — |
| Hardcoded UTF-8 encoding | **DEFERRED** — needs dialog UI for override | — |

---

## Key new pieces (added this session)

### 1. `_FORMAT_REGISTRY` — single source of truth for format lookups

Location: top of [core/export/layer_exporter.py](../../core/export/layer_exporter.py)

```python
@dataclass(frozen=True)
class _FormatSpec:
    ogr_driver: str          # Canonical OGR driver name (e.g. 'ESRI Shapefile')
    extension: str           # Primary extension with leading dot (e.g. '.shp')
    aliases: tuple = ()      # Additional uppercase aliases (don't repeat ogr_driver.upper())

_FORMAT_REGISTRY = (
    _FormatSpec('GPKG',           '.gpkg',    ()),
    _FormatSpec('ESRI Shapefile', '.shp',     ('SHP', 'SHAPEFILE')),
    ...
)

# Both dicts derived; same keyset by construction:
_DRIVER_BY_ALIAS, _EXTENSION_BY_ALIAS = _build_lookup_dicts()
OGR_EXTENSION_MAP = _EXTENSION_BY_ALIAS
LayerExporter.DRIVER_MAP = _DRIVER_BY_ALIAS
```

**To add a format**: append a single `_FormatSpec(...)` entry. Both lookup dicts auto-update, and the validator's `known_keys/known_values` automatically expand. The `TestFormatRegistry` tests guard the invariants (no duplicate aliases, all extensions start with `.`, dialog choices present, etc.).

### 2. `cleanup_partial_export(output_path, datatype)` — orphan-file cleanup

Location: [core/export/layer_exporter.py](../../core/export/layer_exporter.py) (after the registry)

Used by 3 paths:
- `LayerExporter.export_single_layer` — on writer error AND uncaught exception
- `LayerExporter._export_to_gpkg_reproject` — on per-layer writer failure
- `StreamingExporter.export_layer_streaming` — via `_cleanup_partial_streaming_output` (local copy, avoids infrastructure→core layer violation)

Backed by `_FORMAT_SIDECARS` — explicit per-driver list of extensions sharing the basename (SHP has 17 known sidecars, GPKG has the SQLite WAL/journal/shm trio, etc.). Files belonging to **other** layers in the same directory are not touched (extension match is exact, not glob).

**To extend**: add a key to `_FORMAT_SIDECARS` for new formats. Driverless cleanup falls back to "remove only the exact target_path" — safe but minimal.

### 3. `write_layer_styles_to_gpkg(gpkg_path, [(layer, table_name)])` — sqlite3 style embedding

Location: [core/export/gpkg_layer_tree_writer.py](../../core/export/gpkg_layer_tree_writer.py) (appended at the end)

Mirrors what `processing.run('qgis:package', SAVE_STYLES=True)` does internally. Used by:
- `LayerExporter._export_to_gpkg_reproject` (H1 fix) — after the writeAsVectorFormatV3 loop, with `(layer, layer.name())` pairs
- `ExportHandler._export_with_streaming` (H2 fix) — when datatype.upper() == 'GPKG'

Idempotent. Never raises into the caller. Returns `False` on any error (logged at warning level — data is on disk regardless, styles are best-effort). Reads geometry column names from `gpkg_geometry_columns` to populate `f_geometry_column` correctly; falls back to `''` for non-spatial tables.

### 4. `ExportHandler._last_warnings` — boundary-flattening fix for B3-leak

Location: [core/tasks/export_handler.py:38-71](../../core/tasks/export_handler.py)

```python
class ExportHandler:
    def __init__(self):
        self._last_warnings: List[str] = []
    
    def _collect_warnings(self, result):
        # Handles ExportResult.warnings, BatchExportResult.failed_layers, .skipped_layers
        ...
    
    def execute_exporting(...):
        self._last_warnings = []  # reset
        ...
        self._collect_warnings(result)  # called after each result acquisition
```

Drained by `FilterEngineTask.execute_exporting()` into `self.warning_messages` (existing channel that `FinishedHandler` already displays via `iface.messageBar()`). No new plumbing — reuses the existing warning channel.

---

## What remains (Tier 3+, prioritized)

### High value, deferred

**Test backfill for embedding code** (~3-4h)
- `write_layer_tree_to_gpkg` (744 LOC sqlite3+xml in `gpkg_layer_tree_writer.py`) — manipulates user GPKG output, zero coverage. **High blast radius** if buggy: silent corruption of user data.
- `kml_folder_writer.py` (208 LOC xml.etree merge) — same risk class, smaller surface.
- `_save_lyrx` JSON output (`style_exporter.py`) — currently only the basename path is tested.

**Single-layer write uninterruptible** (~3h, design needed)
- `LayerExporter.export_single_layer` calls `writeAsVectorFormatV3` synchronously. Cancel signal isn't honored.
- Fix would require accepting a `feedback: QgsFeedback` param and threading it through to QGIS Processing — non-trivial API surface change.

### Medium value, deferred

**`mapLayersByName` from worker thread** (~4h)
- Violates CLAUDE.md pattern: "QGIS layers are NOT thread-safe — store URI in `__init__`, recreate in `run()`."
- Two call sites (`export_handler.py:96`, `layer_exporter.py:739`).
- Latent race in practice; fix is the URI-resolve-in-init pattern.

**Hardcoded UTF-8 encoding** (~2h)
- 5 places hardcode `options.fileEncoding = 'UTF-8'` with no override.
- Real-world risk: Latin-1/CP1252 SHP sources produce mojibake if QGIS's read-side encoding wasn't set correctly upstream.
- Fix: add `encoding` field to ExportConfig + dialog dropdown.

**`ExportingController.ExportConfiguration` dataclass dedup** (~3-5h)
- Different fields (mode, callbacks) — consolidating means breaking the controller's public surface.
- Currently the controller is a config-state holder; the actual export goes through FilterEngineTask. Could be cleaned up after the controller's role is decided.

---

## How to run the tests

```bash
# Full export test file (90 tests, ~1.5s):
python -m pytest tests/unit/core/export/test_export_bugfix.py

# Full unit suite (1481 tests, ~30s):
python -m pytest tests/unit/

# Single test class — useful when working on a specific area:
python -m pytest tests/unit/core/export/test_export_bugfix.py::TestFormatRegistry
```

The test file has clearly delimited sections (one class per audit finding). Add new tests under the section that covers the area you're working on.

### conftest gotcha

[tests/unit/core/export/conftest.py](../../tests/unit/core/export/conftest.py) builds a synthetic `filter_mate.*` import graph so the export modules can be tested without QGIS. It loads:
- `core/export/{layer,batch,style,export_validator,gpkg_layer_tree_writer}.py` as real modules
- `core/tasks/export_handler.py` as a real module
- `infrastructure/streaming/result_streaming.py` as a real module

It does NOT alias `infrastructure` at the top level (would clobber unrelated test dirs that have their own `infrastructure.database`, `infrastructure.cache`, etc.). When testing streaming directly, **import via the full `filter_mate.infrastructure.streaming.result_streaming` path** — see `TestEmptyLayerStreaming` and `TestStreamingExporterCleansPartialOutput` for examples.

---

## Patterns to follow

### When adding a new export format

1. **Append to `_FORMAT_REGISTRY`** in `layer_exporter.py`. Both `OGR_EXTENSION_MAP` and `DRIVER_MAP` auto-update. The validator's `known_keys` check auto-expands.
2. **Add sidecar entries to `_FORMAT_SIDECARS`** if the format has multiple files (SHP-style). Otherwise the cleanup helper falls back to "exact path only".
3. **Run the registry tests** (`TestFormatRegistry`) — they enforce invariants (no duplicate aliases, all extensions start with `.`, etc.).

### When adding a new export path

The handler boundary is the right level for new paths:
- Read params from `task_parameters['task']['EXPORTING']`
- Route through one of the existing branches in `ExportHandler.execute_exporting`
- Collect warnings with `self._collect_warnings(result)` so they reach the user via `FinishedHandler`
- Clean up partials with `cleanup_partial_export(path, datatype)` on failure

### When the export path needs main-thread access (QGIS object lifecycle)

Use the deferred pattern: store a `_pending_*` dict on the handler in worker thread, drain it in `FilterEngineTask.finished()` on the main thread. See:
- `_pending_layer_tree_write` (filter_task.py:2937-2956 + gpkg_layer_tree_writer.py)
- `_pending_kml_merge` (filter_task.py:2960-2966 + kml_folder_writer.py)

### When you write to the GPKG `layer_styles` table

Use `write_layer_styles_to_gpkg(gpkg_path, [(layer, table_name)])` from `gpkg_layer_tree_writer.py`. Don't roll your own SQL — the helper handles schema creation, geometry column resolution, idempotent inserts.

---

## Anti-patterns (what NOT to do)

1. **Don't add a new driver/extension dict.** Use `_FORMAT_REGISTRY`. The drift-proofing was the whole point.
2. **Don't call `iface.messageBar()` from the worker thread.** Crashes QGIS with access violation. See [layer_exporter.py:530-532](../../core/export/layer_exporter.py) for the preserved comment.
3. **Don't use `QDialog.exec()` in any export-flow dialog.** Crashes QGIS 3.44 with access violation in `QgsCustomization::preNotify`. Use `dialog.open()` (non-blocking) with `accepted`/`rejected` signal callbacks. See [filter_mate_dockwidget.py:6592-6595](../../filter_mate_dockwidget.py).
4. **Don't write SQL to the GPKG `layer_styles` table directly.** Use the helper.
5. **Don't add a `_FORMAT_SIDECARS` glob pattern.** Extension match is exact for a reason — globbing can delete unrelated user files in the same directory.
6. **Don't skip the conftest extension when testing streaming directly.** Import via `filter_mate.infrastructure.streaming.result_streaming` to avoid alias clobbering in unrelated test dirs.

---

## Cross-references

- Original audit (5-pass deep analysis): `~/.claude/projects/.../memory/project_export_audit_2026_04_30.md` (in the auto-memory store, not the project repo)
- Related session: ad54833b (12-fix hardening, ~April 29) — closed the writer-level bugs that this session built on. f769f134 (3-fix earlier hardening, April 21) — sidecar naming, LIBKML normalization.
- The recap dialog UX: [ui/dialogs/export_group_recap_dialog.py](../../ui/dialogs/export_group_recap_dialog.py) — non-blocking modal pattern for QGIS 3.44 compatibility.

## Lessons learned (worth carrying to next session)

1. **The boundary-flattening pattern is sneaky.** B3-leak existed because each layer (LayerExporter, ExportHandler, FinishedHandler) looked correct in isolation, but the 3-tuple return at the handler boundary silently lost the `warnings` field. Always check what data your boundary discards.
2. **Dead code accumulates around active code.** ~943 LOC of dead code (3 stub entry points + ornamental fields) was sitting next to the live path. Lookalike code is harder to delete than dead-and-obvious code.
3. **The `validate-each-large-deletion` discipline matters.** The user feedback memory ("Pas de batch destructif large — valider chaque grande suppression") slowed the cleanup pass but caught one scope-mismatch (Option B vs C in the controller cleanup) that would have been a regression in autonomous mode.
4. **Test conftest pollution is a real risk.** My initial conftest extension (aliasing `sys.modules['infrastructure']`) silently broke 3 unrelated test files until I scoped it to `filter_mate.infrastructure.*`. Watch for cross-directory conftest interactions.
5. **Per-feature CRS transform is a separate concern from writer CRS.** B2 fix (`feature.geometry().transform(...)` per feature in streaming) is the correct way; just setting `writer_crs` only stamps the `.prj`. The writer doesn't transform on `addFeature()`.
