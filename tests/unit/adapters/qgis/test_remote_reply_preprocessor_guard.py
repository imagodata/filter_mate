# -*- coding: utf-8 -*-
"""No setReplyPreprocessor call on the bindings where it segfaults (2026-10-19).

Until QGIS 3.36.0 the binding converts the returned id to a Python string
after releasing the GIL; under Python 3.12 the registration itself crashes
QGIS (3.34.15 on Ubuntu 24.04), and Python's allocator debug hooks abort
under any version. Those builds refuse service reads like a QGIS without
the observer, and a memory read skips it.
"""
import importlib
import os
import pathlib
import re
import sys
import types
import weakref
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


def _qgis(monkeypatch, module, qgis_version, python_version, observer=True, dev_mode=False, debug_build=False):
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
    fake_sys = types.SimpleNamespace(version_info=python_version, flags=types.SimpleNamespace(dev_mode=dev_mode))
    if debug_build:
        fake_sys.gettotalrefcount = lambda: 0
    monkeypatch.setattr(module, "sys", fake_sys)
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
    _qgis(monkeypatch, module, 33415, (3, 11, 2), debug_build=True)
    assert module.supports_reply_validation() is False


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


@pytest.mark.parametrize("dead", ["provider", "network", "message_log", "preprocessor"])
def test_bounded_read_keeps_its_outcome_when_cleanup_meets_a_deleted_object(monkeypatch, dead):
    """CI ltr-noble, 2026-10-20: QGIS deleted the clone's provider before the read's cleanup, and
    ``provider.raiseError.disconnect`` raised RuntimeError from ``finally``, replacing the outcome."""
    module = _load()
    core = _qgis(monkeypatch, module, 33600, (3, 12, 3))
    monkeypatch.setattr(module, "require_worker", lambda: None)
    monkeypatch.setattr(module, "main_network_manager", lambda: None)
    deleted = RuntimeError("wrapped C/C++ object has been deleted")
    iterator = MagicMock()
    iterator.isValid.return_value = True
    iterator.__iter__.return_value = iter([])
    source = MagicMock()
    source.getFeatures.return_value = iterator
    source.dataProvider.return_value.name.return_value = "memory"
    if dead == "provider":
        source.dataProvider.return_value.raiseError.disconnect.side_effect = deleted
    elif dead == "network":
        core.QgsNetworkAccessManager.instance.return_value.finished.disconnect.side_effect = deleted
    elif dead == "message_log":
        core.QgsApplication.messageLog.return_value.messageReceived.disconnect.side_effect = deleted
    else:
        core.QgsNetworkAccessManager.removeReplyPreprocessor.side_effect = KeyError("{observer-id}")

    outcome = module.read_bounded_features(
        source, MagicMock(), module.MaterializationLimits(), None, lambda feature: True, lambda feature: 1,
        source_uri="memory?", provider_key="memory")

    assert outcome.complete and not outcome.fetched, outcome


@pytest.mark.parametrize("provider_key, qgis_version, python_version", [
    ("wfs", 33415, (3, 12, 3)),
    ("oapif", 33415, (3, 12, 3)),
    ("arcgisfeatureserver", 33415, (3, 12, 3)),
    ("wfs", 32216, (3, 10, 6)),   # an old backport exposing the observer stays unverified
])
def test_service_bounded_read_is_refused_before_any_request_without_the_observer(monkeypatch, provider_key,
                                                                                qgis_version, python_version):
    module = _load()
    core = _qgis(monkeypatch, module, qgis_version, python_version)
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
    """setRequestPreprocessor and QgsPathResolver's setters share the binding defect in QGIS 3.34."""
    excluded = {"tests", ".git", ".claude", "__pycache__", "_bmad", "_bmad-output", "website", "docs", "knowledge",
                "dist", "build", "scripts"}
    names = re.compile(r"\b(set(?:Reply|Request)Preprocessor|setPathPreprocessor|setPathWriter)\b")
    mentions, registrations = {}, 0
    for directory, subdirectories, files in os.walk(_ROOT):
        subdirectories[:] = sorted(name for name in subdirectories if name not in excluded)
        for file_name in files:
            if not file_name.endswith(".py"):
                continue
            path = pathlib.Path(directory, file_name)
            text = path.read_text(encoding="utf-8", errors="replace")
            found = set(names.findall(text))
            if found:
                mentions[path.relative_to(_ROOT).as_posix()] = found
                registrations += len(re.findall(r"\.setReplyPreprocessor\s*\(", text))
    assert mentions == {"adapters/qgis/remote_materializer.py": {"setReplyPreprocessor"}}
    assert registrations == 1


