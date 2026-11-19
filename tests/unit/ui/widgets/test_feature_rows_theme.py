"""The rows of the multiple selection list take the colours of the theme of the panel.

They were black (and blue for a feature the filter of its layer hides) whatever the theme: on the dark list of a
dark theme they could not be read. The methods are taken out of the widget and run on a stand-in, as
tests/test_feature_picker_mouse_compat.py does, so no QWidget is built.
"""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

WANTED = {'_dark_rows', 'font_by_state', 'refresh_row_colours', '_row_state', '_style_row', 'select_all', 'deselect_all'}


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
        'is_layer_valid': lambda layer: True,
        'logger': SimpleNamespace(info=lambda *args: None),
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


@pytest.mark.unit
def test_a_refresh_with_the_same_theme_touches_no_row(rows_class):
    items = [_item(True, True), _item(False, False)]
    lightness = [30]
    picker = rows_class()
    picker._fonts_by_theme = {}
    picker.list_widgets = {'layer': _list(items)}
    picker.backgroundRole = lambda: 'window'
    picker.palette = lambda: SimpleNamespace(color=lambda role: SimpleNamespace(lightness=lambda: lightness[0]))
    assert picker.refresh_row_colours() == 2          # first time: the rows take the dark colours
    assert items[0].store[9] == ('brush', rows_class.ROW_COLOURS[True][0])
    items[0].store[9] = 'untouched'
    assert picker.refresh_row_colours() == 0          # called again by another path, same theme
    assert items[0].store[9] == 'untouched'
    lightness[0] = 240
    assert picker.refresh_row_colours() == 2          # the theme changed
    assert items[0].store[9] == ('brush', '#000000')
    assert items[1].store[9] == ('brush', '#0000FF')


@pytest.mark.unit
def test_the_palette_answer_is_kept_too(rows_class):
    asked = []
    picker = rows_class()
    picker._fonts_by_theme = {}
    picker.backgroundRole = lambda: 'window'
    picker.palette = lambda: SimpleNamespace(
        color=lambda role: SimpleNamespace(lightness=lambda: asked.append(1) or 30))
    for _ in range(100):   # thousands of rows must not walk up the parents each
        assert picker.font_by_state['checked'][1] == rows_class.ROW_COLOURS[True][0]
    assert len(asked) == 1


class _Row:
    """A row of the list: its check state, and what setData wrote in it."""

    def __init__(self, checked, in_subset):
        self.state = 2 if checked else 0
        self.store = {4: 'True' if in_subset else 'False'}

    def checkState(self):
        return self.state

    def setCheckState(self, state):
        self.state = state

    def data(self, role):
        return self.store.get(role)

    def setData(self, role, value):
        self.store[role] = value


def _selecting_picker(rows_class, rows):
    class Picker(rows_class):
        def __init__(self):
            self._fonts_by_theme = {}
            self.layer = SimpleNamespace(id=lambda: 'layer')
            self.list_widgets = {'layer': SimpleNamespace(
                count=lambda: len(rows), item=lambda row: rows[row], isTruncated=lambda: False,
                getSearchText=lambda: '', setSelectedFeaturesList=lambda fids: None)}
            self.emitted = []

        def _dark_rows(self):
            return False

        def _emit_checked_items_update(self, force_emit=False):
            self.emitted.append(force_emit)
    return Picker()


@pytest.mark.unit
def test_select_all_makes_the_ticked_rows_bold(rows_class):
    rows = [_Row(False, True), _Row(False, False), _Row(True, True)]
    picker = _selecting_picker(rows_class, rows)
    picker.select_all('Select All')
    assert [row.state for row in rows] == [2, 2, 2]
    assert [row.store[6].weight for row in rows[:2]] == ['bold', 'bold']     # they were not bold before
    assert rows[0].store[9] == ('brush', '#000000') and rows[1].store[9] == ('brush', '#0000FF')
    assert 6 not in rows[2].store or rows[2].store[6].weight == 'bold'
    assert picker.emitted == [False]


@pytest.mark.unit
def test_select_all_of_the_subset_leaves_the_other_rows_alone(rows_class):
    rows = [_Row(False, True), _Row(False, False)]
    picker = _selecting_picker(rows_class, rows)
    picker.select_all('Select All (subset)')
    assert [row.state for row in rows] == [2, 0]
    assert rows[0].store[6].weight == 'bold' and 6 not in rows[1].store
    picker.select_all('Select All (non subset)')
    assert rows[1].state == 2 and rows[1].store[6].weight == 'bold'


@pytest.mark.unit
def test_deselect_all_takes_the_bold_away(rows_class):
    rows = [_Row(True, True), _Row(True, False)]
    picker = _selecting_picker(rows_class, rows)
    picker.deselect_all('De-select All')
    assert [row.state for row in rows] == [0, 0]
    assert [row.store[6].weight for row in rows] == ['medium', 'medium']
    assert rows[1].store[9] == ('brush', '#0000FF')
    assert picker.emitted == [True]


@pytest.mark.unit
def test_the_state_of_a_row_names_its_look(rows_class):
    assert rows_class._row_state(_Row(True, True)) == 'checked'
    assert rows_class._row_state(_Row(False, True)) == 'unChecked'
    assert rows_class._row_state(_Row(True, False)) == 'checkedFiltered'
    assert rows_class._row_state(_Row(False, False)) == 'unCheckedFiltered'
