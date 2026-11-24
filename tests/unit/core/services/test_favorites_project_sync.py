# -*- coding: utf-8 -*-
"""The favorites of a saved project travel with its .qgz: FavoritesService.sync_with_project and the copy written at
each change (2026-11-24).

Two computers are two SQLite files; the project is a stand-in that keeps its entries as QgsProject does. Measured in
QGIS 3.44 before: a favorite added on computer A reached computer B one session late, and never when B had favorites
of its own (tests/qgis_headless/check_favorites_travel.py).
"""
import json
import sqlite3

import pytest

from core.domain import project_favorites
from core.domain.favorites_manager import FavoritesManager, FilterFavorite
from core.services.favorites_service import FavoritesService

pytestmark = pytest.mark.unit

PROJECT_UUID = "11111111-2222-3333-4444-555555555555"


class Project:
    """The entries of a QgsProject, and whether writing one made it dirty."""

    def __init__(self, entries=None):
        self.entries = dict(entries or {})
        self.writes = 0

    def readEntry(self, scope, key, default=""):  # noqa: N802 - the QGIS name
        found = (scope, key) in self.entries
        return self.entries.get((scope, key), default), found

    def writeEntry(self, scope, key, value):  # noqa: N802 - the QGIS name
        self.entries[(scope, key)] = value
        self.writes += 1
        return True

    def favorites(self):
        text, _ = self.readEntry(project_favorites.SCOPE, project_favorites.KEY)
        return sorted(row["name"] for row in json.loads(text)["favorites"]) if text else None


def computer(tmp_path, name, project, project_uuid=PROJECT_UUID):
    """FilterMate on a computer of its own, the project opened."""
    service = FavoritesService(FavoritesManager())
    service._project = staticmethod(lambda _project: project)
    service.set_database(str(tmp_path / f"{name}.sqlite"), project_uuid)
    return service


def add(service, name):
    favorite_id = service.add_favorite(name, f'"rank" < {len(name)}', layer_name="parcelles")
    service._mirror_to_project()  # favorites_changed calls it in QGIS (the signal is a stand-in here)
    return favorite_id


def names(service):
    return sorted(favorite.name for favorite in service.get_all_favorites())


def test_a_favorite_added_on_one_computer_is_on_the_other_at_the_next_opening(tmp_path):
    project = Project()
    a = computer(tmp_path, "a", project)
    add(a, "fav_A1")
    assert project.favorites() == ["fav_A1"]  # in the project before Ctrl+S, not at the next opening
    b = computer(tmp_path, "b", project)
    assert names(b) == ["fav_A1"]


def test_a_computer_with_favorites_of_its_own_gets_those_of_the_project(tmp_path):
    """Before, the backup was read only when the computer had no favorite of the project."""
    project = Project()
    a = computer(tmp_path, "a", project)
    add(a, "fav_A1")
    b = computer(tmp_path, "b", project)
    add(b, "fav_B1")
    a = computer(tmp_path, "a", project)
    assert names(a) == ["fav_A1", "fav_B1"]


def test_a_favorite_removed_on_one_computer_is_removed_on_the_other(tmp_path):
    """Option 1 of 2026-11-24: the project is the truth, no copy comes back."""
    project = Project()
    a = computer(tmp_path, "a", project)
    first = add(a, "fav_A1")
    add(a, "fav_A2")
    a._on_project_saved()  # Ctrl+S: QgsProject.projectSaved
    b = computer(tmp_path, "b", project)
    b.remove_favorite(next(f.id for f in b.get_all_favorites() if f.name == "fav_A1"))
    b._mirror_to_project()
    b._on_project_saved()
    a = computer(tmp_path, "a", project)
    assert names(a) == ["fav_A2"] and first not in [f.id for f in a.get_all_favorites()]


def test_every_favorite_removed_is_said_to_the_other_computers(tmp_path):
    project = Project()
    a = computer(tmp_path, "a", project)
    favorite_id = add(a, "fav_A1")
    a._on_project_saved()
    b = computer(tmp_path, "b", project)
    a.remove_favorite(favorite_id)
    a._mirror_to_project()
    a._on_project_saved()
    assert project.favorites() == []
    b = computer(tmp_path, "b", project)
    assert names(b) == []


def test_the_same_favorite_keeps_its_id_from_computer_to_computer(tmp_path):
    project = Project()
    a = computer(tmp_path, "a", project)
    favorite_id = add(a, "fav_A1")
    b = computer(tmp_path, "b", project)
    assert [f.id for f in b.get_all_favorites()] == [favorite_id]