# A reply's wrapper invalidated while the reply is alive (CI stable / latest, 2026-10-20).
#
# PyQt invalidates the wrapper of a C++-created QObject when that object's destroyed()
# reaches its monitor: a queued call on the main thread, keyed by address. A worker-thread
# reply created at the address of a deleted one is handed that reply's wrapper while it is
# still referenced, or a fresh one, and the late notification then invalidates it while the
# new reply is alive and emitting its signals.

class _Signal:
    """A Qt signal; an exception escaping a slot is recorded, as Qt would only report it."""

    def __init__(self, escaped):
        self.slots, self.escaped = [], escaped

    def emit(self, *args):
        for slot in list(self.slots):
            try:
                slot(*args)
            except Exception as exc:
                self.escaped.append(exc)


class _Reply:
    """The live C++ reply, holding an unread HTTP 200 body, or a Qt network error code."""

    def __init__(self, body, code, escaped):
        self.body, self.code = body, code
        self.readyRead, self.finished, self.errorOccurred = _Signal(escaped), _Signal(escaped), _Signal(escaped)

    def bytesAvailable(self):
        return len(self.body)

    def peek(self, size):
        return self.body[:size]

    def error(self):
        return self.code


class _BoundSignal:
    def __init__(self, wrapper, signal):
        self.wrapper, self.signal = wrapper, signal

    def connect(self, slot, *args):
        self.wrapper.check()
        self.signal.slots.append(slot)
        self.wrapper.sip.connected(self.wrapper)


class _Wrapper:
    """A sip wrapper, unusable once invalidated, even through an attribute fetched before."""

    def __init__(self, fake_sip, reply):
        self.sip, self.reply, self.valid = fake_sip, reply, True

    def check(self):
        if not self.valid:
            raise RuntimeError("wrapped C/C++ object of type QNetworkReply has been deleted")

    def __getattr__(self, name):
        self.check()
        target = getattr(self.reply, name)
        if isinstance(target, _Signal):
            return _BoundSignal(self, target)

        def call(*args):
            self.check()
            return target(*args)
        return call


class _Sip:
    """sip's map, which does not own its wrappers; an invalidated one is forgotten."""

    def __init__(self):
        self.replies = {}
        self.wrappers = weakref.WeakValueDictionary()
        self.pending = 0  # late notifications: each invalidates the next wrapper built
        self.connections_left = None  # invalidate the wrapper in use after that many connections
        self.unwrapped = None  # called once the observer has taken the address
        self.built = 0

    def invalidate(self, address):
        wrapper = self.wrappers.pop(address, None)
        if wrapper is not None:
            wrapper.valid = False

    def connected(self, wrapper):
        if self.connections_left is not None:
            self.connections_left -= 1
            if not self.connections_left:
                self.invalidate(id(wrapper.reply))

    def unwrapinstance(self, wrapper):
        wrapper.check()
        if self.unwrapped is not None:
            self.unwrapped(id(wrapper.reply))
        return id(wrapper.reply)

    def wrapinstance(self, address, unused_type):
        wrapper = self.wrappers.get(address)
        if wrapper is None:
            wrapper = self.wrappers[address] = _Wrapper(self, self.replies[address])
            self.built += 1
            if self.pending:
                self.pending -= 1
                self.invalidate(address)
        return wrapper


_HEALTHY = b'{"type": "FeatureCollection", "features": [], "links": []}'
_EXCEPTION = b'<?xml version="1.0"?><ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"/>'


