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
    assert "<img" not in shown and '<a href="http://evil">x' not in shown
    assert "&lt;img" in shown and "&amp;" in shown and "&quot;q&quot;" in shown


def test_marks_become_tags():
    shown = md.answer_html("Les **routes** et *les* `rues`, _italique_")
    assert "<b>routes</b>" in shown and "<i>les</i>" in shown and "<i>italique</i>" in shown
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


def test_a_web_link_keeps_its_label_and_escapes_its_address():
    shown = md.answer_html("Voir [la page](https://example.org/p?a=1&b=2)")
    assert 'href="https://example.org/p?a=1&amp;b=2"' in shown and '>la page</a>' in shown
    assert 'text-decoration: underline' in shown


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


@pytest.mark.parametrize("line", ["*.shp **ok** " * 500, "*b* " * 900 + "**a " * 750, "*a " * 4000, "[" * 12000,
                                  "**a** " * 2000, "_x_ " * 3000])
def test_a_hostile_line_is_drawn_fast_and_whole(line):
    import time
    start = time.perf_counter()
    shown = md.answer_html(line, ["communes"])  # never a RecursionError: marks inside marks stop at MAX_DEPTH
    assert time.perf_counter() - start < 1.0 and shown


def test_a_mark_inside_a_mark_inside_a_mark_is_plain():
    shown = md.answer_html("**gras _italique *encore*_**")
    assert "<b>" in shown and "<i>" in shown and shown.count("<i>") == 1


def test_a_list_with_blank_lines_is_numbered_on():
    shown = md.answer_html("1. **A**\n\n   texte\n\n2. **B**\n\n3. C")
    assert shown.count("<ol") == 1 and shown.count("<li>") == 3 and ">texte</p>" in shown


def test_a_numbered_item_alone_keeps_its_number():
    assert 'start="3"' in md.answer_html("3. x")


def test_four_columns_remain_a_table_when_space_is_available():
    shown = md.answer_html("| a | b | c | d |\n|---|---|---|---|\n| 1 | 2 | 3 | 4 |")
    assert shown.count('<table') == 1 and shown.count('<th') == 4 and shown.count('<td') == 4


def test_a_cell_past_the_header_is_kept():
    shown = md.answer_html("| a | b |\n|---|---|\n| 1 | 2 | 3 |")
    assert ">3</td>" in shown


def test_dunder_names_stay_as_they_are():
    shown = md.answer_html("la méthode __init__ et le __main__")
    assert "<b>" not in shown and "__init__" in shown


def test_a_rule_is_drawn():
    shown = md.answer_html("a\n\n---\n\nb")
    assert "<hr/>" in shown and ">a<" in shown and ">b<" in shown


def test_two_layers_of_one_name_link_the_first():
    shown = md.answer_html("routes", ["routes", "routes"])
    assert 'href="layer:0"' in shown


def test_stable_layer_links_ignore_the_position_in_the_tree_and_keep_case():
    layers = [md.LayerReference('rivers_id', 'Rivières', 'Données / Hydrographie')]
    shown = md.answer_html('Les RIVIÈRES et `Rivières`.', layers=layers)
    assert shown.count('href="layer:id/rivers_id"') == 2 and '>RIVIÈRES</a>' in shown
    assert md.layer_reference('layer:id/rivers_id', list(reversed(layers))).layer_id == 'rivers_id'
    assert md.layer_reference('layer:id/removed', layers) is None


def test_duplicate_names_need_an_explicit_layer_id():
    layers = [md.LayerReference('roads_a', 'routes', 'A'), md.LayerReference('roads_b', 'routes', 'B')]
    shown = md.answer_html('Les routes : [couche B](layer:roads_b). [Ambigu](layer:routes)', layers=layers)
    assert shown.count('<a ') == 1 and 'href="layer:id/roads_b"' in shown
    assert md.layer_reference('layer:routes', layers) is None


