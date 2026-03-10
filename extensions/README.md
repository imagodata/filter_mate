# FilterMate Extension System

## Overview

FilterMate v5.0 introduces an **extension system** — a plugin-within-a-plugin architecture that allows optional modules to extend FilterMate without modifying its core codebase.

Extensions are **auto-discovered**, **optional**, and **zero-regression**: if an extension's dependencies are missing, FilterMate works exactly as before.

The first extension is **QFieldCloud**, which adds one-click export of filtered layers to QFieldCloud.

---

## Architecture

### FilterMate Plugin Architecture (Hexagonal)

```
filter_mate/
│
├── core/                          # Domain Layer (Pure Python)
│   ├── domain/                    #   Entities (FilterExpression, LayerInfo, FilterResult)
│   ├── ports/                     #   Abstract interfaces (BackendPort, CachePort, QFieldCloudPort)
│   ├── services/                  #   Business logic (FilterService, ExportService, HistoryService)
│   ├── tasks/                     #   Async tasks (FilterEngineTask, handlers/)
│   ├── filter/                    #   Expression building, PredicateRegistry
│   ├── geometry/                  #   Buffer, CRS, spatial operations
│   ├── optimization/              #   Query optimization, performance advisor
│   ├── strategies/                #   Multi-step, progressive filtering
│   └── export/                    #   LayerExporter, BatchExporter, StyleExporter
│
├── adapters/                      # Adapters Layer (QGIS-specific)
│   ├── backends/                  #   4 backends: PostgreSQL, SpatiaLite, OGR, Memory
│   │   ├── postgresql/            #     MV, dynamic buffers, PK detection
│   │   ├── spatialite/            #     R-tree, temporary tables
│   │   ├── ogr/                   #     File-based (Shapefile, GeoJSON)
│   │   ├── memory/                #     In-memory filtering
│   │   └── factory.py             #     BackendFactory with auto-selection
│   ├── qgis/                      #   QGIS adapters (signals, tasks, layer adaptation)
│   ├── repositories/              #   Data access (QGISLayerRepository, HistoryRepository)
│   └── app_bridge.py              #   DI container & service locator
│
├── extensions/                    # Extension System (NEW v5.0)
│   ├── __init__.py                #   Public API (get_extension_registry)
│   ├── base.py                    #   BaseExtension ABC + ExtensionMetadata
│   ├── registry.py                #   ExtensionRegistry (discover, init, teardown)
│   └── qfieldcloud/               #   First extension module
│       ├── extension.py           #     QFieldCloudExtension entry point
│       ├── sdk_adapter.py         #     qfieldcloud-sdk wrapper (retry, backoff)
│       ├── credentials_manager.py #     Multi-level credential storage
│       ├── project_builder.py     #     .qgs generation with QFieldSync modes
│       ├── service.py             #     Push orchestration service
│       ├── signals.py             #     Qt signals for events
│       ├── exceptions.py          #     Exception hierarchy
│       └── ui/                    #     Settings + Push dialogs
│
├── ui/                            # Presentation Layer
│   ├── controllers/               #   13 MVC controllers (BaseController pattern)
│   ├── widgets/                   #   Custom widgets, signal management
│   ├── dialogs/                   #   Configuration dialogs
│   ├── managers/                  #   UI managers (export, config, combobox)
│   ├── tools/                     #   Map tools (raster pixel picker)
│   └── styles/                    #   Theme management (IconManager, ThemeWatcher)
│
├── infrastructure/                # Cross-cutting Concerns
│   ├── cache/                     #   LRU cache, result caching
│   ├── database/                  #   Connection pool, SQL utilities
│   ├── di/                        #   Dependency injection container
│   ├── utils/                     #   Layer utils, validation, field helpers
│   └── logging/                   #   Centralized logging
│
├── config/                        # Configuration
│   ├── config.json                #   User settings (JSON v2.0)
│   ├── config.default.json        #   Fallback defaults
│   └── config_metadata.py         #   Schema + validation
│
├── filter_mate.py                 # Plugin entry point (classFactory, initGui, unload)
├── filter_mate_app.py             # Application orchestrator
└── filter_mate_dockwidget.py      # Main UI dockwidget
```

### How it fits together

```
QGIS Interface (iface)
       │
       ▼
filter_mate.py          ← Entry point: classFactory(), initGui(), unload()
       │
       ├── Toolbar + Menu actions
       ├── Extension discovery & initialization    ← NEW v5.0
       │
       ▼
filter_mate_app.py      ← App orchestrator: services, tasks, dockwidget lifecycle
       │
       ▼
filter_mate_dockwidget.py ← Main UI: tabs (Exploring, Filtering, Exporting)
       │
       ├── Controllers (MVC)  ──→  Services (core/)  ──→  Ports (interfaces)
       │                                                        │
       │                                                        ▼
       │                                                   Adapters (backends/, qgis/)
       │
       └── Extensions (optional)  ──→  Extension services  ──→  External APIs
                                       (QFieldCloud SDK)
```