def test_opening_an_unchanged_project_leaves_it_clean(tmp_path):
    project = Project()
    a = computer(tmp_path, "a", project)
    add(a, "fav_A1")
    writes = project.writes
    computer(tmp_path, "b", project)
    computer(tmp_path, "a", project)
    assert project.writes == writes


def test_applying_a_favorite_does_not_change_the_project(tmp_path):
    """The usage belongs to each computer: counting a use must not make the project dirty."""
    project = Project()
    a = computer(tmp_path, "a", project)
    favorite_id = add(a, "fav_A1")
    writes = project.writes
    a.mark_favorite_used(favorite_id)
    a._mirror_to_project()
    assert project.writes == writes


def test_a_project_that_never_had_favorites_keeps_no_entry(tmp_path):
    project = Project()
    computer(tmp_path, "a", project)
    assert project.entries == {}


def test_the_backup_of_before_is_merged_once_without_copies(tmp_path):
    """A project saved by an earlier FilterMate carries a backup one session late: merged with the computer's."""
    project = Project()
    a = computer(tmp_path, "a", project)
    add(a, "fav_A1")
    add(a, "fav_A2")
    legacy = {"version": "1.0", "backup_type": "project_file",
              "favorites": [{"id": "old-id", "name": "fav_A1", "expression": "x", "updated_at": "2020-01-01"},
                            {"id": "other-id", "name": "fav_old", "expression": "y"}]}
    project.entries[(project_favorites.SCOPE, project_favorites.KEY)] = json.dumps(legacy)
    a = computer(tmp_path, "a", project)
    assert names(a) == ["fav_A1", "fav_A2", "fav_old"]
    assert json.loads(project.entries[(project_favorites.SCOPE, project_favorites.KEY)])["authoritative"] is True


def test_nothing_is_written_into_a_project_before_it_was_read(tmp_path):
    """The favorites of the project of before must never land in the one being opened."""
    project = Project()
    service = FavoritesService(FavoritesManager())
    service._project = staticmethod(lambda _project: project)
    service._favorites_manager.set_database(str(tmp_path / "a.sqlite"), PROJECT_UUID)
    service.add_favorite("fav", "TRUE")
    service._mirror_to_project()
    assert project.entries == {}


def test_the_menu_actions_still_answer(tmp_path):
    project = Project()
    a = computer(tmp_path, "a", project)
    add(a, "fav_A1")
    assert a.save_to_project_file() is True
    assert a.restore_from_project_file() == 1


def test_a_favorite_made_here_and_not_saved_stays_at_the_next_opening(tmp_path):
    """Review of 2026-11-24: QGIS closed without saving, or a project on a share this computer cannot write; the
    favorites made here were removed at the next opening."""
    on_disk = Project()
    a = computer(tmp_path, "a", on_disk)
    add(a, "fav_A1")
    a._on_project_saved()
    saved = dict(on_disk.entries)
    add(a, "made, not saved")
    reopened = Project(saved)  # the file as it was saved
    a = computer(tmp_path, "a", reopened)
    assert names(a) == ["fav_A1", "made, not saved"]


def test_a_favorite_made_elsewhere_before_the_update_is_not_lost(tmp_path):
    """Review of 2026-11-24 (C3): a favorite of computer B that the file never had is not taken for one removed."""
    project = Project()
    a = computer(tmp_path, "a", project)
    add(a, "fav_A1")
    a._on_project_saved()
    b = computer(tmp_path, "b", project)
    b._favorites_manager.add_favorite(FilterFavorite(name="fav_B2", expression="TRUE"))  # before the update
    b = computer(tmp_path, "b", project)
    assert names(b) == ["fav_A1", "fav_B2"]


def test_a_copy_of_the_project_leaves_the_favorites_of_the_original(tmp_path):
    """Review of 2026-11-24 (C2): a copy opened on the same computer took the rows of the original."""
    original = Project()
    a = computer(tmp_path, "a", original, project_uuid="original-uuid")
    add(a, "fav_A1")
    copy = Project(original.entries)
    c = computer(tmp_path, "a", copy, project_uuid="copy-uuid")
    assert names(c) == ["fav_A1"]
    original_without_entry = Project()  # its file never saved with the favorites
    a = computer(tmp_path, "a", original_without_entry, project_uuid="original-uuid")
    assert names(a) == ["fav_A1"]


