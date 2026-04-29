# -*- coding: utf-8 -*-
"""
Conftest for core/tasks handler tests.

Pre-mocks the deep import chains so individual handler modules can be
imported without pulling in the entire QGIS/plugin dependency tree.

The handlers use relative imports like:
    from ...infrastructure.logging import setup_logger

From core/tasks/handler.py, '...' resolves 3 levels up:
    core.tasks.handler -> core.tasks -> core -> (root = filter_mate)

So '...infrastructure' resolves to 'filter_mate.infrastructure'.
Since pytest runs from the filter_mate directory as CWD, we need
a parent 'filter_mate' package that contains 'core', 'infrastructure',
'config', 'adapters', etc.

Strategy:
    1. Create a 'filter_mate' package in sys.modules as parent of 'core'
    2. Mock all submodules under filter_mate (infrastructure, config, etc.)
    3. Load handler modules with proper package hierarchy
"""
import sys
import types
import os
from unittest.mock import MagicMock

import pytest


# Snapshot of `sys.modules` keys this conftest mutates, so we can restore the
# original state after the directory's tests finish. Without this, the
# ``core``/``core.tasks`` aliases the conftest installs leak into sibling
# directories' tests and break their imports — that was the root cause of
# issue #42 (test-order pollution).
_MUTATED_KEYS = (
    'core',
    'core.tasks',
    'core.tasks.cleanup_handler',
    'core.tasks.export_handler',
    'core.tasks.geometry_handler',
    'core.tasks.initialization_handler',
    'core.tasks.source_geometry_preparer',
    'core.tasks.subset_management_handler',
    'core.tasks.expression_evaluation_task',
    'core.tasks.v3_bridge_handler',
)
_PRE_SETUP_SNAPSHOT: dict = {}

# Strong references to the canonical handler modules loaded by
# ``_setup_handler_mocks``. Sibling test directories can re-trigger Python's
# import machinery and replace ``filter_mate.core.tasks.X`` with a fresh
# instance built against THEIR mock chain. That fresh instance binds the
# wrong ``PROVIDER_POSTGRES`` etc. and breaks the handler tests when they
# next run. Keeping a strong reference here lets ``_reassert_handler_aliases``
# repin both the namespaced AND short-name slots to the original correctly-
# mocked instance — see issue #42.
_CANONICAL_HANDLER_MODULES: dict = {}


def _create_package(name, parent=None):
    """Create a real module/package object and register in sys.modules."""
    mod = types.ModuleType(name)
    mod.__path__ = []
    mod.__package__ = name
    sys.modules[name] = mod
    if parent and hasattr(sys.modules.get(parent), '__dict__'):
        short_name = name.rsplit('.', 1)[-1]
        setattr(sys.modules[parent], short_name, mod)
    return mod


