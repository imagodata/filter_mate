# -*- coding: utf-8 -*-
"""
Passwords must never reach filtermate.log, the console, config.json or the
project database.

QGIS puts ``password='...'`` in the source of a PostgreSQL layer that has no
authentication config, and FilterMate logged ``layer.source()`` (and, through
the datasource tracking, saved the URI in config.json). A filter on the
FilterMate handlers masks it whatever the message.
"""
import io
import logging
import sys
import types

import pytest

from infrastructure import logging as fm_logging
from infrastructure.logging.redaction import (
    SecretMaskingFilter, mask_sensitive_text, mask_uri_secrets, scrub_secrets_in_place)

pytestmark = pytest.mark.unit

SOURCE = ("dbname='gis' host=db.example port=5432 user='bob' password='s3cret' "
          "sslmode=disable key='id' table=\"public\".\"roads\" (geom)")


class TestMaskSensitiveText:
    def test_quoted_password_of_a_postgresql_source(self):
        masked = mask_sensitive_text(SOURCE)
        assert "s3cret" not in masked
        assert "password='***'" in masked
        # the rest stays readable
        assert "dbname='gis' host=db.example" in masked
        assert 'table="public"."roads" (geom)' in masked

    @pytest.mark.parametrize("text", [
        "host=h password=hunter2 port=5432",
        "host=h PASSWORD = 'hunter2' port=5432",
        'password="hunter2"',
        "password='it\\'s hunter2'",
        "{'user': 'bob', 'password': 'hunter2'}",
        '{"user": "bob", "password": "hunter2"}',
        "passwd=hunter2",
        "postgresql://bob:hunter2@db.example/gis",
        "sslpassword=hunter2",
        "pwd=hunter2",
        "PGPASSWORD=hunter2",
        "user_password=hunter2",
        "DB_PASSWORD = 'hunter2'",
        "https://user:hunter2@github.com/org/repo.git",
        "url='https://u:hunter2@h/wfs'",
    ])
    def test_forms(self, text):
        masked = mask_sensitive_text(text)
        assert "hunter2" not in masked
        assert "hunter2"[1:] not in masked

    @pytest.mark.parametrize("text", [
        "Missing password: please configure",
        "password policy ok",
        'WHERE "passwd" = \'abc\' AND "x" = 1',
        "C:\\Users\\passwords\\file.gpkg",
        "pwd is /home/user",
    ])
    def test_prose_and_column_names_are_left_alone(self, text):
        assert mask_sensitive_text(text) == text

    def test_text_without_secret_is_returned_unchanged(self):
        text = "Layer 'roads' filtered: 120 features, password policy ok"
        assert mask_sensitive_text(text) == text

    def test_non_strings_pass_through(self):
        assert mask_sensitive_text(None) is None
        assert mask_sensitive_text(12) == 12

    def test_idempotent(self):
        once = mask_sensitive_text(SOURCE)
        assert mask_sensitive_text(once) == once


def _logger_with_stream(name, stream, with_filter=True):
    logger = logging.getLogger(name)
    logger.handlers = []
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    if with_filter:
        handler.addFilter(SecretMaskingFilter())
    logger.addHandler(handler)
    return logger


class TestSecretMaskingFilter:
    def test_preformatted_message(self):
        stream = io.StringIO()
        _logger_with_stream("fm.test.redact1", stream).warning(f"Layer source: {SOURCE}")
        assert "s3cret" not in stream.getvalue()
        assert "password='***'" in stream.getvalue()

    def test_lazy_arguments(self):
        stream = io.StringIO()
        _logger_with_stream("fm.test.redact2", stream).warning("Layer source: %s", SOURCE)
        assert "s3cret" not in stream.getvalue()

    def test_exception_text(self):
        stream = io.StringIO()
        logger = _logger_with_stream("fm.test.redact3", stream)
        try:
            raise RuntimeError(f"could not connect: {SOURCE}")
        except RuntimeError:
            logger.exception("connection failed")
        assert "s3cret" not in stream.getvalue()
        assert "connection failed" in stream.getvalue()

    def test_without_the_filter_the_secret_leaks(self):
        """Guard for the tests above: the stream really would carry it."""
        stream = io.StringIO()
        _logger_with_stream("fm.test.redact4", stream, with_filter=False).warning(SOURCE)
        assert "s3cret" in stream.getvalue()

    def test_a_record_that_cannot_be_formatted_is_kept(self):
        stream = io.StringIO()
        logger = _logger_with_stream("fm.test.redact5", stream)
        logger.handlers[0].setFormatter(logging.Formatter("%(message)s"))
        logger.warning("%d items", "not a number")  # logging reports its own error
        # the filter must not raise nor swallow the record


