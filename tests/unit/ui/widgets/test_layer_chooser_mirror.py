# -*- coding: utf-8 -*-
"""The second chooser of the current layer, at the top of EXPLORING away from FILTERING: what it follows."""
import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "ui" / "widgets" / "layer_chooser_mirror.py"
_spec = importlib.util.spec_from_file_location("fm_layer_chooser_mirror_test", _PATH)
mirror = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mirror)


def test_it_shows_the_row_of_the_first_chooser():
    assert mirror.next_index(shown=0, source=2, list_open=False) == 2
    assert mirror.next_index(shown=3, source=-1, list_open=False) == -1  # no layer left: none shown


def test_nothing_to_do_when_it_already_shows_it():
    assert mirror.next_index(shown=2, source=2, list_open=False) is None


def test_the_row_under_the_pointer_does_not_move_while_the_list_is_open():
    assert mirror.next_index(shown=0, source=2, list_open=True) is None


def test_the_module_needs_no_qt_until_a_chooser_is_made():
    assert mirror._CLASS is None and mirror.FOLLOW_MS >= 200
