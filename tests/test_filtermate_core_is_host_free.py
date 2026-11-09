# -*- coding: utf-8 -*-
"""``filtermate_core`` must not depend on QGIS, Qt, GDAL or the plugin's other packages.

Two checks:

* static: no module under ``filtermate_core/`` imports a host package, even
  lazily or inside ``try``, and no relative import leaves the package;
* runtime: every module imports in a fresh interpreter where the host packages
  are blocked and only the repository root is on ``sys.path`` (the standalone
  spelling ``import filtermate_core``).
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CORE = _ROOT / 'filtermate_core'

# Top-level names the core may never import.
HOST_PACKAGES = ('qgis', 'PyQt5', 'PyQt6', 'PyQt', 'osgeo', 'processing', 'sip')
PLUGIN_PACKAGES = (
    'core', 'adapters', 'infrastructure', 'config', 'ui', 'extensions', 'filtermate_api',
    'filter_mate', 'filter_mate_app', 'filter_mate_dockwidget',
)


def _core_modules() -> list[Path]:
    return sorted(_CORE.rglob('*.py'))


def _depth_inside_core(py: Path) -> int:
    """How many packages deep ``py`` sits inside ``filtermate_core`` (the root package counts 1)."""
    rel = py.relative_to(_CORE)
    parts = rel.parts if py.name != '__init__.py' else rel.parts[:-1]
    return len(parts)  # file at filtermate_core/x.py -> 1 ; filtermate_core/a/x.py -> 2


def _offending_imports():
    for py in _core_modules():
        tree = ast.parse(py.read_text(encoding='utf-8'))
        max_level = _depth_inside_core(py)  # a module may climb up to the package root, not above
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split('.')[0]
                    if root in HOST_PACKAGES or root in PLUGIN_PACKAGES:
                        yield py.relative_to(_ROOT), node.lineno, f'import {alias.name}'
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    root = (node.module or '').split('.')[0]
                    if root in HOST_PACKAGES or root in PLUGIN_PACKAGES:
                        yield py.relative_to(_ROOT), node.lineno, f'from {node.module} import …'
                elif node.level > max_level:
                    yield py.relative_to(_ROOT), node.lineno, f'from {"." * node.level}{node.module or ""} import … (leaves the package)'


@pytest.mark.unit
def test_core_exists_and_is_not_empty():
    assert (_CORE / '__init__.py').exists()
    assert len(_core_modules()) > 20


@pytest.mark.unit
def test_no_host_or_plugin_import_in_core():
    bad = [f'{path}:{line} {stmt}' for path, line, stmt in _offending_imports()]
    assert not bad, (
        'filtermate_core must stay host-free; forbidden imports:\n  ' + '\n  '.join(bad)
    )


_RUNTIME_CHECK = r'''
import importlib, pkgutil, sys
sys.path.insert(0, sys.argv[1])

BLOCKED = {blocked!r}

class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in BLOCKED:
            raise ImportError(f'blocked host package: {{name}}')
        return None

sys.meta_path.insert(0, _Blocker())

import filtermate_core
failed = []
for info in pkgutil.walk_packages(filtermate_core.__path__, 'filtermate_core.'):
    try:
        importlib.import_module(info.name)
    except Exception as e:  # noqa: BLE001 - report every module
        failed.append(f'{{info.name}}: {{type(e).__name__}}: {{e}}')
print('\n'.join(failed))
sys.exit(1 if failed else 0)
'''


@pytest.mark.unit
def test_every_core_module_imports_without_a_host():
    code = _RUNTIME_CHECK.format(blocked=set(HOST_PACKAGES) | set(PLUGIN_PACKAGES))
    proc = subprocess.run(  # nosec B603 - our own interpreter, our own code
        [sys.executable, '-I', '-c', code, str(_ROOT)],
        capture_output=True, text=True, timeout=120, cwd=str(_ROOT),
    )
    assert proc.returncode == 0, (
        'modules of filtermate_core that need a host or the plugin:\n' + proc.stdout + proc.stderr
    )