class TestHandlersOfTheFilterMateLoggers:
    @pytest.fixture(autouse=True)
    def _restore(self, monkeypatch):
        names = ("FilterMate", fm_logging._PACKAGE_LOGGER_NAME)
        saved = {n: (logging.getLogger(n).level, list(logging.getLogger(n).handlers)) for n in names}
        yield
        for name, (level, handlers) in saved.items():
            target = logging.getLogger(name)
            for handler in list(target.handlers):
                if handler not in handlers:
                    target.removeHandler(handler)
            target.setLevel(level)

    def test_root_handlers_carry_the_filter(self, monkeypatch, tmp_path):
        monkeypatch.setattr(fm_logging, "_root_logger_configured", False)
        monkeypatch.setattr(fm_logging, "_file_handler", None)
        monkeypatch.setattr(fm_logging, "_LOG_FILE", str(tmp_path / "filtermate.log"))
        for name in ("FilterMate", fm_logging._PACKAGE_LOGGER_NAME):
            logging.getLogger(name).handlers = []

        fm_logging._ensure_root_logger_configured()

        for name in ("FilterMate", fm_logging._PACKAGE_LOGGER_NAME):
            handlers = logging.getLogger(name).handlers
            assert handlers
            for handler in handlers:
                assert any(isinstance(f, SecretMaskingFilter) for f in handler.filters), handler

    def test_a_message_logged_through_get_logger_is_masked_in_the_file(self, monkeypatch, tmp_path):
        log_file = tmp_path / "filtermate.log"
        monkeypatch.setattr(fm_logging, "_root_logger_configured", False)
        monkeypatch.setattr(fm_logging, "_file_handler", None)
        monkeypatch.setattr(fm_logging, "_LOG_FILE", str(log_file))
        for name in ("FilterMate", fm_logging._PACKAGE_LOGGER_NAME):
            logging.getLogger(name).handlers = []

        logger = fm_logging.get_logger("FilterMate.RedactionTest")
        logger.info(f"source: {SOURCE}")
        fm_logging.flush_logs()

        written = log_file.read_text(encoding="utf-8")
        assert "source:" in written
        assert "s3cret" not in written

    def test_standalone_logger_file_and_console_handlers_carry_the_filter(self, tmp_path):
        name = "standalone.redaction.test"
        logging.getLogger(name).handlers = []
        logger = fm_logging.setup_logger(name, log_file=str(tmp_path / "x.log"))
        assert logger.handlers
        for handler in logger.handlers:
            assert any(isinstance(f, SecretMaskingFilter) for f in handler.filters)


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql):
        pass


class _FakeConnection:
    def __init__(self):
        self.closed_calls = 0
        self.rollbacks = 0

    def cursor(self):
        return _FakeCursor()

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed_calls += 1


class _FailingPgLayer:
    """A PostgreSQL layer without authcfg whose setSubsetString fails."""

    def name(self):
        return "roads"

    def providerType(self):
        return "postgres"

    def source(self):
        return SOURCE

    def isValid(self):
        return True

    def featureCount(self):
        return 0

    def subsetString(self):
        return ""

    def dataProvider(self):
        return types.SimpleNamespace(
            error=lambda: None, errors=lambda: [], reloadData=lambda: None)

    def setSubsetString(self, expression):
        return False


