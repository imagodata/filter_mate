# -*- coding: utf-8 -*-
"""No setReplyPreprocessor call on the bindings where it segfaults (2026-10-19).

Until QGIS 3.36.0 the binding converts the returned id to a Python string
after releasing the GIL; under Python 3.12 the registration itself crashes
QGIS (3.34.15 on Ubuntu 24.04), and Python's allocator debug hooks abort
under any version. Those builds refuse service reads like a QGIS without
the observer, and a memory read skips it.
"""
import importlib
import pathlib
import re
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


@pytest.mark.parametrize("qgis_version, python_version, safe", [
    (33415, (3, 11, 2), False),   # "Python memory allocator called without holding the GIL"
    (33405, (3, 10, 12), False),
    (33600, (3, 12, 3), True),
])
def test_allocator_debug_hooks_abort_on_the_unfixed_binding(qgis_version, python_version, safe):
    assert _load().reply_preprocessor_is_safe(qgis_version, python_version, debug_allocator=True) is safe


def _qgis(monkeypatch, module, qgis_version, python_version, observer=True, dev_mode=False):
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
    monkeypatch.setattr(module, "sys", types.SimpleNamespace(
        version_info=python_version, flags=types.SimpleNamespace(dev_mode=dev_mode)))
    monkeypatch.delenv("PYTHONMALLOC", raising=False)
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


def test_debug_hooks_from_development_mode_or_environment_refuse(monkeypatch):
    module = _load()
    _qgis(monkeypatch, module, 33415, (3, 11, 2), dev_mode=True)
    assert module.supports_reply_validation() is False
    _qgis(monkeypatch, module, 33415, (3, 11, 2))
    monkeypatch.setenv("PYTHONMALLOC", "pymalloc_debug")
    assert module.supports_reply_validation() is False
    monkeypatch.setenv("PYTHONMALLOC", "malloc")
    assert module.supports_reply_validation() is True


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


@pytest.mark.parametrize("provider_key", ["wfs", "oapif", "arcgisfeatureserver"])
def test_service_bounded_read_is_refused_before_any_request_without_the_observer(monkeypatch, provider_key):
    module = _load()
    core = _qgis(monkeypatch, module, 33415, (3, 12, 3))
    core.QgsNetworkAccessManager.setReplyPreprocessor.side_effect = AssertionError("segfault on this build")
    monkeypatch.setattr(module, "require_worker", lambda: None)
    source = MagicMock()
    factory = MagicMock(side_effect=AssertionError("provider construction can already download"))

    outcome = module.read_bounded_features(
        source, MagicMock(), module.MaterializationLimits(), None, lambda feature: True, lambda feature: 1,
        source_uri="url=https://example.org/wfs", source_factory=factory, provider_key=provider_key)

    assert outcome.reason == "unverified_filter" and not outcome.complete and not outcome.keys
    factory.assert_not_called()
    source.getFeatures.assert_not_called()


def test_no_other_qgis_callback_registration_with_an_unlocked_allocation():
    """setRequestPreprocessor and QgsPathResolver's setters share the binding defect."""
    excluded = {"tests", ".git", ".claude", "__pycache__", "_bmad", "_bmad-output", "website", "docs", "knowledge",
                "dist", "build", "scripts"}
    calls = {}
    for path in sorted(_ROOT.rglob("*.py")):
        name = path.relative_to(_ROOT).as_posix()
        if excluded.intersection(name.split("/")):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"\.(set(?:Reply|Request)Preprocessor|setPathPreprocessor|setPathWriter)\(", text):
            calls.setdefault(match.group(1), []).append(name)
    assert calls == {"setReplyPreprocessor": ["adapters/qgis/remote_materializer.py"]}
