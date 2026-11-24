# -*- coding: utf-8 -*-
"""Order of the favorites list: name, last used, most used."""
import importlib.util
import pathlib
from types import SimpleNamespace

_PATH = pathlib.Path(__file__).resolve().parents[4] / "ui" / "dialogs" / "favorite_order.py"
_spec = importlib.util.spec_from_file_location("_favorite_order_under_test", str(_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sorted_favorites = _mod.sorted_favorites


def _fav(name, uses=0, last=None):
    return SimpleNamespace(name=name, use_count=uses, last_used_at=last)


def _names(favorites):
    return [f.name for f in favorites]


def test_by_name_ignores_the_case():
    assert _names(sorted_favorites([_fav("b"), _fav("A"), _fav("c")], "name")) == ["A", "b", "c"]


def test_last_used_is_most_recent_first_and_never_used_last():
    favorites = [
        _fav("never"), _fav("old", last="2026-01-01T10:00:00"), _fav("new", last="2026-11-01T10:00:00"),
        _fav("also never", uses=0),
    ]
    assert _names(sorted_favorites(favorites, "last_used")) == ["new", "old", "also never", "never"]


def test_last_used_ties_by_name():
    moment = "2026-11-01T10:00:00"
    favorites = [_fav("b", last=moment), _fav("a", last=moment)]
    assert _names(sorted_favorites(favorites, "last_used")) == ["a", "b"]


def test_most_used_is_highest_first_ties_by_name():
    favorites = [_fav("b", 2), _fav("c", 9), _fav("a", 2), _fav("z", 0)]
    assert _names(sorted_favorites(favorites, "most_used")) == ["c", "a", "b", "z"]


def test_a_project_favorite_stays_before_a_global_one_of_the_same_name():
    project, global_ = _fav("Roads"), _fav("Roads")
    assert sorted_favorites([project, global_], "name") == [project, global_]


def test_an_unknown_key_sorts_by_name():
    assert _names(sorted_favorites([_fav("b"), _fav("a")], "nope")) == ["a", "b"]