def _observed_read(monkeypatch, invalidate, body=_HEALTHY, code=0, qt_before_515=False, finish=True, late=False,
                   linger=False):
    """One OAPIF bounded read whose items reply has ``body`` and Qt error ``code``.

    ``invalidate`` is when PyQt drops the reply's wrapper: "never", "before" the observer
    runs, "unwrapped" once it has the address, "attach" after its first connection, "after"
    it returned, "twice" (after, and the first wrapper built again too). "unobservable" and
    "always" drop every wrapper built for the reply from "unwrapped" or "after" on;
    "partial" fails the third connection step only. ``finish`` False aborts the reply
    without finished(); ``late`` emits its signals once the iterator is closed; ``linger``
    emits readyRead again after the read has returned, and runs a preprocessor call that
    was already under way for another reply.
    """
    module = _load()
    core = _qgis(monkeypatch, module, 33600, (3, 12, 3))
    reply_class = types.SimpleNamespace(NetworkError=types.SimpleNamespace(NoError=0, OperationCanceledError=5))
    if not qt_before_515:
        reply_class.errorOccurred = "errorOccurred(QNetworkReply::NetworkError)"
    sys.modules["qgis.PyQt.QtNetwork"].QNetworkReply = reply_class
    fake_sip = _Sip()
    pyqt = types.ModuleType("qgis.PyQt")
    pyqt.sip = fake_sip
    monkeypatch.setitem(sys.modules, "qgis.PyQt", pyqt)
    monkeypatch.setattr(module, "require_worker", lambda: None)
    monkeypatch.setattr(module, "main_network_manager", lambda: None)
    request = MagicMock()
    request.attribute.return_value = None
    request.url.return_value.toString.return_value = "https://example.org/ogc/collections/points/items?limit=10"
    trace = types.SimpleNamespace(escaped=[], retained=None, retained_after_read=None, reply=None, sip=fake_sip)

    def signals():
        if invalidate in ("after", "twice", "always"):
            fake_sip.invalidate(id(trace.reply))
            fake_sip.pending = {"twice": 1, "always": 1000}.get(invalidate, 0)
        trace.reply.readyRead.emit()
        if code:
            trace.reply.errorOccurred.emit(code)
        if finish:
            trace.reply.finished.emit()
        trace.retained = id(trace.reply) in fake_sip.wrappers

    def features():
        observer = core.QgsNetworkAccessManager.setReplyPreprocessor.call_args[0][0]
        reply = trace.reply = _Reply(body, code, trace.escaped)
        fake_sip.replies[id(reply)] = reply
        wrapper = fake_sip.wrapinstance(id(reply), None)
        if invalidate == "before":
            fake_sip.invalidate(id(reply))
        elif invalidate in ("unwrapped", "unobservable"):
            fake_sip.unwrapped = fake_sip.invalidate
            fake_sip.pending = 1000 if invalidate == "unobservable" else 0
        elif invalidate in ("attach", "partial"):
            fake_sip.connections_left = 1 if invalidate == "attach" else 2
            fake_sip.pending = 3 if invalidate == "partial" else 0
        try:
            observer(request, wrapper)
        except Exception as exc:  # the QGIS binding leaves it unhandled
            trace.escaped.append(exc)
        del wrapper  # the binding's reference ends with the call
        if not late:
            signals()
        yield MagicMock()

    iterator = MagicMock()
    iterator.isValid.return_value = True
    iterator.__iter__.side_effect = features
    if late:
        iterator.close.side_effect = lambda: trace.retained is None and signals()
    source = MagicMock()
    source.getFeatures.return_value = iterator
    source.dataProvider.return_value.name.return_value = "oapif"
    outcome = module.read_bounded_features(
        source, MagicMock(), module.MaterializationLimits(), None, lambda feature: True, lambda feature: 1,
        source_uri="https://example.org/ogc", provider_key="oapif")
    replies = [trace.reply]
    if linger:
        trace.reply.readyRead.emit()
        replies.append(_Reply(body, code, trace.escaped))
        fake_sip.replies[id(replies[-1])] = replies[-1]
        core.QgsNetworkAccessManager.setReplyPreprocessor.call_args[0][0](
            request, fake_sip.wrapinstance(id(replies[-1]), None))
    trace.retained_after_read = any(id(reply) in fake_sip.wrappers for reply in replies)
    return outcome, trace


def _attached_once(reply):
    signals = (reply.readyRead, reply.finished, reply.errorOccurred)
    return all(len(signal.slots) == len(set(signal.slots)) for signal in signals) and len(reply.readyRead.slots) == 1


