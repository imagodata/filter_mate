# FilterMate architecture

This page is a map of the source tree for a developer who has just cloned the repository. It describes FilterMate 5.0 (QGIS 3.22 to 4.x, Qt5 and Qt6). Paths are relative to the repository root, which is the plugin folder (`filter_mate/`).

Related documents: [AUTOMATION.md](AUTOMATION.md) (Processing, Python API, REST API), [../extensions/README.md](../extensions/README.md) (extension system), [../adapters/backends/README.md](../adapters/backends/README.md) (backends, written for 4.1), [../CONTRIBUTING.md](../CONTRIBUTING.md).

## Layout

The code follows a hexagonal layout: `core/` holds the logic and the ports (abstract interfaces), `adapters/` implements them for QGIS and the data providers, `ui/` is the presentation layer. The layering is not strict. Much of `core/services/`, `core/tasks/` and `core/geometry/` imports `qgis.core`; most of `core/domain/` and `core/ports/` does not.

| Folder | Role |
|---|---|
| `core/` | Domain objects, ports, services, the filter task and its handlers. |
| `adapters/` | Backends (PostgreSQL, Spatialite, OGR, memory), QGIS adapters, repositories, public API. |
| `infrastructure/` | Cross-cutting code: caches, database helpers, logging, DI container, constants, utilities. |
| `ui/` | Controllers, managers, widgets, dialogs, styles and layout of the dock widget. |
| `processing/` | Processing provider, algorithms and shipped models. |
| `filtermate_api/` | FastAPI REST server. |
| `extensions/` | Optional modules discovered at startup (QFieldCloud, favorites sharing). |
| `config/` | Default configuration and configuration helpers. |
| `resources/` | Fonts and QSS style sheets. |
| `i18n/` | Translation sources (`.ts`) and compiled files (`.qm`) for 34 locales. |
| `tests/` | Unit tests, API tests, AST guards, headless QGIS smoke tests. |
| `scripts/` | Release, screenshot, site and QGIS check scripts. Not shipped in the zip. |

Other top-level items: `icons/` (button icons), `website/` (static site published to GitHub Pages by `.github/workflows/deploy-docs.yml`), `metadata.txt` (plugin metadata), `filter_mate_dockwidget_base.ui` (Qt Designer form of the dock).

## Entry point

```
__init__.py            classFactory(iface) -> FilterMate(iface)
filter_mate.py         FilterMate: initGui, menu and toolbar, extensions, Processing provider, unload
filter_mate_app.py     FilterMateApp: layer state, task management, dock lifecycle
filter_mate_dockwidget.py   FilterMateDockWidget: the panel (EXPLORING, FILTERING, EXPORTING, configuration)
```

- `FilterMate.initGui` calls `_init_extensions()` and `initProcessing()`. `metadata.txt` declares `hasProcessingProvider=yes`, so `qgis_process` calls `initProcessing()` alone, with no `iface`.
- `FilterMate.run()` creates `FilterMateApp` and calls `FilterMateApp.run()`, which creates the dock widget (delegated to `AppInitializer` in `core/services/app_initializer.py` when available).
- `FilterMateApp` is a large legacy class being split into services. New logic belongs in `core/services/` or a handler, not in these three files.
- The dock widget owns the widgets. It delegates behaviour to the controllers of `ui/controllers/`, wired by `ControllerIntegration` (`ui/controllers/integration.py`).
- `FilterMateApp.PROJECT_LAYERS` (a dict keyed by layer id) holds the per-layer properties and filter state. The dock shares it.

## Folders

### `core/`

- `domain/`: dataclasses and enums. `filter_expression.py`, `layer_info.py`, `filter_state.py`, `favorites_manager.py`; v5 additions `layer_kind.py` (`LayerKind`), `cross_filter.py` (`CrossFilterRequest`, predicate table), `raster_filter_criteria.py`, `point_cloud_filter_criteria.py`, `api_requests.py` (`OperationReport`).
- `ports/`: abstract interfaces (`backend_port.py`, `cache_port.py`, `filter_executor_port.py`, `repository_port.py`, `public_api_port.py`, `qfieldcloud_port.py`, `point_cloud_port.py`) and the `BackendServices` facade (`backend_services.py`).
- `services/`: application services. `task_orchestrator.py`, `task_run_orchestrator.py`, `filter_application_service.py`, `history_service.py`, `favorites_service.py`, `cross_filter_service.py` (v5), `point_cloud_filter_service.py`, `app_initializer.py`.
- `tasks/`: `filter_task.py` (`FilterEngineTask`, a `QgsTask`) and the handlers it delegates to (`filtering_orchestrator.py`, `finished_handler.py`, `export_handler.py`, `subset_management_handler.py`, ...), with sub-packages `dispatchers/`, `executors/`, `builders/`, `collectors/`, `connectors/`, `cache/`. `layer_management_task.py` and `expression_evaluation_task.py` are separate tasks.
- `filter/`: `filter_orchestrator.py` (per-layer backend choice and fallback), `expression_builder.py`, `expression_combiner.py`, `filter_chain.py`.
- `geometry/`, `optimization/`, `strategies/`, `export/`: buffer and CRS helpers, backend auto-selection and query analysis, multi-step filtering, layer exporters.