### Key Architectural Principles

| Principle | Implementation |
|-----------|---------------|
| **Hexagonal Architecture** | `core/ports/` = interfaces, `adapters/` = implementations |
| **Pure Domain** | `core/` has zero QGIS imports (testable without QGIS) |
| **Dependency Injection** | `adapters/app_bridge.py` = service locator + singletons |
| **MVC Controllers** | `ui/controllers/` with `BaseController`, `ControllerRegistry` |
| **Optional Extensions** | `extensions/` with auto-discovery, lazy loading |
| **Signal-driven** | Qt signals for decoupled event communication |

---

## Extension System

### Lifecycle

```
discover_extensions()     Scan extensions/ for subpackages with Extension class
        │
        ▼
check_dependencies()      Verify required packages (e.g., qfieldcloud-sdk)
        │
        ▼
initialize(iface)         Create services, adapters, register with DI
        │
        ▼
create_ui(toolbar, menu)  Add toolbar buttons, menu entries
        │
        ▼
  [Plugin running...]     Extension active, services available
        │
        ▼
teardown()                Cleanup on plugin unload (reverse order)
```

### Creating a New Extension

1. Create a directory under `extensions/`:

```
extensions/
└── my_extension/
    ├── __init__.py      # Must expose Extension class
    ├── extension.py     # Implements BaseExtension
    └── ...              # Your modules
```

2. Implement `BaseExtension`:

```python
# extensions/my_extension/__init__.py
from .extension import MyExtension
Extension = MyExtension  # Required: registry looks for this name

# extensions/my_extension/extension.py
from ..base import BaseExtension, ExtensionMetadata

class MyExtension(BaseExtension):

    @property
    def metadata(self) -> ExtensionMetadata:
        return ExtensionMetadata(
            id="my_extension",
            name="My Extension",
            version="1.0.0",
            description="What it does",
            dependencies=["some_package"],  # pip packages required
        )

    def check_dependencies(self) -> bool:
        try:
            import some_package
            return True
        except ImportError:
            return False

    def initialize(self, iface) -> None:
        # Create your services, register them
        self.register_service('my_service', MyService())

    def create_ui(self, toolbar, menu_name) -> list:
        from qgis.PyQt.QtGui import QAction
        action = QAction("My Action", iface.mainWindow())
        action.triggered.connect(self._on_triggered)
        toolbar.addAction(action)
        return [action]

    def teardown(self) -> None:
        self._services.clear()
```

3. That's it. FilterMate auto-discovers your extension on next startup.

### Extension API

```python
from filter_mate.extensions import get_extension_registry

registry = get_extension_registry()

# Get a specific extension
qfc = registry.get_extension('qfieldcloud')
if qfc and qfc.is_available():
    service = qfc.get_service('push')
    result = service.push_project(...)

# List all available extensions
for ext in registry.get_available_extensions():
    print(f"{ext.metadata.name} v{ext.metadata.version}")

# Status summary
summary = registry.get_status_summary()
# {'qfieldcloud': {'name': 'QFieldCloud', 'state': 'ui_created', 'available': True}}
```

---

## QFieldCloud Extension

### What it does

Adds a **one-click export** of FilterMate's filtered layers to QFieldCloud:

```
FilterMate filters zone POP_001  →  [1 click]  →  QFieldCloud project ready for QField
```

**Before** (5 steps, 3 tools, 15-20 min):
FilterMate → Export GPKG → Script .qgs → QFieldSync → Push

**After** (2 steps, 1 tool, 30 sec):
FilterMate → Click "Export QFieldCloud"

### Requirements

```bash
pip install qfieldcloud-sdk     # Required
pip install keyring              # Optional (secure credential storage)
```

If `qfieldcloud-sdk` is not installed, the extension silently disables itself. No error, no warning, no impact on FilterMate.

### Module Structure

