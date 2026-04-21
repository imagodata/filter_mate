# -*- coding: utf-8 -*-
"""Conftest for ``tests/unit/core/export``.

Installs a minimal ``core.export.*`` and ``core.tasks.export_handler`` import
graph so the regression tests can exercise the real implementations without
pulling the full QGIS plugin dependency tree.
"""
import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock


def _ensure_package(name, parent=None):
    if name in sys.modules and isinstance(sys.modules[name], types.ModuleType) \
            and not isinstance(sys.modules[name], MagicMock):
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = []
    mod.__package__ = name
    sys.modules[name] = mod
    if parent:
        short = name.rsplit('.', 1)[-1]
        setattr(sys.modules[parent], short, mod)
    return mod


def _load_file_as(module_name: str, file_path: str, package: str):
    if module_name in sys.modules and not isinstance(sys.modules[module_name], MagicMock):
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(
        module_name, file_path, submodule_search_locations=[],
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _setup():
    if getattr(_setup, '_done', False):
        return
    _setup._done = True

    ROOT = 'filter_mate'
    project_root = os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
    )

    # Package hierarchy
    _ensure_package(ROOT)
    _ensure_package(f'{ROOT}.core', parent=ROOT)
    _ensure_package(f'{ROOT}.core.export', parent=f'{ROOT}.core')
    _ensure_package(f'{ROOT}.core.tasks', parent=f'{ROOT}.core')

    # Top-level aliases (so `from core.export.X` and `from core.tasks.X` work)
    if not isinstance(sys.modules.get('core'), types.ModuleType) or \
            isinstance(sys.modules.get('core'), MagicMock):
        sys.modules['core'] = sys.modules[f'{ROOT}.core']
    sys.modules['core.export'] = sys.modules[f'{ROOT}.core.export']
    sys.modules['core.tasks'] = sys.modules[f'{ROOT}.core.tasks']

    # Mock leaf modules the handler imports indirectly
    infra = _ensure_package(f'{ROOT}.infrastructure', parent=ROOT)
    _ensure_package(f'{ROOT}.infrastructure.streaming', parent=f'{ROOT}.infrastructure')
    sys.modules[f'{ROOT}.infrastructure.logging'] = MagicMock(setup_logger=MagicMock(return_value=MagicMock()))
    sys.modules[f'{ROOT}.infrastructure.streaming'] = MagicMock(
        StreamingExporter=MagicMock,
        StreamingConfig=MagicMock,
    )
    _ensure_package(f'{ROOT}.config', parent=ROOT)
    sys.modules[f'{ROOT}.config.config'] = MagicMock(
        ENV_VARS={"PATH_ABSOLUTE_PROJECT": "/tmp/filtermate_test"},  # nosec B108
    )

    # Load real modules
    export_dir = os.path.join(project_root, 'core', 'export')
    for name in ('layer_exporter', 'batch_exporter', 'style_exporter',
                 'export_validator'):
        _load_file_as(
            f'{ROOT}.core.export.{name}',
            os.path.join(export_dir, f'{name}.py'),
            f'{ROOT}.core.export',
        )
        sys.modules[f'core.export.{name}'] = sys.modules[f'{ROOT}.core.export.{name}']
        setattr(sys.modules[f'{ROOT}.core.export'], name,
                sys.modules[f'{ROOT}.core.export.{name}'])

    # core.export package attributes the handler imports via ``from ..export import X``
    le = sys.modules[f'{ROOT}.core.export.layer_exporter']
    be = sys.modules[f'{ROOT}.core.export.batch_exporter']
    ev = sys.modules[f'{ROOT}.core.export.export_validator']
    se = sys.modules[f'{ROOT}.core.export.style_exporter']
    pkg = sys.modules[f'{ROOT}.core.export']
    pkg.LayerExporter = le.LayerExporter
    pkg.ExportConfig = le.ExportConfig
    pkg.BatchExporter = be.BatchExporter
    pkg.sanitize_filename = be.sanitize_filename
    pkg.validate_export_parameters = ev.validate_export_parameters
    pkg.save_layer_style = se.save_layer_style
    # Mirror to short alias
    sys.modules['core.export'].__dict__.update(pkg.__dict__)

    # Load the real export_handler
    handler_path = os.path.join(project_root, 'core', 'tasks', 'export_handler.py')
    _load_file_as(
        f'{ROOT}.core.tasks.export_handler', handler_path, f'{ROOT}.core.tasks',
    )
    sys.modules['core.tasks.export_handler'] = sys.modules[f'{ROOT}.core.tasks.export_handler']


_setup()
