# -*- coding: utf-8 -*-
"""The answers of the agent drawn from their Markdown (ui/widgets/agent_markdown.py, 2026-11-24): every character a
model wrote is escaped, only its marks become tags of our own, the names of the layers become links ``layer:<rank>``.

Pure Python: the module is loaded from its file, without the package (which needs Qt).
"""
import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "ui" / "widgets" / "agent_markdown.py"
_SPEC = importlib.util.spec_from_file_location("fm_agent_markdown_test", _PATH)
md = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(md)

COLORS = {"accent": "#0066cc", "code_bg": "#eeeeee", "rule": "#cccccc"}


def test_everything_the_model_wrote_is_escaped():
    shown = md.answer_html('<img src="file:///x.png"> <a href="http://evil">x</a> & "q"')
    assert "<img" not in shown and "<a " not in shown
    assert "&lt;img" in shown and "&amp;" in shown and "&quot;q&quot;" in shown


def test_marks_become_tags():
    shown = md.answer_html("Les **routes** et *les* `rues`, __gras__ _italique_")
    assert "<b>routes</b>" in shown and "<i>les</i>" in shown and "<b>gras</b>" in shown and "<i>italique</i>" in shown
    assert "font-family: monospace" in shown and ">rues<" in shown and "*" not in shown and "`" not in shown


def test_nothing_inside_code_is_a_mark():
    shown = md.answer_html("`**a** < b`")
    assert "<b>" not in shown and "**a** &lt; b" in shown


def test_a_snake_case_name_is_not_italic():
    shown = md.answer_html("le champ nom_de_la_rue et code_postal")
    assert "<i>" not in shown and "nom_de_la_rue" in shown


def test_lists_headings_and_paragraphs():
    shown = md.answer_html("## Bilan\nUn\ndeux\n\n- a\n- b\n\n1. x\n2. y")
    assert "<b>Bilan</b>" in shown and "Un<br/>deux" in shown
    assert "<ul" in shown and "<li>a</li><li>b</li>" in shown and "<ol" in shown and "<li>x</li><li>y</li>" in shown


def test_a_table_with_a_short_row():
    shown = md.answer_html("| Nom | Pop |\n|---|---:|\n| Toulouse | 500 000 |\n| Colomiers |", colors=COLORS)
    assert "<table" in shown and shown.count("<th") == 2 and shown.count("<td") == 4
    assert ">Toulouse</td>" in shown and "#cccccc" in shown and "|" not in shown


def test_a_pipe_in_a_sentence_is_no_table():
    shown = md.answer_html("a | b\nc | d")
    assert "<table" not in shown and "a | b" in shown


def test_fenced_code_keeps_its_lines_escaped():
    shown = md.answer_html("```sql\nSELECT * FROM t\nWHERE a < 3\n```\nFin")
    assert "white-space: pre-wrap" in shown and "SELECT * FROM t\nWHERE a &lt; 3" in shown and "Fin" in shown
    assert "```" not in shown


def test_a_link_shows_its_address_and_is_never_clicked_through():
    shown = md.answer_html("Voir [la page](https://example.org/p?a=1&b=2)")
    assert "<a " not in shown and "la page (https://example.org/p?a=1&amp;b=2)" in shown


def test_layer_names_link_whole_words_only():
    names = ["communes", "routes", "a"]
    shown = md.answer_html("Les communes, pas intercommunes ; routes et `routes`. a b", names, COLORS)
    assert shown.count('href="layer:0"') == 1 and shown.count('href="layer:1"') == 2
    assert 'href="layer:2"' not in shown  # too short to be told from a word
    assert "intercommunes" in shown and "#0066cc" in shown


def test_the_longest_name_wins():
    shown = md.answer_html("routes principales", ["routes", "routes principales"])
    assert shown.count("<a ") == 1 and 'href="layer:1"' in shown


def test_layer_of_link():
    names = ["communes", "routes"]
    assert md.layer_of_link("layer:1", names) == "routes"
    assert md.layer_of_link("layer:9", names) == "" and md.layer_of_link("layer:x", names) == ""
    assert md.layer_of_link("https://evil", names) == ""


def test_long_words_get_their_places_to_wrap_before_escaping():
    shown = md.answer_html("a<b", breakable=lambda text: text.replace("<", "<​"))
    assert "&lt;​b" in shown
