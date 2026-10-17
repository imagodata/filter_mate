# -*- coding: utf-8 -*-
"""An unsaved project falls back to Desktop / home (the comparison with './' never matched)."""
import os

import pytest

from core.domain.project_folder import project_folder

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("read_path", ["./", ".", ""])
def test_unsaved_project_falls_back_to_home_on_posix(read_path):
    assert project_folder(read_path, windows=False, environ={"HOME": "/home/ada"}) == os.path.normpath("/home/ada")


def test_unsaved_project_falls_back_to_the_desktop_on_windows():
    environ = {"USERPROFILE": "/users/ada", "HOME": "/ignored"}
    assert project_folder("./", windows=True, environ=environ) == os.path.normpath("/users/ada/Desktop")


def test_missing_environment_does_not_raise():
    assert project_folder("./", windows=True, environ={}) == os.path.normpath(os.path.expanduser("~"))


def test_saved_project_keeps_its_folder():
    folder = project_folder("/data/projects/communes/", windows=False, environ={"HOME": "/home/ada"})
    assert folder == os.path.normpath("/data/projects/communes")
