# FilterMate - Claude Code Memory

## Project
- QGIS plugin, Python/PyQt5, hexagonal architecture
- Current branch: `main`

## Workflow preferences
- [Pas de batch destructif large](feedback_destructive_batches.md) — valider chaque grande suppression, pas de rafale de 20+ deletes parallèles

## Audits
- [Export pipeline deep audit (2026-04-30)](project_export_audit_2026_04_30.md) — 5 shipping bugs (B-bug, H1, H2, B3-leak, B3-leak-batch), ~900 LOC dead code, PR sequencing. **All Tier 1 + Tier 2 closed; partial Tier 3+4. Checkpoint for next devs in project's `.serena/memories/export_pipeline_checkpoint_2026_04_30.md`.**

## Audit & Backlog Session COMPLETE (2026-02-11)
**Full audit report**: `.serena/memories/audit_filtermate_2026_02_11.md`
**Score**: 6.5/10 → 8.5/10 → **9.0/10** (P0+P1+P2+P3 + Backlog)

### Key metrics final
- filter_task.py: **2 929 lines** (was 5 884, -50.3%) — target <3000 ACHIEVED
- dockwidget.py: **~6 480 lines** (was 7 130) — 0 manual blockSignals
- Tests: **600** (was 0) across 34 files — 2 pre-existing failures (test pollution)
- Commits this session: **32** on main
- CI/CD: GitHub Actions pytest (Python 3.10+3.12)
- 12 handlers extracted from filter_task.py (Orchestrator-Handler pattern)
- 4 managers extracted from dockwidget.py
- i18n: 19 strings wrapped in tr()/QCoreApplication.translate(), 22 languages

### Backlog items completed (9/9)
1. Pass 3 filter_task.py: 4 new handlers (-1041 lines)
2. Dockwidget Phase 2: DEFERRED to Sprint Raster
3. blockSignals: 24 pairs → SignalBlocker in dockwidget (`96e00bc6`)
4. Tests 4 backends: 141 tests (`1295c197`)
5. Tests 3 controllers: 98 tests (`1295c197`)
6. CI/CD pytest: GitHub Actions (`b207587b`)
7. Fix API get_optimal_metric_crs() (`d752583d`)
8. Fix SQL f-prefix (`935a48e8`)
9. PROVIDER_* centralized: 5 core files (`d805b555`)

### Remaining work (low priority)
- PROVIDER_* migration: ~55 UI/infra files still using string literals
- Dockwidget Phase 2: ~700 more lines extractable
- 9/12 controllers without test coverage
- 2 test pollution issues (pass in isolation, fail in suite)

## Backlog Raster & Point Cloud V1 (2026-02-11)
**Full backlog**: `BACKLOG_RASTER_POINTCLOUD_V1.md` (project root)
**Atlas research**: `.serena/memories/atlas_raster_lidar_research_2026_02_11`
**Serena summary**: `.serena/memories/backlog_raster_pointcloud_v1_2026_02_11`
- 8 EPICs, 17 User Stories, 5 sprints, 55-75 days
- MUST: R0 (foundations) → R1 (sampling) → R2 (zonal stats)
- SHOULD: R3 (highlight) + PC1 (classification/attributes/Z)
- Sprint 0 ready: US-R0.1 (cherry-pick) — pass 3 from US-R0.2 is DONE

## Config Harmonization Session (2026-02-19)
**Serena memory**: `.serena/memories/config_harmonization_2026_02_19`
**Plan**: `.claude/plans/binary-wobbling-lantern.md`

### What was done
- **P1**: min/max constraints now enforced in JSON TreeView spinboxes (`datatypes.py`)
- **P2**: 6 raw params wrapped in `{value, description}` format + backward-compat helpers
- **P3**: `config_schema.json` marked deprecated (unused in core flow)
- **P5**: FALLBACK_CONFIG fixed (deprecated THEME → COLORS.ACTIVE_THEME)
- **Inconsistency fix**: MAX_ADD_LAYERS_QUEUE aligned to 50
- **16 new configurable params** (was hardcoded): debounce timers, favorites limit, spatialite tuning, expression builder limits, query timeouts, exploration geometry

### Key files (16 modified)
- `config/config.default.json`, `config/config.py`, `config/config_schema.json`
- `ui/widgets/json_view/datatypes.py` (min/max in createEditor)
- `filter_mate_app.py`, `filter_mate_dockwidget.py`, `adapters/database_manager.py`
- `ui/widgets/custom_widgets.py`, `ui/widgets/favorites_widget.py`
- `core/tasks/task_completion_handler.py`, `core/filter/expression_builder.py`
- `adapters/backends/spatialite/interruptible_query.py`
- `infrastructure/resilience.py`, `ui/controllers/exploring_controller.py`
- `core/services/task_orchestrator.py`, `infrastructure/utils/task_utils.py`

### Config access pattern
```python
from config.config import _get_option_value, _set_option_value
# Read: _get_option_value(options.get("KEY"), default)
# Write: _set_option_value(options, "KEY", new_value)
# Both handle wrapped {value, description} and raw formats
```

## Raster Dual Panel State (2026-02-10)
- Branch `refactor/quick-wins-2026-02-10` has Phase 0 + Phase 1 + Phase 2 (partial)
- See Serena memories: `dual_panel_phase0/1/2_implementation`
- Design doc: `DUAL_PANEL_DESIGN_ATLAS.md` — full roadmap through Phase 5

## Key Patterns
- Serena memories in `.serena/memories/` - always check before starting work
- Thread safety: QGIS layers are NOT thread-safe - store URI in `__init__`, recreate in `run()`
- Signal safety: use `SignalBlocker(widget)` context manager (infrastructure/signal_utils.py)
- Dead code: verify with grep before deleting - check `__init__.py` exports too
- SQL security: always use `sanitize_sql_identifier()` for DDL identifiers
- Provider types: use constants from `infrastructure/constants.py` (PROVIDER_POSTGRES, QGIS_PROVIDER_POSTGRES, etc.)
- i18n: non-QObject classes use `QCoreApplication.translate("ClassName", msg)`, QgsTask uses `self.tr()`
- Config access: use `_get_option_value()`/`_set_option_value()` from `config.config` for OPTIONS params (handles wrapped+raw formats)
- Config source of truth: `config.default.json` only — `config_schema.json` is deprecated

## Common Pitfalls
- Use `pointOnSurface()` not `centroid()` for concave polygons (raster sampling)
- `QgsZonalStatistics` writes in-place → use temp memory layer
- CRS: always reproject vector to raster CRS before sampling
- The dockwidget is ~6500 lines - use `_get_current_exploring_layer()` to get current layer
- COG export requires GDAL >= 3.1 - always check version
- Don't recreate the Raster Calculator — stay focused on filtering
- `get_optimal_metric_crs()` takes `(geometry: QgsGeometry, source_crs: QgsCRS)` — NOT extent/project kwargs

## Memory Hygiene
- Always verify Serena memories against actual `main` branch state
- Branch-specific work should be clearly labeled as such

## Indexées automatiquement (à reclasser)

- [Dynamic Widget Fix - Complete Solution (2026-02-05 v2)](dynamic_widget_fix_complete_2026_02_05_v2.md) — The dynamic widget insertion system had multiple conflicts between the OLD pattern (programmatic creation) and NEW patte
