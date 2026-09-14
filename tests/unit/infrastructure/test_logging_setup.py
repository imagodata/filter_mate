# -*- coding: utf-8 -*-
"""
PERF 2026-09-12: root logger level and dual root configuration.

- The root level defaults to INFO (was DEBUG while every handler dropped
  DEBUG records anyway) and can be raised through FILTERMATE_LOG_LEVEL.
- Both logger families ('FilterMate.*' and the package family used by
  ``logging.getLogger(__name__)``) receive the same handlers.
"""

import logging

import pytest

from infrastructure import logging as fm_logging


@pytest.mark.unit
class TestResolveRootLogLevel:

    def test_default_is_info(self, monkeypatch):
        monkeypatch.delenv("FILTERMATE_LOG_LEVEL", raising=False)
        assert fm_logging._resolve_root_log_level() == logging.INFO

    @pytest.mark.parametrize("value,expected", [
        ("DEBUG", logging.DEBUG),
        ("debug", logging.DEBUG),
        (" warning ", logging.WARNING),
        ("ERROR", logging.ERROR),
    ])
    def test_env_override(self, monkeypatch, value, expected):
        monkeypatch.setenv("FILTERMATE_LOG_LEVEL", value)
        assert fm_logging._resolve_root_log_level() == expected

    def test_garbage_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("FILTERMATE_LOG_LEVEL", "VERBOSE_PLEASE")
        assert fm_logging._resolve_root_log_level() == logging.INFO


@pytest.mark.unit
class TestRootLoggerConfiguration:

    @pytest.fixture(autouse=True)
    def _restore_logger_state(self):
        names = ("FilterMate", fm_logging._PACKAGE_LOGGER_NAME)
        saved = {n: (logging.getLogger(n).level, list(logging.getLogger(n).handlers)) for n in names}
        yield
        for name, (level, handlers) in saved.items():
            target = logging.getLogger(name)
            for handler in list(target.handlers):
                if handler not in handlers:
                    target.removeHandler(handler)
            target.setLevel(level)

    def test_both_roots_share_level_and_handlers(self, monkeypatch):
        monkeypatch.delenv("FILTERMATE_LOG_LEVEL", raising=False)
        monkeypatch.setattr(fm_logging, "_root_logger_configured", False)
        monkeypatch.setattr(fm_logging, "_file_handler", None)

        fm_logging._ensure_root_logger_configured()

        explicit_root = logging.getLogger("FilterMate")
        package_root = logging.getLogger(fm_logging._PACKAGE_LOGGER_NAME)

        assert explicit_root.level == logging.INFO
        assert package_root.level == logging.INFO
        # A debug call is now rejected at the logger level (no LogRecord built)
        assert not logging.getLogger("FilterMate.Anything").isEnabledFor(logging.DEBUG)
        assert not logging.getLogger(f"{fm_logging._PACKAGE_LOGGER_NAME}.core.x").isEnabledFor(logging.DEBUG)

        console_types = [type(h) for h in package_root.handlers]
        assert fm_logging.SafeStreamHandler in console_types
        if fm_logging._LOG_FILE:
            assert any(isinstance(h, fm_logging.RotatingFileHandler) for h in package_root.handlers)
            assert any(isinstance(h, fm_logging.RotatingFileHandler) for h in explicit_root.handlers)


@pytest.mark.unit
class TestGetLoggerPropagatesToTheRoots:
    """2026-09-14: get_logger() used to route every handler-less name through
    setup_logger(), which set propagate=False and attached a console-only
    handler: 'FilterMate.App', the plugin entry module and every
    get_logger(__name__) caller never wrote an INFO line to filtermate.log."""

    @pytest.fixture(autouse=True)
    def _configured_roots(self, monkeypatch):
        monkeypatch.delenv("FILTERMATE_LOG_LEVEL", raising=False)
        monkeypatch.setattr(fm_logging, "_root_logger_configured", False)
        monkeypatch.setattr(fm_logging, "_file_handler", None)
        names = ("FilterMate", fm_logging._PACKAGE_LOGGER_NAME)
        saved = {n: (logging.getLogger(n).level, list(logging.getLogger(n).handlers)) for n in names}
        yield
        for name, (level, handlers) in saved.items():
            target = logging.getLogger(name)
            for handler in list(target.handlers):
                if handler not in handlers:
                    target.removeHandler(handler)
            target.setLevel(level)

    @pytest.mark.parametrize("name", [
        "FilterMate.App",
        "FilterMate.Tasks",
        f"{fm_logging._PACKAGE_LOGGER_NAME}.filter_mate",
        f"{fm_logging._PACKAGE_LOGGER_NAME}.core.services.datasource_manager",
    ])
    def test_filtermate_names_propagate_and_own_no_handler(self, name):
        logger = fm_logging.get_logger(name)
        assert logger.propagate is True
        assert logger.handlers == []
        root = logging.getLogger(name.split(".")[0])
        assert any(isinstance(h, fm_logging.SafeStreamHandler) for h in root.handlers)

    def test_info_record_reaches_the_root_handlers(self):
        captured = []

        class _Sink(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        root = logging.getLogger("FilterMate")
        sink = _Sink(level=logging.INFO)
        root.addHandler(sink)
        try:
            fm_logging.get_logger("FilterMate.App").info("project switch step")
        finally:
            root.removeHandler(sink)
        assert captured == ["project switch step"]

    def test_earlier_standalone_setup_is_undone(self):
        standalone = fm_logging.setup_logger("FilterMate.Legacy")
        assert standalone.propagate is False and standalone.handlers

        logger = fm_logging.get_logger("FilterMate.Legacy")

        assert logger is standalone
        assert logger.propagate is True
        assert logger.handlers == []

    def test_foreign_names_keep_a_standalone_console_logger(self):
        logger = fm_logging.get_logger("some.other.tool")
        assert logger.propagate is False
        assert any(isinstance(h, fm_logging.SafeStreamHandler) for h in logger.handlers)

    def test_root_names_are_returned_untouched(self):
        root = fm_logging.get_logger("FilterMate")
        assert root is logging.getLogger("FilterMate")
        assert root.handlers  # the configured root keeps its handlers
