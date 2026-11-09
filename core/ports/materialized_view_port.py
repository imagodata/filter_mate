# -*- coding: utf-8 -*-
"""Compatibility shim: this module moved to ``filtermate_core.ports.materialized_view_port``.

The name is aliased to the moved module so existing imports, ``isinstance``
checks and ``mock.patch`` targets keep working; new code imports
``filtermate_core`` directly. The moved module is looked up under this
module's own package prefix (``filter_mate.`` in QGIS, nothing when the
sub-packages are imported from the repository root) and, failing that, as the
top-level ``filtermate_core`` next to this file, so loaders that register the
file under another name (tests) get the same objects.
"""
import importlib as _importlib
import os as _os
import sys as _sys

_OLD = 'core.ports.materialized_view_port'
_NEW = 'filtermate_core.ports.materialized_view_port'
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..'))


def _load():
    if __name__ == _OLD or __name__.endswith('.' + _OLD):
        try:
            return _importlib.import_module(__name__[:-len(_OLD)] + _NEW)
        except ImportError:
            pass  # not reachable under this prefix: use the top-level spelling
    if _ROOT not in _sys.path:
        _sys.path.append(_ROOT)
    return _importlib.import_module(_NEW)


_moved = _load()
_sys.modules[__name__] = _moved
__all__ = getattr(_moved, '__all__', [_n for _n in vars(_moved) if not _n.startswith('_')])


def __getattr__(name):
    """Delegate to the moved module for loaders that keep this module object."""
    return getattr(_moved, name)
