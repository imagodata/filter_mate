# -*- coding: utf-8 -*-
"""The rule that keeps one project copy of a global favorite."""
from types import SimpleNamespace

from core.domain.global_favorite_copy import project_copy_of_global


def _fav(name, expression="TRUE"):
    return SimpleNamespace(name=name, expression=expression)


def test_same_name_and_expression_is_the_copy():
    copy = _fav("Roads")
    assert project_copy_of_global(_fav("Roads"), [_fav("Other"), copy]) is copy


def test_the_global_suffix_is_ignored_like_the_import_does():
    copy = _fav("Roads")
    assert project_copy_of_global(_fav("Roads (Global)"), [copy]) is copy


def test_another_expression_or_name_is_not_a_copy():
    assert project_copy_of_global(_fav("Roads"), [_fav("Roads", "FALSE"), _fav("Rails")]) is None


def test_no_project_favorite_is_no_copy():
    assert project_copy_of_global(_fav("Roads"), []) is None
