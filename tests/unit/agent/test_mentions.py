# -*- coding: utf-8 -*-
"""The rows "@" offers for the layers (core/agent/mentions.py): one layer of its name writes it, homonyms write ids.
"""
import pytest

from core.agent.mentions import mention_rows

pytestmark = pytest.mark.unit


def test_a_single_name_is_written_as_is():
    assert mention_rows([("communes_1a2b", "communes", "Villes")]) == [("communes", "communes")]


def test_homonyms_are_shown_with_their_group_and_write_their_id():
    rows = mention_rows([("id_first", "communes", "Est"), ("id_second", "communes", "Ouest")])
    assert rows == [("communes (Est)", "id_first"), ("communes (Ouest)", "id_second")]


def test_homonyms_without_a_group_fall_back_to_the_end_of_the_id():
    rows = mention_rows([("communes_aaaa11", "communes", ""), ("communes_bbbb22", "communes", "")])
    assert [label for label, _insert in rows] == ["communes (…aaaa11)", "communes (…bbbb22)"]
    assert [insert for _label, insert in rows] == ["communes_aaaa11", "communes_bbbb22"]


def test_nameless_layers_stay_out_and_mixed_rows_sort_by_label():
    rows = mention_rows([("id_z", "zoos", ""), ("id_x", "", ""), ("id_a", "alles", "")])
    assert rows == [("alles", "alles"), ("zoos", "zoos")]
