"""A1 — ResultProcessor routes warnings via IFeedback, not iface.

Audit 2026-04-29 (A1): ``core/filter/result_processor.py`` imported ``iface``
at module level, breaking the hexagonal contract. The fix wires the
:class:`IFeedback` port and uses :func:`get_feedback_adapter` instead.
These tests pin the new contract:

1. The ``iface`` symbol must NOT be imported at module load.
2. ``_display_warnings`` must route through the port when wired.
3. ``_display_warnings`` must downgrade gracefully (log only) when the
   adapter has not been wired (headless / partial init).
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


ROOT = "filter_mate_a1"


def _install_stubs() -> None:
    """Stub the QGIS / infrastructure imports performed at module load."""
    if ROOT not in sys.modules:
        pkg = types.ModuleType(ROOT)
        pkg.__path__ = []
        sys.modules[ROOT] = pkg

    stubs = [
        "qgis", "qgis.core", "qgis.PyQt", "qgis.PyQt.QtCore",
        f"{ROOT}.infrastructure",
        f"{ROOT}.infrastructure.database",
        f"{ROOT}.infrastructure.database.sql_utils",
        f"{ROOT}.infrastructure.signal_utils",
        f"{ROOT}.core",
        f"{ROOT}.core.ports",
        f"{ROOT}.core.ports.qgis_port",
    ]
    for name in stubs:
        sys.modules.setdefault(name, MagicMock())

    # Names the module pulls via `from X import Y`.
    sys.modules["qgis.core"].QgsVectorLayer = MagicMock
    sys.modules["qgis.core"].QgsMessageLog = MagicMock
    sys.modules["qgis.core"].Qgis = MagicMock
    sys.modules[f"{ROOT}.infrastructure.database.sql_utils"].safe_set_subset_string = MagicMock()
    sys.modules[f"{ROOT}.infrastructure.signal_utils"].SignalBlocker = MagicMock

    # core.ports re-exports get_backend_services. Provide a callable that
    # returns an object with the attributes the module reads at import.
    backend_services_stub = MagicMock()
    backend_services_stub.is_valid_layer = MagicMock(return_value=True)
    sys.modules[f"{ROOT}.core.ports"].get_backend_services = MagicMock(
        return_value=backend_services_stub
    )


_install_stubs()


# Build an enum-ish stand-in for the real MessageLevel + a mutable feedback
# adapter slot so the tests can inject and reset between cases.
_LEVELS = types.SimpleNamespace(INFO="INFO", WARNING="WARNING", CRITICAL="CRITICAL", SUCCESS="SUCCESS")
sys.modules[f"{ROOT}.core.ports.qgis_port"].MessageLevel = _LEVELS

_state = {"adapter": None}


def _get_feedback_adapter():
    if _state["adapter"] is None:
        raise RuntimeError("Feedback adapter not initialized.")
    return _state["adapter"]


sys.modules[f"{ROOT}.core.ports.qgis_port"].get_feedback_adapter = _get_feedback_adapter


_processor_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..",
    "core", "filter", "result_processor.py",
))
_spec = importlib.util.spec_from_file_location(
    f"{ROOT}.core.filter.result_processor", _processor_path
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = f"{ROOT}.core.filter"
sys.modules[_mod.__name__] = _mod
_spec.loader.exec_module(_mod)


ResultProcessor = _mod.ResultProcessor


@pytest.fixture(autouse=True)
def reset_adapter():
    _state["adapter"] = None
    yield
    _state["adapter"] = None


def _make_processor() -> ResultProcessor:
    return ResultProcessor(task_action="filter", task_parameters={})


class TestNoIfaceImport:
    def test_module_does_not_import_iface(self):
        # The fixed module must not bind ``iface`` at module load — that's
        # the hexagonal violation A1 closes.
        assert "iface" not in vars(_mod), (
            "REGRESSION A1: result_processor module must not import iface "
            "at module level — route via the IFeedback port instead."
        )


class TestDisplayWarningsRoutesThroughPort:
    def test_warning_messages_pushed_via_adapter(self):
        adapter = MagicMock()
        _state["adapter"] = adapter

        proc = _make_processor()
        proc.warning_messages = ["queue lag", "extent skipped"]
        proc._display_warnings()

        assert adapter.push_message.call_count == 2
        first_call = adapter.push_message.call_args_list[0]
        assert first_call.args[0] == "FilterMate"
        assert first_call.args[1] == "queue lag"
        assert first_call.args[2] == _LEVELS.WARNING
        assert proc.warning_messages == []

    def test_backend_warnings_pushed_via_adapter(self):
        adapter = MagicMock()
        _state["adapter"] = adapter

        proc = _make_processor()
        proc.backend_warnings = ["pg connection slow"]
        proc._display_warnings()

        adapter.push_message.assert_called_once_with(
            "FilterMate", "pg connection slow", _LEVELS.WARNING
        )
        assert proc.backend_warnings == []

    def test_both_buckets_drained_in_one_call(self):
        adapter = MagicMock()
        _state["adapter"] = adapter

        proc = _make_processor()
        proc.warning_messages = ["w1"]
        proc.backend_warnings = ["b1", "b2"]
        proc._display_warnings()

        assert adapter.push_message.call_count == 3
        assert proc.warning_messages == []
        assert proc.backend_warnings == []


class TestDisplayWarningsFallback:
    def test_no_adapter_does_not_raise(self):
        # Adapter not wired (state["adapter"] is None → RuntimeError).
        # _display_warnings must downgrade silently to logging — never
        # raise into the caller (which is finished() on the main thread).
        _state["adapter"] = None

        proc = _make_processor()
        proc.warning_messages = ["a"]
        proc.backend_warnings = ["b"]
        proc._display_warnings()  # must not raise

        # Buckets still drained so the next call doesn't repeat the messages.
        assert proc.warning_messages == []
        assert proc.backend_warnings == []

    def test_no_warnings_short_circuits_without_touching_adapter(self):
        adapter = MagicMock()
        _state["adapter"] = adapter

        proc = _make_processor()
        # Both buckets empty.
        proc._display_warnings()

        adapter.push_message.assert_not_called()
