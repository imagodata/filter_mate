# -*- coding: utf-8 -*-
"""An unsaved project falls back to Desktop / home (the comparison with './' never matched)."""
import os

import pytest

from core.domain.project_folder import project_folder

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("read_path", ["./", ".", ""])
def test_unsaved_project_falls_back_to_home_on_posix(read_path):
    assert project_folder(read_path, windows=False, environ={"HOME": "/home/ada"}) == os.path.normpath("/home/ada")


def test_unsaved_project_uses_the_desktop_qt_reports_on_windows(tmp_path):
    redirected = tmp_path / "OneDrive" / "Bureau"
    redirected.mkdir(parents=True)
    environ = {"USERPROFILE": str(tmp_path / "ada"), "HOME": "/ignored"}
    folder = project_folder("./", windows=True, environ=environ, desktop=str(redirected))
    assert folder == os.path.normpath(str(redirected))


def test_a_missing_desktop_is_never_created_the_profile_folder_is_used(tmp_path):
    profile = tmp_path / "ada"
    profile.mkdir()
    folder = project_folder("./", windows=True, environ={"USERPROFILE": str(profile)}, desktop=str(profile / "Desktop"))
    assert folder == os.path.normpath(str(profile))
    assert not (profile / "Desktop").exists()


def test_missing_environment_does_not_raise():
    assert project_folder("./", windows=True, environ={}, desktop="") == os.path.normpath(os.path.expanduser("~"))


def test_saved_project_keeps_its_folder():
    folder = project_folder("/data/projects/communes/", windows=False, environ={"HOME": "/home/ada"})
    assert folder == os.path.normpath("/data/projects/communes")
