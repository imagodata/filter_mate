# -*- coding: utf-8 -*-
"""The environment the standalone host prepares (standalone/host/app.py, standard library and paths only).

Processing (GRASS) and the Qt libraries write beside $HOME (~/.grass8, ~/.cache): the host routes them into its
own folders instead (audit of 2026-11-24), unless the user already chose (an explicit XDG_CACHE_HOME, GISRC or
GRASS session keeps working as it does).
"""
import os
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

from standalone import paths
from standalone.host import app


@pytest.fixture
def moved_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("FILTERMATE_HOME", str(home))
    for key in ("XDG_CACHE_HOME", "GISRC", "QGIS_CUSTOM_CONFIG_PATH", "QGIS_AUTH_PASSWORD_FILE",
                "FILTERMATE_LOG_DIR"):
        monkeypatch.delenv(key, raising=False)
    return str(home)


def test_caches_and_grass_are_routed_into_the_application_folders(moved_home):
    profile = app.prepare_environment(SimpleNamespace(offscreen=True, profile=None))
    assert profile == paths.profile_dir()
    assert os.environ["XDG_CACHE_HOME"] == paths.cache_dir() == os.path.join(moved_home, "cache")
    assert os.environ["GISRC"] == paths.grassrc_file() == os.path.join(moved_home, "profile", "grassrc")


def test_an_explicit_cache_or_grass_setup_is_kept(moved_home, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", "/tmp/keep-cache")
    monkeypatch.setenv("GISRC", "/tmp/keep-grassrc")
    app.prepare_environment(SimpleNamespace(offscreen=True, profile=None))
    assert os.environ["XDG_CACHE_HOME"] == "/tmp/keep-cache"
    assert os.environ["GISRC"] == "/tmp/keep-grassrc"