```
extensions/qfieldcloud/
├── extension.py            Main entry point (QFieldCloudExtension)
│                           - Lazy service initialization
│                           - UI action handlers
│                           - Lifecycle management
│
├── sdk_adapter.py          SDK wrapper (QFieldCloudAdapter)
│                           - login / login_with_token
│                           - list_projects / create_project
│                           - upload_project_files (3x retry, exponential backoff)
│                           - trigger_package / poll_job_status
│                           - add_collaborator
│
├── credentials_manager.py  Multi-level credential storage (CredentialsManager)
│                           - Level 1: QgsSettings (URL, username, preferences)
│                           - Level 2: keyring (token, password — encrypted by OS)
│                           - Level 3: Environment variables (CI/CD fallback)
│
├── project_builder.py      .qgs project generation (QFieldProjectBuilder)
│                           - Reads layers from exported GeoPackage
│                           - Applies QFieldSync custom properties
│                           - Sets layer action modes (OFFLINE, COPY, NO_ACTION)
│                           - Embeds QML styles
│
├── service.py              Push orchestration (QFieldCloudService)
│                           - push_project(): GPKG → .qgs → upload → package
│                           - batch_push_zones(): N zones sequentially
│                           - Progress callbacks + signal emission
│
├── signals.py              Qt signals (QFieldCloudSignals)
│                           - project_pushed(project_id, name, url)
│                           - batch_completed(total, succeeded, failed)
│                           - push_failed(name, error)
│                           - progress_updated(percent, message)
│                           - authenticated(username)
│
├── exceptions.py           Exception hierarchy
│                           - QFieldCloudError (base)
│                           - QFieldCloudAuthError
│                           - QFieldCloudUploadError
│                           - QFieldCloudProjectError
│                           - QFieldCloudTimeoutError
│
└── ui/
    ├── settings_dialog.py  Configuration dialog
    │                       - Server URL, username, password/token
    │                       - Login + test connection buttons
    │                       - Preferences (auto-package, default project)
    │
    └── push_dialog.py      Export dialog
                            - Active filter summary
                            - Project naming (create new / update existing)
                            - Layer action mode overrides (table)
                            - Progress bar with async push (QThread)
```

### Push Pipeline

```
1. User clicks "Export QFieldCloud"
2. Dialog shows: active filter, layers, project naming
3. User clicks "Export":
   a. Export GPKG (FilterMate's existing export, respects subsetString)
   b. Generate .qgs with QFieldSync properties
   c. Upload all files to QFieldCloud (3x retry)
   d. Trigger packaging job on server
4. Success notification with project URL
```

### Layer Action Modes (WYRE FTTH defaults)

| Layer | Mode | Meaning |
|-------|------|---------|
| structures | OFFLINE | Downloaded, editable on device |
| demand_points | OFFLINE | Downloaded, editable on device |
| zone_drop | OFFLINE | Downloaded, editable on device |
| zone_distribution | OFFLINE | Downloaded, editable on device |
| sheaths | COPY | Downloaded, read-only |
| ducts | COPY | Downloaded, read-only |
| subducts | COPY | Downloaded, read-only |
| zone_pop | COPY | Downloaded, read-only |
| zone_mro | NO_ACTION | Not included in package |

### Connecting to Signals

```python
from filter_mate.extensions import get_extension_registry

registry = get_extension_registry()
qfc = registry.get_extension('qfieldcloud')

if qfc:
    signals = qfc.get_service('signals')
    signals.project_pushed.connect(lambda pid, name, url:
        print(f"Pushed {name}: {url}")
    )
```

### Credential Storage

```
┌─────────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  keyring (OS)       │     │  QgsSettings     │     │  Environment   │
│  - JWT token        │     │  - Server URL    │     │  - QFIELDCLOUD │
│  - Password         │     │  - Username      │     │    _TOKEN      │
│  (encrypted by OS)  │     │  - Preferences   │     │  (CI/CD only)  │
└─────────────────────┘     └──────────────────┘     └────────────────┘
        ▲ preferred              ▲ always                ▲ fallback
```

---

## Tests

48 unit tests covering the extension framework and QFieldCloud modules:

```bash
# Run all extension tests
python -m pytest tests/unit/extensions/ -v -o "addopts="

# Run specific test files
python -m pytest tests/unit/extensions/test_extension_registry.py    # 18 tests
python -m pytest tests/unit/extensions/test_qfieldcloud_adapter.py   # 18 tests
python -m pytest tests/unit/extensions/test_qfieldcloud_service.py   # 8 tests
python -m pytest tests/unit/extensions/test_credentials_manager.py   # 4 tests
```

All tests mock QGIS and SDK dependencies — no QGIS installation required.

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Extension registry + BaseExtension | 18 | Lifecycle, discovery, teardown order, notifications |
| SDK adapter | 18 | Auth, projects, upload retry, job polling, URLs |
| Push service | 8 | Create/update project, signals, progress, batch |
| Credentials manager | 4 | Store/retrieve, keyring fallback, env vars |

---

## Roadmap

### MVP (v5.0) - Current
- [x] Extension framework (base, registry, lifecycle)
- [x] QFieldCloud: credentials, SDK adapter, project builder
- [x] QFieldCloud: push service, settings dialog, push dialog
- [x] 48 unit tests

### V2 (v5.1) - Planned
- [ ] Project list combo (CRUD on existing projects)
- [ ] Batch multi-zone push
- [ ] Project templates (JSON config)
- [ ] Collaborator management

### V3 (v5.2) - Planned
- [ ] Packaging job monitoring (real-time status)
- [ ] QGIS notifications on sync events
- [ ] Dashboard widget (project list, status, activity)
- [ ] ESB WYRE integration (trigger after sync)