def test_explicit_named_links_and_quoted_short_names_are_supported():
    layers = [md.LayerReference('points_id', 'A'), md.LayerReference('cities_id', 'Communes')]
    shown = md.answer_html('A et `A`, [les villes](layer:Communes)', layers=layers)
    assert shown.count('<a ') == 2 and 'href="layer:id/points_id"' in shown
    assert 'href="layer:id/cities_id"' in shown


def test_a_layer_id_and_its_displayed_name_are_escaped_independently():
    layer = md.LayerReference('id/?"', 'Routes <img> & voies')
    shown = md.answer_html(layer.name, layers=[layer])
    assert '<img>' not in shown and 'href="layer:id/id%2F%3F%22"' in shown
    assert md.layer_reference('layer:id/id%2F%3F%22', [layer]) == layer


@pytest.mark.parametrize('url', ['file:///tmp/data.gpkg', 'javascript:alert(1)', 'data:text/html,test',
                                'mailto:user@example.org', 'qgis://run/code', 'https://',
                                'https://user:password@example.org', 'https://host:wrong',
                                'https://host/\nnext', 'https://host/\\data', 'https://[bad'])
def test_only_web_urls_can_be_opened(url):
    assert md.web_url(url) == ''
    if not any(char.isspace() for char in url):
        assert '<a ' not in md.answer_html('[open](' + url + ')')


def test_plain_web_urls_do_not_link_layer_names_inside_their_address():
    shown = md.answer_html('Voir https://example.org/communes?q=1&b=2, puis communes.', ['communes'])
    assert shown.count('<a ') == 2 and 'href="https://example.org/communes?q=1&amp;b=2"' in shown
    assert shown.count('href="layer:0"') == 1 and '</a>, puis' in shown


def test_url_parentheses_and_trailing_sentence_punctuation():
    shown = md.answer_html('(https://example.org/place_(city)).')
    assert 'href="https://example.org/place_(city)"' in shown and '</a>).' in shown


def test_a_long_url_with_unbalanced_brackets_is_linear():
    import time
    start = time.perf_counter()
    shown = md.answer_html('https://example.org/' + ')' * 100_000)
    assert time.perf_counter() - start < 1.0 and shown


def test_unicode_case_matching_does_not_fail_for_turkish_names():
    shown = md.answer_html('İSTANBUL et istanbul', layers=[md.LayerReference('city_id', 'İstanbul')])
    assert shown.count('href="layer:id/city_id"') == 2


def test_registered_output_files_and_folders_are_clickable():
    files = [md.FileReference('/chosen/layouts/map.pdf', 'layouts/map.pdf', aliases=('map.pdf',)),
             md.FileReference('/chosen/layouts', 'layouts', True)]
    shown = md.answer_html('map.pdf, `layouts/map.pdf`, [PDF](layouts/map.pdf), [dossier](folder:layouts)', files=files)
    assert shown.count('href="' + md.output_href(files[0].path) + '"') == 3
    assert md.output_href(files[1].path) in shown
    assert md.file_reference('file:///chosen/layouts/map.pdf', files) == files[0]
    assert md.file_reference('file:///etc/passwd', files) is None


def test_duplicate_output_names_need_their_relative_path():
    files = [md.FileReference('/chosen/charts/map.pdf', 'charts/map.pdf', aliases=('map.pdf',)),
             md.FileReference('/chosen/layouts/map.pdf', 'layouts/map.pdf', aliases=('map.pdf',))]
    shown = md.answer_html('map.pdf et charts/map.pdf', files=files)
    assert shown.count('<a ') == 1 and md.output_href(files[0].path) in shown
    assert md.file_reference('map.pdf', files) is None


def test_output_paths_with_spaces_accents_and_quotes_are_escaped():
    file = md.FileReference('/chosen/été & "carte".pdf', 'été & "carte".pdf')
    shown = md.answer_html(file.name, files=[file])
    assert md.output_href(file.path) in shown and '&quot;carte&quot;' in shown
    assert md.file_reference(md.output_href(file.path), [file]) == file


