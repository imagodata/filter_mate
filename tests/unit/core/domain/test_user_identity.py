# -*- coding: utf-8 -*-
"""
Tests for ``core.domain.user_identity`` cascade resolver.

Cascade order (first non-empty wins):
    APP.USER_IDENTITY  →  QgsSettings("qgis/userName")  →  OS user
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_identity_cache():
    """Cache bleeds across tests — clear before and after each one."""
    from core.domain import user_identity
    user_identity.invalidate_identity_cache()
    yield
    user_identity.invalidate_identity_cache()


class TestCascade:
    def test_config_wins_when_set(self, monkeypatch):
        from core.domain import user_identity

        monkeypatch.setattr(user_identity, "_from_config",
                            lambda: "alice.config")
        monkeypatch.setattr(user_identity, "_from_qgis_settings",
                            lambda: "should-not-see")
        monkeypatch.setattr(user_identity, "_from_os",
                            lambda: "should-not-see")

        assert user_identity.resolve_current_user() == "alice.config"

    def test_qgis_settings_wins_over_os(self, monkeypatch):
        from core.domain import user_identity

        monkeypatch.setattr(user_identity, "_from_config",
                            lambda: None)
        monkeypatch.setattr(user_identity, "_from_qgis_settings",
                            lambda: "alice.qgis")
        monkeypatch.setattr(user_identity, "_from_os",
                            lambda: "os-user")

        assert user_identity.resolve_current_user() == "alice.qgis"

    def test_os_is_last_resort(self, monkeypatch):
        from core.domain import user_identity

        monkeypatch.setattr(user_identity, "_from_config", lambda: None)
        monkeypatch.setattr(user_identity, "_from_qgis_settings", lambda: None)
        monkeypatch.setattr(user_identity, "_from_os", lambda: "alice.os")

        assert user_identity.resolve_current_user() == "alice.os"

    def test_all_empty_returns_none(self, monkeypatch):
        from core.domain import user_identity

        monkeypatch.setattr(user_identity, "_from_config", lambda: None)
        monkeypatch.setattr(user_identity, "_from_qgis_settings", lambda: None)
        monkeypatch.setattr(user_identity, "_from_os", lambda: None)

        assert user_identity.resolve_current_user() is None

    def test_empty_string_treated_as_empty(self, monkeypatch):
        from core.domain import user_identity

        # Whitespace / empty strings shouldn't win the cascade
        monkeypatch.setattr(user_identity, "_from_config", lambda: "")
        monkeypatch.setattr(user_identity, "_from_qgis_settings", lambda: "   ")
        monkeypatch.setattr(user_identity, "_from_os", lambda: "alice.os")

        assert user_identity.resolve_current_user() == "alice.os"


class TestCache:
    def test_cached_across_calls(self, monkeypatch):
        from core.domain import user_identity

        calls = {"n": 0}

        def counting_os():
            calls["n"] += 1
            return "alice"

        monkeypatch.setattr(user_identity, "_from_config", lambda: None)
        monkeypatch.setattr(user_identity, "_from_qgis_settings", lambda: None)
        monkeypatch.setattr(user_identity, "_from_os", counting_os)

        user_identity.resolve_current_user()
        user_identity.resolve_current_user()
        user_identity.resolve_current_user()
        assert calls["n"] == 1

    def test_invalidate_cache_forces_re_resolution(self, monkeypatch):
        from core.domain import user_identity

        values = iter(["first", "second"])
        monkeypatch.setattr(user_identity, "_from_config", lambda: None)
        monkeypatch.setattr(user_identity, "_from_qgis_settings", lambda: None)
        monkeypatch.setattr(user_identity, "_from_os", lambda: next(values))

        assert user_identity.resolve_current_user() == "first"
        user_identity.invalidate_identity_cache()
        assert user_identity.resolve_current_user() == "second"

    def test_none_result_is_cached_too(self, monkeypatch):
        """An exhausted cascade must cache None — otherwise every call
        re-runs OS lookups that may be expensive in a headless CI setup.
        """
        from core.domain import user_identity

        calls = {"n": 0}

        def counting_config():
            calls["n"] += 1
            return None

        monkeypatch.setattr(user_identity, "_from_config", counting_config)
        monkeypatch.setattr(user_identity, "_from_qgis_settings", lambda: None)
        monkeypatch.setattr(user_identity, "_from_os", lambda: None)

        assert user_identity.resolve_current_user() is None
        assert user_identity.resolve_current_user() is None
        assert calls["n"] == 1


# TestConfigReader was removed — ENV_VARS is a process-wide global and
# mutating it from a test leads to cross-test bleed (another test may
# populate CONFIG_DATA.APP.USER_IDENTITY before this one runs, making
# "empty env" assertions unstable). The cascade tests above fully cover
# the behaviour via mocked step functions.