@pytest.mark.parametrize("qt_before_515", [False, True])
@pytest.mark.parametrize("invalidate", ["never", "unwrapped", "attach", "after", "twice"])
def test_a_healthy_reply_is_complete_when_pyqt_drops_its_wrapper(monkeypatch, invalidate, qt_before_515):
    outcome, trace = _observed_read(monkeypatch, invalidate, qt_before_515=qt_before_515)

    assert outcome.complete and outcome.keys == (1,), outcome
    assert not trace.escaped and _attached_once(trace.reply)
    # A wrapper still held once its reply finished would be handed to the next reply at its address.
    assert trace.retained is False and trace.retained_after_read is False
    if invalidate == "never":
        assert trace.sip.built == 1  # one wrapper for the reply's life, not one per signal


@pytest.mark.parametrize("qt_before_515", [False, True])
@pytest.mark.parametrize("invalidate", ["never", "unwrapped", "attach", "after", "twice"])
@pytest.mark.parametrize("body, code", [(_EXCEPTION, 0), (_HEALTHY, 3)], ids=["exception_report", "qt_error"])
def test_errors_are_still_refused_when_pyqt_drops_the_wrapper(monkeypatch, invalidate, body, code, qt_before_515):
    outcome, trace = _observed_read(monkeypatch, invalidate, body, code, qt_before_515)

    assert outcome.reason == "read_error" and not outcome.complete and not outcome.keys, outcome
    assert not trace.escaped and _attached_once(trace.reply)


@pytest.mark.parametrize("qt_before_515", [False, True])
@pytest.mark.parametrize("invalidate", ["before", "unobservable", "partial", "always"])
def test_a_reply_that_cannot_be_observed_is_never_verified(monkeypatch, invalidate, qt_before_515):
    outcome, trace = _observed_read(monkeypatch, invalidate, qt_before_515=qt_before_515)

    assert outcome.reason == "read_error" and not outcome.complete and not outcome.keys, outcome
    assert not trace.escaped and trace.retained_after_read is False


@pytest.mark.parametrize("linger", [False, True])
def test_a_reply_aborted_without_finished_holds_no_wrapper_once_the_read_ends(monkeypatch, linger):
    """QGIS deletes an in-flight page at a feature limit, timeout or cancellation without finished()."""
    outcome, trace = _observed_read(monkeypatch, "never", finish=False, linger=linger)

    assert outcome.complete and trace.retained is True and trace.retained_after_read is False
    assert not trace.escaped


@pytest.mark.parametrize("qt_before_515", [False, True])
@pytest.mark.parametrize("invalidate, code", [("always", 0), ("never", 5)], ids=["unobservable", "cancelled"])
def test_a_reply_lost_after_the_read_ended_does_not_refuse_it(monkeypatch, invalidate, code, qt_before_515):
    outcome, trace = _observed_read(monkeypatch, invalidate, code=code, qt_before_515=qt_before_515, late=True)

    assert outcome.complete and outcome.keys == (1,), outcome
    assert not trace.escaped and trace.retained_after_read is False


def test_a_provider_wrapper_invalidated_by_pyqt_does_not_fail_the_read(monkeypatch):
    """The provider of a worker-side copy loses its fresh wrapper like a reply can."""
    module = _load()
    _qgis(monkeypatch, module, 33600, (3, 12, 3))
    monkeypatch.setattr(module, "require_worker", lambda: None)
    monkeypatch.setattr(module, "main_network_manager", lambda: None)
    deleted = RuntimeError("wrapped C/C++ object of type QgsVectorDataProvider has been deleted")
    stale, fresh = MagicMock(), MagicMock()
    stale.raiseError.connect.side_effect = deleted
    stale.name.side_effect = deleted
    fresh.name.side_effect = deleted  # invalidated again after its connection
    iterator = MagicMock()
    iterator.isValid.return_value = True
    iterator.__iter__.return_value = iter([])
    source = MagicMock()
    source.getFeatures.return_value = iterator
    source.dataProvider.side_effect = [stale, fresh]

    outcome = module.read_bounded_features(
        source, MagicMock(), module.MaterializationLimits(), None, lambda feature: True, lambda feature: 1,
        source_uri="memory?", provider_key="memory")

    assert outcome.complete and not outcome.fetched, outcome
    fresh.raiseError.connect.assert_called_once()
    fresh.raiseError.disconnect.assert_called_once()