def test_explicit_links_keep_balanced_parentheses_in_their_url():
    shown = md.answer_html('[page](https://example.org/(place_(city))/map) puis **bilan**')
    assert 'href="https://example.org/(place_(city))/map"' in shown
    assert '>page</a> puis <b>bilan</b>' in shown


def test_angle_delimited_local_links_support_spaces_in_known_output_names():
    file = md.FileReference('/chosen/carte été.pdf', 'carte été.pdf')
    shown = md.answer_html('[La carte](</chosen/carte été.pdf>)', files=[file])
    assert md.output_href(file.path) in shown and '>La carte</a>' in shown


def test_network_file_links_resolve_only_to_registered_outputs():
    file = md.FileReference('//server/share/map.pdf', 'map.pdf')
    assert md.file_reference('file://server/share/map.pdf', [file]) == file
    assert md.file_reference('file://other/share/map.pdf', [file]) is None


def test_table_outer_pipes_are_optional_and_alignment_is_kept():
    shown = md.answer_html('Nom | Type | Nombre\n:--- | :---: | ---:\nCommunes | vector | 42', colors=COLORS)
    assert '<table' in shown and '<th align="center"' in shown
    assert '<td align="right"' in shown and '>42</td>' in shown


def test_table_rows_can_omit_delimiters_and_end_at_another_block():
    shown = md.answer_html('| Nom | Valeur |\n|---|---|\nCommunes\n# Suite\nFin')
    assert shown.count('<td') == 2 and '>Communes</td>' in shown and '<b>Suite</b>' in shown


def test_tables_inside_lists_keep_their_structure():
    shown = md.answer_html('- Nom | Valeur\n  ---|---\n  Communes | 42\n- Suite')
    assert shown.count('<ul') == 1 and shown.count('<table') == 1 and '>42</td>' in shown
    assert '<li>Suite</li>' in shown


def test_table_pipes_in_code_and_escaped_pipes_are_cell_contents():
    shown = md.answer_html('| Expression | Résultat |\n|---|---|\n| `a | b` | un \\| deux |')
    assert shown.count('<th') == 2 and shown.count('<td') == 2
    assert 'a | b' in shown and 'un | deux' in shown


def test_a_mismatched_table_header_is_not_silently_reinterpreted():
    shown = md.answer_html('Un | Deux | Trois\n--- | ---\n1 | 2 | 3')
    assert '<table' not in shown and 'Trois' in shown


def test_a_table_stacks_records_on_a_narrow_viewport_and_keeps_empty_fields():
    text = '| Nom | Type | Nombre | Source |\n|---|---|---:|---|\n| A | vector | 42 | X |\n| B | raster | | Y |'
    narrow = md.answer_html(text, width=260)
    wide = md.answer_html(text, width=720)
    assert narrow.count('<table') == 2 and narrow.count('<th') == 8
    assert wide.count('<table') == 1 and wide.count('<th') == 4
    assert '>Nombre</th>' in narrow and '>Y</td>' in narrow and '>42</td>' in narrow


def test_table_headers_and_alternating_rows_take_the_theme_colors():
    shown = md.answer_html('A | B\n---|---\n1|2\n3|4', colors={**COLORS, 'table_header': '#123456', 'table_alt': '#abcdef'})
    assert 'bgcolor="#123456"' in shown and 'bgcolor="#abcdef"' in shown


def test_table_cells_keep_output_links_when_there_are_no_project_layers():
    file = md.FileReference('/chosen/map.pdf', 'map.pdf')
    shown = md.answer_html('Fichier | Valeur\n---|---\nmap.pdf | 1', files=[file], width=500)
    assert md.output_href(file.path) in shown and 'href="layer:' not in shown


def test_table_layer_links_keep_stable_ids_and_cells_wrap_long_tokens():
    layer = md.LayerReference('city_id', 'Communes')
    shown = md.answer_html('Couche | Clé\n---|---\nCommunes | ' + 'abcdef' * 20, layers=[layer], width=300)
    assert 'href="layer:id/city_id"' in shown and '\u200b' in shown
    assert 'abcdef' * 20 in shown.replace('\u200b', '')


