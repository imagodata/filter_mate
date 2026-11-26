# -*- coding: utf-8 -*-
"""Where the standalone application keeps its files (standalone/paths.py, standard library only)."""
import os
import stat

import pytest

pytestmark = pytest.mark.unit

from standalone import paths


@pytest.fixture
def home(tmp_path, monkeypatch):
    folder = tmp_path / "home"
    monkeypatch.setenv("FILTERMATE_HOME", str(folder))
    return folder


def test_profile_dir_lives_under_filtermate_home(home):
    assert paths.profile_dir() == os.path.join(str(home), "profile")
    assert paths.user_data_dir() == str(home)


def test_auth_password_file_created_once_mode_600(home):
    first = paths.auth_password_file()
    assert first == os.path.join(str(home), "auth-password")
    assert stat.S_IMODE(os.stat(first).st_mode) == 0o600
    with open(first, encoding="utf-8") as handle:
        secret = handle.read()
    assert len(secret) >= 32
    assert paths.auth_password_file() == first
    with open(first, encoding="utf-8") as handle:
        assert handle.read() == secret  # stable, not rewritten


def test_auth_password_file_regenerated_when_empty(home):
    path = paths.auth_password_file()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("  \n")
    assert paths.auth_password_file() == path
    with open(path, encoding="utf-8") as handle:
        assert handle.read().strip() != ""
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