### `adapters/`

- `backends/`: `factory.py` (`BackendFactory`, `BackendSelector`), then one package per backend: `postgresql/`, `spatialite/`, `ogr/`, `memory/`. Each has a `backend.py`; PostgreSQL also has `mv_manager.py` (materialized views) and Spatialite `index_manager.py`, `temp_table_manager.py`.
- `backend_registry.py`: `BackendRegistry` returns the executor for a layer's provider type. It is created in `filter_mate_app.py` and injected into `FilterEngineTask`.
- `qgis/`: QGIS adapters (layers, expressions, signals in `signals/`, `tasks/`) and `coverage_layers/` for rasters and point clouds (see below).
- `repositories/`: layer and history storage.
- `public_api/`: `operations.py` and `filter_mate_public_api.py`.
- `task_builder.py` (`TaskParameterBuilder`), `filter_result_handler.py`, `undo_redo_handler.py`, `database_manager.py`, `app_bridge.py` (service locator used by the legacy app).

### `infrastructure/`

`cache/` (query, geometry, WKT, Spatialite caches), `database/` (connection pool, PostgreSQL and Spatialite helpers, `sql_utils.py`), `di/` (`Container`, `providers.py`), `logging/`, `parallel/`, `streaming/`, `state/`, `feedback/` (message bar helpers), `utils/` (layer, thread, validation helpers), `constants.py` (provider names), `perf_timer.py`, `config/config_migration.py`.

### `ui/`

- `controllers/`: `BaseController` and one controller per area: `exploring_controller.py`, `filtering_controller.py`, `exporting_controller.py`, `favorites_controller.py`, `config_controller.py`, `backend_controller.py`, `layer_sync_controller.py`, `coverage_mode_controller.py` (v5). `registry.py` holds `ControllerRegistry` and `TabIndex`.
- `managers/`: widget configuration, combobox population, config model, export dialogs.
- `widgets/`: custom widgets, `json_view/` (configuration tree), `coverage_panels/` (raster and point cloud EXPLORING panels).
- `dialogs/`, `layout/` (spacing and layout managers), `styles/` (themes, icons, QSS loading), `tools/` (raster pixel picker map tool).

### `processing/` and `filtermate_api/`

- `processing/provider.py`: `FilterMateProcessingProvider` (id `filtermate`). `algorithms/` has the algorithm classes, `models/` the four shipped `.model3` files.
- `filtermate_api/`: `server.py` (FastAPI app), `routers/` (`filters.py`, `layers.py`, `export.py`, `favorites.py`), `auth.py` (API key), `main_thread.py` (runs QGIS calls on the Qt main thread), `qgis_accessor.py` (bridge to the running plugin), `run_api.py` and `__main__.py` (standalone start). Dependencies are in `requirements-api.txt`.

### `config/`, `resources/`, `i18n/`

See the sections below.

## Path of a vector filter

