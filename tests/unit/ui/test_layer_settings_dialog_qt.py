# -*- coding: utf-8 -*-
"""
2026-11-24: the question asked at the opening of a project whose layer settings differ from this computer's.

Both groups ticked (the project is the truth); Keep mine takes nothing; a closed dialog answers nothing and remembers
nothing. Loaded with ``qgis.PyQt`` pointing at PyQt5 for the import only (the root conftest mocks Qt).
"""
import importlib.util
import os
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui  # noqa: E402

_PATH = pathlib.Path(__file__).resolve().parents[3] / "ui" / "dialogs" / "layer_settings_dialog.py"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets}
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)
    try:
        spec = importlib.util.spec_from_file_location("fmtest_layer_settings_dialog", _PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return app, module
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


_APP, dialog_module = _load()


def _box(dialog, name, kind=QtWidgets.QCheckBox):
    return dialog.findChild(kind, name)


def test_both_groups_ticked_and_applied():
    dialog = dialog_module.LayerSettingsDialog(["exploring", "filtering"])
    assert _box(dialog, "exploring").isChecked() and _box(dialog, "filtering").isChecked()
    assert _box(dialog, "exploring").text() == "EXPLORING"
    _box(dialog, "apply", QtWidgets.QPushButton).click()
    assert dialog.chosen_groups() == ["exploring", "filtering"] and dialog.remember() is False


def test_filtering_only_remembered():
    dialog = dialog_module.LayerSettingsDialog(["exploring", "filtering"])
    _box(dialog, "exploring").setChecked(False)
    _box(dialog, "remember").setChecked(True)
    _box(dialog, "apply", QtWidgets.QPushButton).click()
    assert dialog.chosen_groups() == ["filtering"] and dialog.remember() is True


def test_keep_mine_takes_nothing():
    dialog = dialog_module.LayerSettingsDialog(["filtering"])
    _box(dialog, "remember").setChecked(True)
    _box(dialog, "keep", QtWidgets.QPushButton).click()
    assert dialog.chosen_groups() == [] and dialog.remember() is True
    assert _box(dialog, "exploring") is None  # a group with no difference is not asked


def test_a_closed_dialog_answers_nothing():
    dialog = dialog_module.LayerSettingsDialog(["exploring", "filtering"])
    _box(dialog, "remember").setChecked(True)
    dialog.reject()
    assert dialog.chosen_groups() == [] and dialog.remember() is False


def test_no_remember_without_the_option():
    dialog = dialog_module.LayerSettingsDialog(["exploring"], can_remember=False)
    assert _box(dialog, "remember").isHidden()
    _box(dialog, "remember").setChecked(True)
    _box(dialog, "apply", QtWidgets.QPushButton).click()
    assert dialog.remember() is False