class TestSafeSetSubsetStringDiagnostics:
    @pytest.fixture
    def fake_probe(self, monkeypatch):
        connection = _FakeConnection()
        for name in ("filter_mate", "filter_mate.infrastructure"):
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
        utils = types.ModuleType("filter_mate.infrastructure.utils")
        utils.get_datasource_connexion_from_layer = lambda layer: (connection, None)
        monkeypatch.setitem(sys.modules, "filter_mate.infrastructure.utils", utils)
        # sql_utils imports ...infrastructure.utils relatively: re-root it under the fake filter_mate package
        from tests.unit.extensions.plugin_alias import alias_package
        alias_package(monkeypatch, "infrastructure.database.sql_utils")
        return connection

    def test_failure_diagnostics_do_not_log_the_password(self, fake_probe):
        from infrastructure.database import sql_utils

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(SecretMaskingFilter())  # as on the real handlers: the log call itself is masked
        previous_level = sql_utils.logger.level
        sql_utils.logger.setLevel(logging.DEBUG)
        sql_utils.logger.addHandler(handler)
        raw = []

        class _Raw(logging.Handler):
            def emit(self, record):
                raw.append(record.getMessage())

        raw_handler = _Raw()
        sql_utils.logger.addHandler(raw_handler)
        try:
            assert sql_utils.safe_set_subset_string(_FailingPgLayer(), "") is False
        finally:
            sql_utils.logger.removeHandler(handler)
            sql_utils.logger.removeHandler(raw_handler)
            sql_utils.logger.setLevel(previous_level)

        # even before any handler filter, the message built by FilterMate is clean
        assert any("Layer source" in m for m in raw)
        assert not [m for m in raw if "s3cret" in m]

    def test_the_probe_connection_is_closed(self, fake_probe):
        from infrastructure.database import sql_utils

        sql_utils.safe_set_subset_string(_FailingPgLayer(), "")

        assert fake_probe.closed_calls == 1


class TestMaskUriSecrets:
    """The narrow variant for saved data: connection-string passwords only."""

    @pytest.mark.parametrize("text", [
        SOURCE,
        "host=h password=hunter2 port=5432",
        "sslpassword='hunter2' sslmode=require",
        "postgresql://bob:hunter2@db.example/gis",
        "note: password='hunter2' was typed",
    ])
    def test_connection_strings(self, text):
        assert "hunter2" not in mask_uri_secrets(text) and "s3cret" not in mask_uri_secrets(text)

    @pytest.mark.parametrize("text", [
        'WHERE "passwd" = \'abc\' AND "x" = 1',
        "passwd = 'abc'",
        "pwd=abc",
        "PGPASSWORD=abc",
        "user_password=abc",
        '"password": "abc"',
        "password: abc",
        "Missing password: please configure",
        "the_password='abc'",
    ])
    def test_everything_else_is_left_alone(self, text):
        assert mask_uri_secrets(text) == text

    def test_idempotent_and_non_strings(self):
        once = mask_uri_secrets(SOURCE)
        assert mask_uri_secrets(once) == once
        assert mask_uri_secrets(None) is None and mask_uri_secrets(3) == 3


class TestScrubSecretsInPlace:
    """What an older version saved: URIs with their password, in config.json and the project settings."""

    def test_nested_structures_are_cleaned_and_counted(self):
        data = {
            "CURRENT_PROJECT": {"OPTIONS": {"ACTIVE_POSTGRESQL": [SOURCE], "IS_ACTIVE_POSTGRESQL": True,
                                            "note": f"was {SOURCE}"}},
            "APP": {"remotes": ["https://user:hunter2@github.com/x.git", "clean"]},
        }

        corrections = scrub_secrets_in_place(data)

        assert corrections == 3
        assert "s3cret" not in repr(data) and "hunter2" not in repr(data)
        assert data["CURRENT_PROJECT"]["OPTIONS"]["ACTIVE_POSTGRESQL"] == ""
        assert data["CURRENT_PROJECT"]["OPTIONS"]["IS_ACTIVE_POSTGRESQL"] is True
        assert data["APP"]["remotes"][1] == "clean"

    def test_clean_data_is_untouched_and_counts_zero(self):
        data = {"a": 1, "b": ["x", {"c": 'WHERE "passwd" = \'abc\''}], "ACTIVE_POSTGRESQL": None, "d": ""}
        before = repr(data)

        assert scrub_secrets_in_place(data) == 0
        assert repr(data) == before

    def test_second_pass_finds_nothing(self):
        data = {"x": SOURCE}
        assert scrub_secrets_in_place(data) == 1
        assert scrub_secrets_in_place(data) == 0