1. The user clicks Filter (`pushButton_action_filter`). The button's `clicked` handler calls `launchTaskEvent(state, 'filter')` in `filter_mate_dockwidget.py`. It first offers the task to `ControllerIntegration.delegate_point_cloud_task`, which returns True only when the current layer is a raster or a point cloud (see the next section).
2. For a vector source, `launchTaskEvent` stores the checked target layers in `PROJECT_LAYERS`, splits off raster and point cloud targets (`delegate_split_coverage_targets`) and emits `launchingTask('filter')`.
3. `FilterMateApp.manage_task` receives it (connected in `filter_mate_app.py`). It checks that the dock is ready (it retries every 500 ms, up to 10 times), deals with layers in edit mode, then calls `TaskOrchestrator.dispatch_task` (`core/services/task_orchestrator.py`). If that raises, `_legacy_dispatch_task` is used instead.
4. The orchestrator calls back `FilterMateApp.get_task_parameters`, which validates the current layer and builds the parameter dict with `TaskParameterBuilder` (`adapters/task_builder.py`): a `task` section (layers to filter, expression, `skip_source_filter`), a `filtering` section (buffer, predicates) and `forced_backends`.
5. `FilterMateApp._execute_filter_task` (the orchestrator's filter callback) creates `FilterEngineTask(description, task_name, task_parameters, backend_registry=...)` (`core/tasks/filter_task.py`), connects the completion handlers, freezes the canvas and adds the task to `QgsApplication.taskManager()`.
6. In the worker thread, `FilterEngineTask.run` goes through `TaskRunOrchestrator`, then `ActionDispatcher` (`core/tasks/dispatchers/action_dispatcher.py`) routes the action (`filter`, `unfilter`, `reset`, `export`). For a filter, `FilteringOrchestrator.execute_filtering` (`core/tasks/filtering_orchestrator.py`) filters the source layer, then the target layers, in parallel (`infrastructure/parallel/`) or sequentially.
7. For each target layer, `FilterOrchestrator.orchestrate_geometric_filter` (`core/filter/filter_orchestrator.py`) calls `BackendFactory.get_backend` (`adapters/backends/factory.py`) and builds the expression through the backend's `expression_builder.py`. `postgresql/` writes SQL for PostGIS, `spatialite/` SQL for Spatialite and GeoPackage, `ogr/` serves file formats without a SQL subset, `memory/` memory layers. A forced backend (`forced_backends` in the parameters) is honoured, and a failing backend falls back to another.
8. The worker thread never calls `setSubsetString`. It queues `(layer, expression)` pairs (`FilterEngineTask.queue_subset_request`).
9. `FilterEngineTask.finished` runs on the main thread. `FinishedHandler` (`core/tasks/finished_handler.py`) applies the queued subsets with `apply_pending_subset_requests`, which calls `safe_set_subset_string` (`infrastructure/utils`), then schedules one canvas refresh.
10. `taskCompleted` triggers `FilterMateApp.filter_engine_task_completed`, which calls `FilterResultHandler.handle_task_completion` (`adapters/filter_result_handler.py`): history push, cache clearing, auto-zoom, backend indicator, completion message. Undo and redo are handled by `adapters/undo_redo_handler.py` with `core/services/history_service.py`.

`FilteringController.execute_filter` (`ui/controllers/filtering_controller.py`) validates the configuration but returns False, so the path above is the one that runs. The controller still builds the `FilterConfiguration` and receives the task-started and task-completed callbacks.

## Coverage mode: rasters and point clouds (v5)

When the current layer is a raster or a point cloud, EXPLORING shows a panel of that kind and the dock's buttons run a cross filter instead of the vector task.

- `ui/controllers/coverage_mode_controller.py` (`CoverageModeController`) swaps the EXPLORING groups, owns the panels of `ui/widgets/coverage_panels/` (`raster_exploring_panel.py`, `point_cloud_exploring_panel.py`, `histogram_widget.py`) and implements `handle_task` for `filter`, `unfilter`, `reset`, `undo`, `redo` and `export`. `ui/controllers/coverage_dock_extras.py` adds the layer card and the tool rail buttons of the layer kind; `ui/tools/pixel_picker_tool.py` is the map tool.
- `core/services/cross_filter_service.py` (`CrossFilterService`) handles every source/target pair except vector to vector. It keeps the cross operation history per source layer so Undo, Redo and Unfilter can restore derived sources. The model is in `core/domain/cross_filter.py`; snapshots and history are in `core/domain/filter_state.py`.
- `adapters/qgis/coverage_layers/` does the QGIS work:
  - `source_jobs.py`: turns the EXPLORING selection into a source geometry (`VectorSourceJob`, `RasterSourceJob`, `PointCloudSourceJob`).
  - `target_appliers.py`: applies it to a target (`VectorTargetJob`, `RasterTargetJob`, `PointCloudTargetJob`). A job runs `prepare` on the main thread, `compute` in the task, `apply` on the main thread again.
  - `cross_filter_task.py`: the `QgsTask` that runs the jobs.
  - `raster_adapter.py`, `point_cloud_footprint.py`, `geometry_tools.py`: raster statistics and pixel selection, footprint of selected points, geometry helpers.
  - `gdal_warp.py`, `pdal_cli.py`, `hag_task.py`: `gdal.Warp` wrapper, the `pdal` executable, height above ground.
  - `exporters.py`, `favorites_bridge.py`.
- Derived sources: a raster is clipped to a VRT, a point cloud to a COPC file. The layer keeps its id and style; its data source is swapped (`setDataSource`). `snapshots.py` keeps the registry of swapped layers (`DerivedSourceRegistry`): it writes the original source back into the saved project XML and restores every layer when the plugin unloads.
- Cache: `cache.py` manages the folder of derived files, `<QGIS profile>/filtermate/cache/<session>/` unless `APP.OPTIONS.CROSS_FILTER.cache_dir` is set. `collect_garbage` removes files that no layer or undo step uses. `cache_max_gb` caps the size. A lock file protects a live session from other QGIS instances.
- When the source is a vector layer, raster and point cloud targets are removed from the vector task and clipped by the same source geometry after it is launched (`delegate_vector_source_coverage_task`).

## Public API and automation

`adapters/public_api/operations.py` implements the operations without the dock: `cross_filter`, `cross_filter_by_geometry`, `filter_point_clouds`, `clear_filters`, `export_layers`, `apply_favorite`, `list_favorites`, `filter_state`. They run synchronously on the main thread, one at a time (`busy_reason`), and record their changes in the cross filter history.

Three surfaces share it:

| Surface | Code |
|---|---|
| Processing, `qgis_process`, models | `processing/` |
| Python API | `adapters/public_api/filter_mate_public_api.py`, returned by `FilterMate.get_public_api()` |
| REST API | `filtermate_api/` through `QGISFilterMateAccessor` |

Parameters, routes and examples are in [AUTOMATION.md](AUTOMATION.md). Add a new operation in `operations.py` first, then expose it on each surface.

## Extensions

`extensions/` holds optional modules. `ExtensionRegistry` (`extensions/registry.py`) discovers every sub-package that exposes an `Extension` class deriving from `BaseExtension` (`extensions/base.py`), then runs `check_dependencies`, `initialize(iface)`, `create_ui` and, on unload, `teardown`. `FilterMate._init_extensions` drives this from `initGui`. An extension whose dependencies are missing disables itself and FilterMate runs unchanged.

- `extensions/qfieldcloud/`: export of filtered layers to QFieldCloud (needs `qfieldcloud-sdk`).
- `extensions/favorites_sharing/`: share favorites through git repositories; has its own [README](../extensions/favorites_sharing/README.md).

An extension declares its configuration keys in `config_schema()`; they appear under `EXTENSIONS.<id>` in `config.json`. The full tree and the extension guide are in [../extensions/README.md](../extensions/README.md).

## Configuration

- `config/config.default.json`: the reference. Each setting is `{"value": ..., "description": ..., "choices"/"min"/"max": ...}`; keys starting with `_` (`_display_name`, `_hidden`) drive the Configuration tab. Top-level sections: `APP`, `CURRENT_PROJECT`, `EXTENSIONS`.
- At start, `config/config.py` (`init_env_vars`) loads `config.json` from the `FilterMate` folder of the QGIS profile, creating it from the default when missing. It merges new keys, refreshes the metadata of existing keys and keeps user values (`_migrate_config`). `ENV_VARS` holds paths and the loaded data.
- Other modules: `feedback_config.py` (message verbosity), `theme_helpers.py`, `config_metadata.py`. See [../config/README_CONFIG.md](../config/README_CONFIG.md).
- The Configuration tab is a JSON tree (`ui/widgets/json_view/`) managed by `ui/managers/config_model_manager.py`.
- Plugin metadata is in `metadata.txt` (version, QGIS 3.22 to 4.99: QGIS 4 compatibility comes from `qgisMaximumVersion`).

## Internationalization

User strings go through `tr()` or `QCoreApplication.translate`. `i18n/FilterMate.pro` lists the source files and the 34 `FilterMate_<locale>.ts` files; the compiled `.qm` files are tracked in git and shipped. `FilterMate` loads `i18n/FilterMate_<locale>.qm` with a `QTranslator` and can reload it when the language is changed in the Configuration tab. The zip script leaves out `.ts` and `.pro` files.

## Tests and CI

- `tests/unit/` mirrors the plugin layout (`core`, `adapters`, `infrastructure`, `ui`, `processing`, `extensions`). `tests/api/` tests the REST API. `tests/conftest.py` mocks `qgis.*` so these run without QGIS.
- AST guards at the top of `tests/`: `test_no_unscoped_qt_enums.py`, `test_no_qtwidgets_relocated_symbols.py`, `test_no_unguarded_sip_import.py`, `test_no_bare_disconnect_on_qgis_signals.py`, `test_no_clear_on_map_layer_combobox.py`, `test_no_layout_insert_item_temporaries.py`, plus `test_package_import_exports.py` and `test_backend_services_facade_calls.py`. Each walks the plugin source and fails on a pattern that broke in a real QGIS.
- `tests/qgis_headless/`: scripts run inside QGIS Docker images (fixtures, engine smoke test, dock smoke test under Xvfb). They are not pytest modules.
- `.github/workflows/test.yml`: flake8, then pytest on Python 3.10 and 3.12.
- `.github/workflows/qgis-headless.yml`: the headless scripts on `qgis/qgis` images from QGIS 3.22 to nightly.
- `.github/workflows/release.yml`: on a `v*.*.*` tag, runs the tests, checks the tag against `metadata.txt`, builds the zip with `scripts/prepare_plugin_zip.sh`, creates the GitHub release and publishes to plugins.qgis.org.
- `.github/workflows/deploy-docs.yml`: publishes `website/` to GitHub Pages.
