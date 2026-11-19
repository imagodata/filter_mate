"""The rows of the multiple selection list take the colours of the theme of the panel.

They were black (and blue for a feature the filter of its layer hides) whatever the theme: on the dark list of a
dark theme they could not be read. The methods are taken out of the widget and run on a stand-in, as
tests/test_feature_picker_mouse_compat.py does, so no QWidget is built.
"""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

WANTED = {'_dark_rows', 'font_by_state', 'refresh_row_colours'}


class _Font:
    Weight = SimpleNamespace(Medium='medium', Bold='bold')

    def __init__(self, family, size, weight):
        self.family, self.size, self.weight = family, size, weight


@pytest.fixture(scope='module')
def rows_class():
    path = Path(__file__).resolve().parents[4] / 'ui/widgets/custom_widgets.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    widget = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                  and node.name == 'QgsCheckableComboBoxFeaturesListPickerWidget')
    body = [node for node in widget.body
            if (isinstance(node, ast.FunctionDef) and node.name in WANTED)
            or (isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') in ('ROW_COLOURS', '_dark'))]
    assert {getattr(node, 'name', None) or node.targets[0].id for node in body} == WANTED | {'ROW_COLOURS', '_dark'}
    module = ast.Module(body=[ast.ClassDef(name='Rows', bases=[], keywords=[], body=body, decorator_list=[])],
                        type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        'QColor': lambda colour: colour,
        'QFont': _Font,
        'QBrush': lambda colour: ('brush', colour),
        'Qt': SimpleNamespace(CheckState=SimpleNamespace(Checked=2, Unchecked=0)),
    }
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace['Rows']


def _picker(rows_class, dark, lists=None):
    class Picker(rows_class):
        def __init__(self):
            self._fonts_by_theme = {}
            self.list_widgets = lists or {}
            self.dark = dark

        def _dark_rows(self):
            return self.dark
    return Picker()


def _item(checked, in_subset):
    data = {4: 'True' if in_subset else 'False'}
    return SimpleNamespace(checkState=lambda: 2 if checked else 0, data=lambda role: data.get(role),
                           setData=lambda role, value: data.__setitem__(role, value), store=data)


def _list(items):
    return SimpleNamespace(count=lambda: len(items), item=lambda row: items[row])


@pytest.mark.unit
def test_light_rows_keep_their_colours(rows_class):
    fonts = _picker(rows_class, dark=False).font_by_state
    assert fonts['unChecked'][1] == fonts['checked'][1] == '#000000'
    assert fonts['unCheckedFiltered'][1] == fonts['checkedFiltered'][1] == '#0000FF'
    assert fonts['checked'][0].weight == 'bold' and fonts['unChecked'][0].weight == 'medium'


@pytest.mark.unit
def test_dark_rows_are_light_on_the_dark_list(rows_class):
    fonts = _picker(rows_class, dark=True).font_by_state
    text, hidden = fonts['checked'][1], fonts['checkedFiltered'][1]
    assert text == fonts['unChecked'][1] and hidden == fonts['unCheckedFiltered'][1]
    for colour in (text, hidden):   # light enough to be read on a dark list
        red, green, blue = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
        assert 0.299 * red + 0.587 * green + 0.114 * blue > 150
    assert text != hidden


@pytest.mark.unit
def test_the_fonts_of_a_theme_are_built_once(rows_class):
    picker = _picker(rows_class, dark=True)
    assert picker.font_by_state is picker.font_by_state
    picker.dark = False
    assert picker.font_by_state['checked'][1] == '#000000'


@pytest.mark.unit
def test_listed_rows_follow_a_change_of_theme(rows_class):
    items = [_item(True, True), _item(False, True), _item(True, False), _item(False, False)]

    def gone():
        raise RuntimeError('wrapped C/C++ object has been deleted')
    picker = _picker(rows_class, dark=False, lists={'gone': SimpleNamespace(count=gone), 'layer': _list(items)})
    assert picker.refresh_row_colours() == 4
    assert [item.store[9] for item in items] == [('brush', '#000000'), ('brush', '#000000'),
                                                 ('brush', '#0000FF'), ('brush', '#0000FF')]
    picker.dark = True
    assert picker.refresh_row_colours() == 4
    dark = picker.font_by_state
    assert [item.store[9] for item in items] == [('brush', dark['checked'][1]), ('brush', dark['unChecked'][1]),
                                                 ('brush', dark['checkedFiltered'][1]),
                                                 ('brush', dark['unCheckedFiltered'][1])]
    assert items[0].store[9] != ('brush', '#000000')


@pytest.mark.unit
def test_without_a_stylesheet_the_palette_says_the_theme(rows_class):
    def picker(lightness):
        instance = rows_class()
        instance.backgroundRole = lambda: 'window'
        instance.palette = lambda: SimpleNamespace(color=lambda role: SimpleNamespace(lightness=lambda: lightness))
        return instance
    # the styles package is not importable from the stand-in: the stylesheet says nothing, the palette decides
    assert picker(30)._dark_rows() is True
    assert picker(240)._dark_rows() is False


@pytest.mark.unit
def test_the_theme_is_read_once_until_it_changes(rows_class, monkeypatch):
    import sys
    import types
    asked = []

    def stylesheet_is_dark(widget):
        asked.append(widget)
        return answers[0]
    answers = [True]
    # the relative import of the stand-in resolves to nothing: give it the module it asks for
    module = types.ModuleType('mockup_design')
    module.stylesheet_is_dark = stylesheet_is_dark
    real_import = __builtins__['__import__'] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 2 and name == 'styles.mockup_design':
            return module
        return real_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr('builtins.__import__', fake_import)
    picker = rows_class()
    picker._fonts_by_theme = {}
    picker.list_widgets = {}
    for _ in range(50):   # a list filled row by row
        assert picker.font_by_state['checked'][1] == rows_class.ROW_COLOURS[True][0]
    assert len(asked) == 1
    answers[0] = False
    assert picker.font_by_state['checked'][1] == rows_class.ROW_COLOURS[True][0]   # not asked again by itself
    picker.refresh_row_colours()   # a change of theme
    assert picker.font_by_state['checked'][1] == '#000000'
    assert len(asked) == 2
