# -*- coding: utf-8 -*-
"""
FilterMate 5: the centroid button sums up the per-target centroid toggles of
the FILTERING list (CentroidTargetsSync), on fake widgets.

Loaded by path under a private synthetic package like the other controller
tests: Qt / QGIS resolve to the root mocks.
"""
import importlib
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_centroid_sync_test"


def _load():
    for name, path in (
        ("", _ROOT),
        (".core", _ROOT / "core"),
        (".core.domain", _ROOT / "core" / "domain"),
        (".ui", _ROOT / "ui"),
        (".ui.controllers", _ROOT / "ui" / "controllers"),
    ):
        package = types.ModuleType(_PKG + name)
        package.__path__ = [str(path)]
        package.__package__ = _PKG + name
        sys.modules[_PKG + name] = package
    return importlib.import_module(f"{_PKG}.ui.controllers.centroid_targets_sync")


sync_module = _load()
CheckState = sync_module.Qt.CheckState


class FakeCombo:
    """Targets list: ``eligible`` line / polygon ids, ``checked`` ids, centroid toggles."""

    def __init__(self, eligible, checked, centroids=()):
        self.eligible, self.checked, self.centroids = list(eligible), set(checked), set(centroids)
        self.cleared = False

    def centroid_layer_ids(self):
        return [i for i in self.eligible if i in self.centroids]

    def centroid_eligible_ids(self, checked_only=False):
        return [i for i in self.eligible if not checked_only or i in self.checked]

    def set_centroid_layer_ids(self, ids, emit=False):
        self.centroids = set(ids) & set(self.eligible)

    def clear_centroid_toggles(self):
        self.cleared, self.eligible = True, []


class FakeButton:
    def __init__(self, checked=True):
        self.state, self.tristate, self.enabled, self.tooltip = CheckState.Unchecked, False, True, ""
        self.checked, self.blocked = checked, False

    def isChecked(self):
        return self.checked

    def checkState(self):
        return self.state

    def setCheckState(self, state):
        self.state = state

    def setTristate(self, tristate):
        self.tristate = tristate

    def blockSignals(self, blocked):
        previous, self.blocked = self.blocked, blocked
        return previous

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setToolTip(self, tip):
        self.tooltip = tip

    def update(self):
        pass


def _env(monkeypatch, combo, filtering=None, vector=True, targets_on=True):
    monkeypatch.setattr(sync_module.CentroidTargetsSync, "tr", lambda self, text: text, raising=False)
    saved = []
    layer = types.SimpleNamespace(id=lambda: "src")
    dock = types.SimpleNamespace(
        current_layer=layer,
        PROJECT_LAYERS={"src": {"filtering": dict(filtering or {})}},
        checkableComboBoxLayer_filtering_layers_to_filter=combo,
        checkBox_filtering_use_centroids_distant_layers=FakeButton(),
        pushButton_checkable_filtering_layers_to_filter=FakeButton(checked=targets_on),
        setLayerVariableEvent=lambda layer, props: saved.append(props),
    )
    sync = sync_module.CentroidTargetsSync(dock)
    monkeypatch.setattr(sync, "_source_is_vector", lambda: vector)
    return types.SimpleNamespace(sync=sync, dock=dock, button=dock.checkBox_filtering_use_centroids_distant_layers,
                                 combo=combo, saved=saved)


def test_old_projects_with_the_global_flag_turn_every_target_on(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads", "parcels"], ["roads", "parcels"]),
               {"use_centroids_distant_layers": True})
    env.sync.apply_stored()
    assert env.combo.centroid_layer_ids() == ["roads", "parcels"]
    assert env.button.state == CheckState.Checked and env.button.enabled


def test_some_targets_give_a_partial_button(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads", "parcels"], ["roads", "parcels"]), {"centroid_layers": ["parcels"]})
    env.sync.apply_stored()
    assert env.button.state == CheckState.PartiallyChecked and env.button.tristate is True


def test_a_click_sets_every_checked_target_and_stores_the_choice(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads", "parcels", "rivers"], ["roads", "parcels"]),
               {"centroid_layers": ["parcels"]})
    env.sync.apply_stored()
    env.sync.set_all(True)
    filtering = env.dock.PROJECT_LAYERS["src"]["filtering"]
    assert sorted(filtering["centroid_layers"]) == ["parcels", "roads"]  # the unchecked river is left alone
    assert filtering["use_centroids_distant_layers"] is True
    assert env.saved and ("filtering", "centroid_layers") in env.saved[-1]
    assert env.button.state == CheckState.Checked
    env.sync.set_all(False)
    assert env.dock.PROJECT_LAYERS["src"]["filtering"]["centroid_layers"] == []
    assert env.button.state == CheckState.Unchecked


def test_no_checked_line_or_polygon_target_disables_the_button(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads"], []))
    env.sync.apply_stored()
    assert env.button.enabled is False and "check one" in env.button.tooltip


def test_targets_key_off_disables_the_button(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads"], ["roads"], ["roads"]), targets_on=False)
    env.sync.refresh()
    assert env.button.enabled is False and env.button.state == CheckState.Unchecked


def test_nonvector_source_keeps_eligible_target_toggles(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads", "parcels"], ["roads", "parcels"]),
               {"centroid_layers": ["roads"]}, vector=False)
    env.sync.apply_stored()
    assert not env.combo.cleared and env.button.enabled
    assert env.button.state == CheckState.PartiallyChecked
    assert env.sync.centroid_ids() == ["roads"]
    env.sync.set_all(True)
    assert env.sync.centroid_ids() == ["roads", "parcels"]
    assert env.dock.PROJECT_LAYERS["src"]["filtering"]["centroid_layers"] == ["roads", "parcels"]
    assert env.saved == [], "nonvector settings must not emit the QgsVectorLayer-typed variable signal"
    env.sync.set_all(False)
    assert env.sync.centroid_ids() == [] and env.button.state == CheckState.Unchecked


def test_nonvector_choices_are_restored_per_source(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads", "parcels"], ["roads", "parcels"]),
               {"centroid_layers": ["roads"]}, vector=False)
    env.sync.apply_stored()
    env.dock.PROJECT_LAYERS["cloud"] = {"filtering": {"centroid_layers": ["parcels"]}}
    env.dock.current_layer = types.SimpleNamespace(id=lambda: "cloud")
    env.sync.apply_stored()
    assert env.sync.centroid_ids() == ["parcels"]
    env.dock.current_layer = types.SimpleNamespace(id=lambda: "src")
    env.sync.apply_stored()
    assert env.sync.centroid_ids() == ["roads"] and not env.combo.cleared


def test_refresh_gives_the_signals_back_even_on_error(monkeypatch):
    env = _env(monkeypatch, FakeCombo(["roads"], ["roads"]))

    def boom(_state):
        raise RuntimeError("wrapped C/C++ object has been deleted")

    env.button.setCheckState = boom
    with pytest.raises(RuntimeError):
        env.sync.refresh()
    assert env.button.blocked is False
