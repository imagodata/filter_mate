# -*- coding: utf-8 -*-
"""No setReplyPreprocessor call on the bindings where it segfaults (2026-10-19).

Until QGIS 3.36.0 the binding converts the returned id to a Python string
after releasing the GIL; under Python 3.12 the registration itself crashes
QGIS (3.34.15 on Ubuntu 24.04). Those builds refuse service reads like a
QGIS without the observer, and a memory read skips it.
"""
import importlib
import pathlib
import sys
import types
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_reply_preprocessor_guard_test"


def _load():
    for name, path in (("", _ROOT), (".adapters", _ROOT / "adapters"), (".adapters.qgis", _ROOT / "adapters" / "qgis"),
                       (".core", _ROOT / "core"), (".infrastructure", _ROOT / "infrastructure"),
                       (".config", _ROOT / "config")):
        if _PKG + name not in sys.modules:
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.adapters.qgis.remote_materializer")


@pytest.mark.parametrize("qgis_version, python_version, safe", [
    (33415, (3, 12, 3), False),   # 3.34.15 on Ubuntu 24.04: segfault on registration
    (33406, (3, 12, 3), False),   # every 3.34.x has the same binding
    (32815, (3, 13, 0), False),   # 3.28 LTR, same binding
    (32600, (3, 12, 0), False),   # the binding as introduced in 3.26
    (33599, (3, 12, 3), False),   # a 3.35 development build
    (33415, (3, 11, 9), True),    # Debian bookworm: no null thread-state read
    (33405, (3, 10, 12), True),   # qgis/qgis:release-3_34, Ubuntu 22.04
    (33600, (3, 12, 3), True),    # 3.36.0 converts the id under the GIL
    (34415, (3, 13, 7), True),
    (40300, (3, 13, 7), True),
])
def test_registration_is_safe_only_on_fixed_bindings_or_older_pythons(qgis_version, python_version, safe):
    assert _load().reply_preprocessor_is_safe(qgis_version, python_version) is safe


def _qgis(monkeypatch, module, qgis_version, python_version, observer=True):
    core = MagicMock()
    core.Qgis.QGIS_VERSION_INT = qgis_version
    if observer:
        core.QgsNetworkAccessManager.setReplyPreprocessor.return_value = "{observer-id}"
    else:
        del core.QgsNetworkAccessManager.setReplyPreprocessor
    core.QgsDataSourceUri.return_value.param.return_value = ""
    monkeypatch.setitem(sys.modules, "qgis.core", core)
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", MagicMock())
    monkeypatch.setitem(sys.modules, "qgis.PyQt.QtNetwork", MagicMock())
    monkeypatch.setattr(module, "sys", types.SimpleNamespace(version_info=python_version))
    return core


@pytest.mark.parametrize("qgis_version, python_version, observer, supported", [
    (33415, (3, 12, 3), True, False),
    (33415, (3, 10, 12), True, True),
    (33600, (3, 12, 3), True, True),
    (32216, (3, 10, 6), True, False),   # an old backport stays refused
    (33600, (3, 12, 3), False, False),
])
def test_service_reads_are_refused_where_the_observer_is_unsafe(monkeypatch, qgis_version, python_version,
                                                                observer, supported):
    module = _load()
    _qgis(monkeypatch, module, qgis_version, python_version, observer)
    assert module.supports_reply_validation() is supported


@pytest.mark.parametrize("qgis_version, python_version, registered", [
    (33415, (3, 12, 3), False),
    (33415, (3, 10, 12), True),
    (33600, (3, 12, 3), True),
])
def test_bounded_read_registers_the_observer_only_when_safe(monkeypatch, qgis_version, python_version, registered):
    module = _load()
    core = _qgis(monkeypatch, module, qgis_version, python_version)
    if not registered:
        core.QgsNetworkAccessManager.setReplyPreprocessor.side_effect = AssertionError("segfault on this build")
    monkeypatch.setattr(module, "require_worker", lambda: None)
    monkeypatch.setattr(module, "main_network_manager", lambda: None)
    iterator = MagicMock()
    iterator.isValid.return_value = True
    iterator.__iter__.return_value = iter([])
    source = MagicMock()
    source.getFeatures.return_value = iterator
    source.dataProvider.return_value.name.return_value = "memory"

    outcome = module.read_bounded_features(
        source, MagicMock(), module.MaterializationLimits(), None, lambda feature: True, lambda feature: 1,
        source_uri="memory?", provider_key="memory")

    assert outcome.complete and not outcome.fetched, outcome
    manager = core.QgsNetworkAccessManager
    assert manager.setReplyPreprocessor.called is registered
    if registered:
        manager.removeReplyPreprocessor.assert_called_once_with("{observer-id}")
    else:
        manager.removeReplyPreprocessor.assert_not_called()