def test_nothing_is_written_into_the_next_project_before_it_was_read(tmp_path):
    """Review of 2026-11-24 (C1): set_database comes later than QGIS reading the next project; a change between the
    two wrote the favorites of the first one into it."""
    first, second = Project(), Project()
    current = {"project": first}
    service = FavoritesService(FavoritesManager())
    service._project = staticmethod(lambda _project: current["project"])
    service.set_database(str(tmp_path / "a.sqlite"), PROJECT_UUID)
    add(service, "fav of the first")
    current["project"] = second
    service._forget_synced_project()  # QgsProject.cleared / readProject
    add(service, "made meanwhile")
    assert second.entries == {}


def rows(tmp_path, name):
    """(project id, favorite name) of every favorite in the SQLite of a computer."""
    conn = sqlite3.connect(str(tmp_path / f"{name}.sqlite"))
    try:
        return sorted(conn.execute("SELECT project_uuid, name FROM fm_favorites").fetchall())
    finally:
        conn.close()


def test_a_project_closed_leaves_no_favorite_of_it(tmp_path):
    """2026-11-24, seen by Simon: a project closed (QgsProject.cleared) kept its favorites listed (★ 3 on an empty
    project), and a favorite added then went to the closed project, then into its .qgz at its next opening."""
    project = Project()
    a = computer(tmp_path, "a", project)
    add(a, "fav_A1")
    a._on_project_cleared()  # QgsProject.cleared
    assert names(a) == [] and not a.is_bound
    # no project could be bound (no callback): refused, nothing written under any id
    assert a.add_favorite("made with no project", "TRUE") is None
    assert a.import_global_to_project("any") is None
    assert rows(tmp_path, "a") == [(PROJECT_UUID, "fav_A1")]
    a = computer(tmp_path, "a", project)  # the project opened again
    assert names(a) == ["fav_A1"]


def test_a_favorite_made_after_closing_goes_to_the_project_on_screen(tmp_path):
    """Project > Close, then a favorite made: the service binds the project on screen first (the app's
    ensure_project_bound), and the favorite is that project's, not the closed one's."""
    closed, on_screen = Project(), Project()
    a = computer(tmp_path, "a", closed)
    add(a, "fav_A1")
    a._on_project_cleared()
    other_uuid = "99999999-2222-3333-4444-555555555555"

    def bind():
        a._project = staticmethod(lambda _project: on_screen)
        a.set_database(str(tmp_path / "a.sqlite"), other_uuid)

    a.set_bind_callback(bind)
    assert add(a, "made after closing") is not None
    assert rows(tmp_path, "a") == sorted([(PROJECT_UUID, "fav_A1"), (other_uuid, "made after closing")])
    assert closed.favorites() == ["fav_A1"] and on_screen.favorites() == ["made after closing"]


def test_an_import_while_nothing_can_be_bound_writes_nothing(tmp_path):
    a = computer(tmp_path, "a", Project())
    a._on_project_cleared()
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps({"favorites": [{"name": "imported", "expression": "TRUE"}]}), encoding="utf-8")
    a.set_bind_callback(lambda: None)  # binds nothing
    result = a.import_favorites(str(bundle))
    assert not result.success and rows(tmp_path, "a") == []


def test_the_manager_refuses_a_favorite_with_no_project():
    """FavoritesManager: no row without a project (before, the NOT NULL constraint refused it, by luck)."""
    from core.domain.exceptions import FavoritesNotInitialized
    manager = FavoritesManager()
    manager._initialized = True
    with pytest.raises(FavoritesNotInitialized):
        manager.add_favorite(FilterFavorite(name="x", expression="TRUE"))


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot):
        self.slots.remove(slot)


def test_the_project_no_longer_calls_an_unloaded_service(monkeypatch):
    """FilterMateApp.cleanup → teardown: the project kept calling the service of an unloaded plugin, whose
    favorites_changed reached the widgets of the panel unloaded at the next project closed."""
    import sys
    import types
    project = types.SimpleNamespace(cleared=_Signal(), readProject=_Signal(), projectSaved=_Signal())
    monkeypatch.setattr(sys.modules["qgis.core"], "QgsProject", types.SimpleNamespace(instance=lambda: project))
    service = FavoritesService(FavoritesManager())
    service.set_bind_callback(lambda: None)
    assert [len(signal.slots) for signal in (project.cleared, project.readProject, project.projectSaved)] == [1, 1, 1]
    service.teardown()
    assert [len(signal.slots) for signal in (project.cleared, project.readProject, project.projectSaved)] == [0, 0, 0]
    assert service._bind_project is None
    service.teardown()  # twice: nothing to disconnect, no error