def _setup_handler_mocks():
    """Install all mocks needed for handler imports."""
    if getattr(_setup_handler_mocks, '_done', False):
        return
    _setup_handler_mocks._done = True

    # Snapshot pre-existing entries for the keys we're about to mutate so a
    # session-end fixture can restore them. Captures None for keys not yet
    # in sys.modules (i.e. "delete on teardown").
    for key in _MUTATED_KEYS:
        _PRE_SETUP_SNAPSHOT[key] = sys.modules.get(key)

    # Logger and ENV mocks
    mock_logger = MagicMock()
    mock_setup_logger = MagicMock(return_value=mock_logger)
    mock_env_vars = {"PATH_ABSOLUTE_PROJECT": "/tmp/filtermate_test"}  # nosec B108

    # Constants mock with real values
    mock_constants = MagicMock()
    mock_constants.PROVIDER_POSTGRES = 'postgresql'
    mock_constants.PROVIDER_SPATIALITE = 'spatialite'
    mock_constants.PROVIDER_OGR = 'ogr'
    mock_constants.PROVIDER_MEMORY = 'memory'
    mock_constants.PROVIDER_VIRTUAL = 'virtual'

    # Backend services mock
    mock_bs_instance = MagicMock()
    # v3_bridge_handler unpacks: get_task_bridge, BridgeStatus = _bs.get_task_bridge()
    mock_bs_instance.get_task_bridge = MagicMock(
        return_value=(MagicMock(), MagicMock())
    )
    mock_get_bs = MagicMock(return_value=mock_bs_instance)

    # HistoryRepository as a real class (not instance)
    MockHistoryRepo = type('HistoryRepository', (), {
        '__init__': lambda self, conn, cur: None,
        'insert': MagicMock(return_value=True),
        'delete_for_layer': MagicMock(return_value=True),
        'delete_entry': MagicMock(return_value=True),
        'get_last_entry': MagicMock(return_value=None),
        'close': lambda self: None,
    })

    # ---------------------------------------------------------------
    # Create the filter_mate package hierarchy
    # ---------------------------------------------------------------
    # We need: filter_mate -> core -> tasks -> handler.py
    # And:     filter_mate -> infrastructure, config, adapters, etc.

    ROOT = 'filter_mate'

    # Create filter_mate root package
    _create_package(ROOT)

    # Create core hierarchy under filter_mate
    _create_package(f'{ROOT}.core')
    _create_package(f'{ROOT}.core.tasks', f'{ROOT}.core')

    # Also ensure 'core' at top level points to filter_mate.core
    if 'core' not in sys.modules or isinstance(sys.modules['core'], MagicMock):
        sys.modules['core'] = sys.modules[f'{ROOT}.core']
    if 'core.tasks' not in sys.modules or isinstance(sys.modules['core.tasks'], MagicMock):
        sys.modules['core.tasks'] = sys.modules[f'{ROOT}.core.tasks']
        sys.modules['core'].tasks = sys.modules['core.tasks']

    # ---------------------------------------------------------------
    # Mock all modules under filter_mate.* that handlers import
    # via relative imports (from ...X import Y)
    # ---------------------------------------------------------------
    fm_modules = {
        # infrastructure
        f'{ROOT}.infrastructure': MagicMock(),
        f'{ROOT}.infrastructure.logging': MagicMock(setup_logger=mock_setup_logger),
        f'{ROOT}.infrastructure.constants': mock_constants,
        f'{ROOT}.infrastructure.utils': MagicMock(
            detect_layer_provider_type=MagicMock(return_value='ogr'),
            get_spatialite_datasource_from_layer=MagicMock(return_value=(None, None)),
        ),
        f'{ROOT}.infrastructure.streaming': MagicMock(),
        f'{ROOT}.infrastructure.database': MagicMock(),
        f'{ROOT}.infrastructure.database.prepared_statements': MagicMock(
            create_prepared_statements=MagicMock(return_value=None),
        ),

        # config
        f'{ROOT}.config': MagicMock(),
        f'{ROOT}.config.config': MagicMock(ENV_VARS=mock_env_vars),

        # core sub-packages
        f'{ROOT}.core.ports': MagicMock(),
        f'{ROOT}.core.ports.backend_services': MagicMock(
            get_backend_services=mock_get_bs,
            BackendServices=MagicMock(),
        ),
        f'{ROOT}.core.export': MagicMock(),
        f'{ROOT}.core.export.style_exporter': MagicMock(),
        f'{ROOT}.core.services': MagicMock(),
        f'{ROOT}.core.services.buffer_service': MagicMock(),
        f'{ROOT}.core.services.filter_config_builder': MagicMock(),
        f'{ROOT}.core.services.source_subset_buffer_builder': MagicMock(),
        f'{ROOT}.core.services.geometry_preparer': MagicMock(),
        f'{ROOT}.core.geometry': MagicMock(),
        f'{ROOT}.core.geometry.crs_utils': MagicMock(
            is_geographic_crs=MagicMock(return_value=False),
            is_metric_crs=MagicMock(return_value=True),
            get_optimal_metric_crs=MagicMock(return_value='EPSG:2154'),
            get_layer_crs_info=MagicMock(return_value={}),
        ),
        f'{ROOT}.core.geometry.spatial_index': MagicMock(),
        f'{ROOT}.core.geometry.buffer_processor': MagicMock(),
        f'{ROOT}.core.optimization': MagicMock(),
        f'{ROOT}.core.optimization.config_provider': MagicMock(),
        f'{ROOT}.core.backends': MagicMock(),
        f'{ROOT}.core.backends.auto_optimizer': MagicMock(),

        # adapters
        f'{ROOT}.adapters': MagicMock(),
        f'{ROOT}.adapters.repositories': MagicMock(),
        f'{ROOT}.adapters.repositories.history_repository': MagicMock(
            HistoryRepository=MockHistoryRepo,
        ),
        f'{ROOT}.adapters.backends': MagicMock(),
        f'{ROOT}.adapters.backends.postgresql': MagicMock(),
        f'{ROOT}.adapters.backends.postgresql.mv_reference_tracker': MagicMock(),
        f'{ROOT}.adapters.backends.spatialite': MagicMock(),
        f'{ROOT}.adapters.backends.ogr': MagicMock(),

        # tasks sub-modules
        f'{ROOT}.core.tasks.builders': MagicMock(),
        f'{ROOT}.core.tasks.builders.subset_string_builder': MagicMock(),
    }

    for mod_name, mock_obj in fm_modules.items():
        if mod_name not in sys.modules:
            sys.modules[mod_name] = mock_obj

    # ---------------------------------------------------------------
    # Load handler modules using importlib with proper __package__
    # ---------------------------------------------------------------
    import importlib.util

    handler_dir = os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..', '..', 'core', 'tasks'
    )
    handler_dir = os.path.normpath(handler_dir)

    handler_files = [
        'cleanup_handler',
        'export_handler',
        'geometry_handler',
        'initialization_handler',
        'source_geometry_preparer',
        'subset_management_handler',
        'expression_evaluation_task',
        'v3_bridge_handler',
    ]

    for handler_name in handler_files:
        fm_module_name = f'{ROOT}.core.tasks.{handler_name}'
        short_module_name = f'core.tasks.{handler_name}'

        if fm_module_name in sys.modules and not isinstance(sys.modules[fm_module_name], MagicMock):
            # Already loaded as a real module
            sys.modules[short_module_name] = sys.modules[fm_module_name]
            continue

        file_path = os.path.join(handler_dir, f'{handler_name}.py')
        if not os.path.exists(file_path):
            continue

        spec = importlib.util.spec_from_file_location(
            fm_module_name,
            file_path,
            submodule_search_locations=[],
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            module.__package__ = f'{ROOT}.core.tasks'
            sys.modules[fm_module_name] = module
            sys.modules[short_module_name] = module  # alias
            try:
                spec.loader.exec_module(module)
                # Also set as attribute on the tasks package
                setattr(sys.modules[f'{ROOT}.core.tasks'], handler_name, module)
                setattr(sys.modules['core.tasks'], handler_name, module)
                # Keep a strong reference for #42 alias-restoration.
                _CANONICAL_HANDLER_MODULES[handler_name] = module
            except Exception as e:
                sys.modules[fm_module_name] = MagicMock()
                sys.modules[short_module_name] = MagicMock()
                import warnings
                warnings.warn(
                    f"Could not load handler {handler_name}: {e}",
                    stacklevel=2,
                )


# Run at import time so that test files in this directory can use
# ``from core.tasks.X import Y`` inside setup methods. The setup is guarded
# by `_setup_handler_mocks._done` so repeat invocations are no-ops.
_setup_handler_mocks()


def _reassert_handler_aliases():
    """Re-pin the ``core.tasks.<handler>`` aliases to the conftest's loaded
    module instances.

    #42 root-cause: between handler tests, sibling tests (e.g. those in
    ``tests/unit/ui/controllers/`` or ``tests/unit/extensions/``) install
    their own ``filter_mate`` package with a real ``__path__``. Subsequent
    ``import core.tasks.subset_management_handler`` re-loads the module
    file from disk via the standard machinery, replacing the alias. The
    new module instance pulls ``PROVIDER_POSTGRES`` etc. from whatever
    ``infrastructure.constants`` mock happens to be installed at that
    moment — typically a bare MagicMock without our string values.

    Re-pinning before each handler test guarantees the alias points to
    the conftest's original (correctly-mocked) instance.
    """
    ROOT = 'filter_mate'
    for short_name, canonical in _CANONICAL_HANDLER_MODULES.items():
        # Force both the namespaced and short-name slots back to the canonical
        # instance, even if a sibling test re-imported the file from disk and
        # replaced the namespaced slot.
        sys.modules[f'{ROOT}.core.tasks.{short_name}'] = canonical
        sys.modules[f'core.tasks.{short_name}'] = canonical

    # Re-pin the provider constants on each handler module. When the conftest
    # runs AFTER a sibling test has already populated
    # ``filter_mate.infrastructure.constants`` with a bare MagicMock, our
    # ``setdefault``-based install is a no-op and the handler captures
    # ``PROVIDER_POSTGRES`` as a MagicMock instance. Re-binding the attribute
    # directly on the loaded module restores the test contract.
    _PROVIDER_VALUES = {
        'PROVIDER_POSTGRES': 'postgresql',
        'PROVIDER_SPATIALITE': 'spatialite',
        'PROVIDER_OGR': 'ogr',
        'PROVIDER_MEMORY': 'memory',
        'PROVIDER_VIRTUAL': 'virtual',
    }
    for canonical in _CANONICAL_HANDLER_MODULES.values():
        for attr_name, attr_value in _PROVIDER_VALUES.items():
            if hasattr(canonical, attr_name):
                # Only overwrite if the existing binding is non-string (the
                # MagicMock case). A real string already in place is correct.
                current = getattr(canonical, attr_name)
                if not isinstance(current, str):
                    setattr(canonical, attr_name, attr_value)


@pytest.fixture(autouse=True)
def _refresh_handler_aliases():
    """Run before each test in this directory to defend against alias
    corruption by sibling test directories (#42)."""
    _reassert_handler_aliases()
    yield


@pytest.fixture(scope='session', autouse=True)
def _restore_core_aliases_after_tasks_tests():
    """Restore the snapshot of ``sys.modules`` keys this conftest mutated.

    Runs once at session end. Removes the leak documented in
    ``_setup_handler_mocks()``.
    """
    yield
    if not _PRE_SETUP_SNAPSHOT:
        return
    for key, original in _PRE_SETUP_SNAPSHOT.items():
        if original is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original
