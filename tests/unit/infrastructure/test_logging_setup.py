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