def test_nested_ordered_and_unordered_lists_have_distinct_levels():
    shown = md.answer_html('1. Préparer\n   - Routes\n     - Principales\n   - Communes\n2. Exporter')
    assert shown.count('<ol') == 1 and shown.count('<ul') == 2 and shown.count('<li>') == 5
    assert '-qt-list-indent: 3' in shown and '>Principales</li>' in shown


def test_task_lists_render_as_text_without_interactive_controls():
    shown = md.answer_html('- [x] **Prêt**\n- [ ] À faire')
    assert '☑ <b>Prêt</b>' in shown and '☐ À faire' in shown and '<input' not in shown


def test_blockquotes_contain_formatted_paragraphs_and_lists():
    shown = md.answer_html('> **Attention**\n>\n> - Première\n> - Deuxième\n\nSuite')
    assert '<blockquote' in shown and '<b>Attention</b>' in shown and '<ul' in shown
    assert '</blockquote>' in shown and '>Suite</p>' in shown


def test_code_fences_only_close_with_the_matching_kind_and_length():
    shown = md.answer_html('````python\nx = "```"\n~~~\n```\n````\nFin')
    assert '<pre' in shown and 'x = &quot;```&quot;\n~~~\n```' in shown and '>Fin</p>' in shown


def test_unfinished_fences_remain_visible_while_the_answer_streams():
    shown = md.answer_html('```sql\nSELECT 1\nWHERE x < 2')
    assert 'SELECT 1\nWHERE x &lt; 2' in shown and shown.endswith('</pre>')


def test_inline_code_accepts_backticks_inside_a_longer_delimiter():
    shown = md.answer_html('Exemple : `` `nom` **brut** ``.')
    assert '`nom` **brut**' in shown and '<b>' not in shown


def test_link_labels_support_formatting_without_nested_auto_links():
    shown = md.answer_html('[**Communes**](https://example.org)', ['Communes'])
    assert '<b>Communes</b></a>' in shown and shown.count('<a ') == 1


def test_link_labels_can_contain_inline_code_and_code_cannot_contain_live_links():
    shown = md.answer_html('[`Communes`](https://example.org)', ['Communes'])
    assert shown.count('<a ') == 1 and 'font-family: monospace' in shown and '>Communes</span></a>' in shown
    assert '<a ' not in md.answer_html('`[page](https://example.org)`')


def test_strikethrough_and_heading_levels_have_their_own_presentation():
    shown = md.answer_html('# Titre\n### Détail\n~~ancien~~ **nouveau**')
    assert '<s>ancien</s>' in shown and 'font-size: 18px' in shown and 'font-size: 14px' in shown


def test_html_stays_escaped_in_all_new_block_types():
    shown = md.answer_html('> <img src="http://evil/quote">\n\nA|B\n---|---\n<script>x</script>|<img src="file:///x">\n\n'
                           '```<img\n<a href="javascript:evil">x</a>\n```')
    assert '<img' not in shown and '<script' not in shown and '<a href="javascript' not in shown
    assert '&lt;img' in shown and '&lt;script' in shown


def test_deep_quote_and_list_nesting_is_bounded_without_losing_the_text():
    shown = md.answer_html('> ' * 200 + 'Fin\n\n' + '\n'.join('  ' * index + '- item' for index in range(30)))
    assert 'Fin' in shown and shown.count('<blockquote') <= md.MAX_BLOCK_DEPTH
    assert shown.count('<ul') <= md.MAX_BLOCK_DEPTH


def test_long_table_cells_and_many_empty_lines_do_not_block_rendering():
    import time
    start = time.perf_counter()
    shown = md.answer_html('Nom|Valeur\n---|---\nA|' + 'x' * 150_000 + '\n' * 10_000 + 'Fin')
    assert time.perf_counter() - start < 1.0 and 'Fin' in shown
