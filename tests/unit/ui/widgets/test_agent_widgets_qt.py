# -*- coding: utf-8 -*-
"""
The widgets strip and the thread of the AGENT section, on real Qt widgets (PyQt5, offscreen).

Loaded under a private package with ``qgis.PyQt`` pointing at PyQt5 for the import only (the root conftest mocks Qt
for the other tests). Skipped without PyQt5 (the CI test job has none).
"""
import importlib
import os
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5 import QtCore, QtGui, sip  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PKG = "fm_agent_widgets_qt_test"


def _load():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    qt = {"qgis.PyQt": types.ModuleType("qgis.PyQt"), "qgis.PyQt.QtCore": QtCore, "qgis.PyQt.QtGui": QtGui,
          "qgis.PyQt.QtWidgets": QtWidgets}
    saved = {name: sys.modules.get(name) for name in qt}
    sys.modules.update(qt)  # for the imports only: the modules loaded keep the real Qt classes
    try:
        for name, path in (("", _ROOT), (".core", _ROOT / "core"), (".core.agent", _ROOT / "core" / "agent"),
                           (".ui", _ROOT / "ui"), (".ui.widgets", _ROOT / "ui" / "widgets"),
                           (".ui.styles", _ROOT / "ui" / "styles"), (".ui.layout", _ROOT / "ui" / "layout"),
                           # its __init__ loads the panels of EXPLORING: the histogram alone
                           (".ui.widgets.coverage_panels", _ROOT / "ui" / "widgets" / "coverage_panels")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        modules = [importlib.import_module(f"{_PKG}.{name}")
                   for name in ("ui.widgets.agent_widgets_strip", "ui.widgets.agent_thread", "core.agent.widgets",
                                "ui.layout.action_bar_manager", "ui.widgets.coverage_panels.histogram_widget")]
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return (app, *modules)


_APP, strip_module, thread_module, model, action_bar_module, histogram_module = _load()
Qt = QtCore.Qt


def _run(ms=150):
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec_()


def _quote(name):
    return '"' + name + '"'


def _range(minimum, maximum, **changes):
    widget = model.make([], model.RANGE, "L1", "communes", "", field="f", minimum=minimum, maximum=maximum)
    widget.update(changes)
    return widget


def _moved(widget, **values):
    """The state the card emits once its bounds are moved as ``values`` says, in that order."""
    card = strip_module.WidgetCard(widget)
    emitted = []
    card.changed.connect(emitted.append)
    for name, value in values.items():
        box = getattr(card, name)
        box.setValue({"bottom": box.minimum(), "top": box.maximum()}.get(value, value))
    card.flush()
    card.deleteLater()
    return emitted[-1]


class TestRange:
    def test_the_bound_not_moved_keeps_its_value_and_writes_no_condition(self):
        state = _moved(_range(0.125, 10.006), high=5.0)
        assert (state["low"], state["high"]) == (0.125, 5.0)
        assert model.condition(state, _quote, repr) == '"f" <= 5.0'

    def test_small_numbers_are_not_rounded_to_zero(self):
        state = _moved(_range(0.001, 0.005), high=0.003)
        assert model.condition(state, _quote, repr) == '"f" <= 0.003'

    def test_a_bound_at_an_end_keeps_the_feature_of_that_end(self):
        state = _moved(_range(0.125, 10.006), high="bottom")
        assert model.condition(state, _quote, repr) == '"f" <= 0.125'
        state = _moved(_range(0.125, 10.006), low="top")
        assert model.condition(state, _quote, repr) == '"f" >= 10.006'

    def test_a_bound_dragged_past_the_other_one_takes_it_along(self):
        state = _moved(_range(0.0, 10.0), high=3.0, low=7.0)
        assert (state["low"], state["high"]) == (7.0, 7.0)

    def test_a_bound_saved_rounded_at_an_end_by_5_1_stays_at_the_end(self):
        stored = model.parse(model.dumps([_range(0.125, 0.9, low=0.13)]))[0]  # 3 decimals now: shown 0.130
        assert model.condition(_moved(stored, high=0.5), _quote, repr) == '"f" <= 0.5'

    def test_whole_numbers_for_an_integer_field(self):
        widget = model.make([], model.RANGE, "L1", "communes", "", field="n", minimum=3, maximum=17, integer=True)
        assert model.condition(_moved(widget, low=5), _quote, repr) == '"n" >= 5'


def _shown_card(widget, bars=None, width=380):
    """A card in a holder as wide as a narrow dock, its bars set, laid out."""
    holder = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(holder)
    card = strip_module.WidgetCard(widget, holder)
    layout.addWidget(card)
    layout.addStretch(1)
    holder.resize(width, 400)
    holder.show()
    if bars is not None:
        card.set_bars(bars)
    _run(30)
    return holder, card


def _drop(histogram, start, end):
    """A handle grabbed at abscissa ``start`` of the histogram and dropped at ``end`` (pixels of the widget)."""
    from PyQt5 import QtTest
    y = histogram.height() // 2
    QtTest.QTest.mousePress(histogram, Qt.LeftButton, Qt.NoModifier, QtCore.QPoint(start, y))
    QtTest.QTest.mouseRelease(histogram, Qt.LeftButton, Qt.NoModifier, QtCore.QPoint(end, y))


def _value_at(histogram, x, minimum, maximum, places):
    """The value a handle dropped at ``x`` takes, as the histogram computes it."""
    width = histogram.width() - 12  # the plot keeps 6 px on each side for the handles
    return histogram_module.snap(histogram_module.value_at(x - 6, width, minimum, maximum), places, minimum, maximum)


class TestRangeHistogram:
    BARS = {"counts": [1] * 24, "unknown": [], "outside": 0, "empty": 0}

    def test_a_handle_dropped_moves_the_bound_and_its_box_then_filters_after_the_pause(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"), self.BARS)
        emitted = []
        card.changed.connect(emitted.append)
        histogram = card.histogram
        assert histogram.isVisible()
        target = 6 + int(0.4 * (histogram.width() - 12))
        expected = _value_at(histogram, target, 0.0, 100.0, 2)
        _drop(histogram, 6, target)
        assert card.widget["low"] == expected and card.low.value() == expected and card.widget["high"] == 100.0
        assert emitted == []  # not before the pause
        _run(strip_module.APPLY_DELAY_MS + 100)
        assert len(emitted) == 1 and emitted[0]["low"] == expected
        assert model.condition(emitted[0], _quote, repr) == f'"f" >= {expected!r}'
        holder.deleteLater()

    def test_a_box_moves_its_handle_and_nothing_is_applied_twice(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"), self.BARS)
        emitted = []
        card.changed.connect(emitted.append)
        card.high.setValue(40.0)
        assert card.histogram.range() == (None, 40.0)
        card.low.setValue(60.0)  # past the other one: both bounds on it
        assert card.histogram.range() == (60.0, 60.0)
        _run(strip_module.APPLY_DELAY_MS + 100)
        assert len(emitted) == 1 and (emitted[0]["low"], emitted[0]["high"]) == (60.0, 60.0)
        holder.deleteLater()

    def test_a_handle_dropped_at_an_end_is_the_end_of_the_field_itself(self):
        holder, card = _shown_card(dict(_range(0.125, 10.006, low=5.0, high=6.0), id="w1"), self.BARS)
        histogram = card.histogram
        _drop(histogram, 6 + int(0.5 * (histogram.width() - 12)), 0)  # the low handle to the left end
        _drop(histogram, 6 + int(0.6 * (histogram.width() - 12)), histogram.width())  # the high one to the right end
        state = card.widget
        assert (state["low"], state["high"]) == (0.125, 10.006) and model.condition(state, _quote, repr) == ""
        assert card.low.value() == card.low.minimum()  # shown rounded, the state exact
        holder.deleteLater()

    def test_the_handles_of_an_integer_field_stop_on_whole_numbers(self):
        widget = model.make([], model.RANGE, "L1", "communes", "", field="n", minimum=3, maximum=17, integer=True)
        holder, card = _shown_card(dict(widget, id="w1"), self.BARS)
        histogram = card.histogram
        _drop(histogram, 6, 6 + int(0.37 * (histogram.width() - 12)))
        low = card.widget["low"]
        assert low == int(low) and 3 < low < 17 and model.condition(card.widget, _quote, repr) == f'"n" >= {int(low)}'
        holder.deleteLater()

    def test_without_bars_the_boxes_alone(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"))
        assert not card.histogram.isVisible() and card.low.isVisible()
        card.set_bars(self.BARS)
        assert card.histogram.isVisible()
        card.set_bars(None)  # too many features, a web service: no histogram, no empty frame
        assert not card.histogram.isVisible()
        holder.deleteLater()

    def test_a_handle_held_while_its_card_goes_is_applied(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"), self.BARS)
        emitted = []
        card.changed.connect(emitted.append)
        from PyQt5 import QtTest
        histogram = card.histogram
        y = histogram.height() // 2
        target = 6 + int(0.7 * (histogram.width() - 12))
        QtTest.QTest.mousePress(histogram, Qt.LeftButton, Qt.NoModifier, QtCore.QPoint(target, y))  # not released
        assert card.flush() and emitted[-1]["high"] == _value_at(histogram, target, 0.0, 100.0, 2)
        assert not card.flush()  # once
        holder.deleteLater()

    def test_the_histogram_does_not_widen_the_card_and_keeps_its_height(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"))
        without = (card.minimumSizeHint().width(), card.sizeHint().width())
        card.set_bars(self.BARS)
        _run(30)
        assert (card.minimumSizeHint().width(), card.sizeHint().width()) == without
        assert card.histogram.height() == strip_module.RANGE_HISTOGRAM_HEIGHT
        assert card.histogram.width() > 300  # as wide as the card in a dock of 380 px
        holder.deleteLater()

    def test_the_bars_take_the_accent_of_the_plugin(self, strip):
        strip.set_widgets([dict(_range(0.0, 100.0), id="w1")])
        histogram = strip.cards["w1"].histogram
        palette = importlib.import_module(f"{_PKG}.ui.styles.mockup_design").tokens(False)
        assert histogram._accent is not None and histogram._accent.name() == QtGui.QColor(palette["fm_accent"]).name()

    @pytest.mark.parametrize("minimum, maximum, side", [(0.0234, 0.1234, "high"), (0.0236, 0.1236, "low")])
    def test_a_handle_dropped_near_an_end_shown_as_that_end_is_the_end_itself(self, minimum, maximum, side):
        holder, card = _shown_card(dict(_range(minimum, maximum), id="w1"), self.BARS)
        histogram, box = card.histogram, getattr(card, side)
        places = model.decimals(card.widget)
        right = histogram.width() - 6
        start, target = (6, 8) if side == "low" else (right, right - 2)  # 2 px from the end
        value = _value_at(histogram, target, minimum, maximum, places)
        end = box.minimum() if side == "low" else box.maximum()
        assert value not in (minimum, maximum) and value == end  # the box shows it as its end
        _drop(histogram, start, target)
        assert card.widget[side] == (minimum if side == "low" else maximum)
        assert model.condition(card.widget, _quote, repr) == "" and histogram.range() == (None, None)
        state = card.flush() and card.applied
        assert model.parse(model.dumps([state]))[0] == state  # kept as dropped once saved and read again
        holder.deleteLater()

    def test_a_value_typed_without_enter_is_kept_when_a_handle_is_dropped(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"), self.BARS)
        histogram = card.histogram
        card.low.lineEdit().setText("40")  # typed, Enter not pressed
        target = 6 + int(0.8 * (histogram.width() - 12))
        _drop(histogram, histogram.width() - 6, target)
        assert card.widget["low"] == 40.0 and card.widget["high"] == _value_at(histogram, target, 0.0, 100.0, 2)
        assert histogram.range() == (40.0, card.widget["high"])
        holder.deleteLater()

    def test_a_handle_dropped_past_a_value_typed_drags_it_along(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"), self.BARS)
        histogram = card.histogram
        card.low.lineEdit().setText("80")
        target = 6 + int(0.5 * (histogram.width() - 12))
        _drop(histogram, histogram.width() - 6, target)  # the high handle to 50, under the 80 typed
        assert card.widget["low"] == card.widget["high"] == _value_at(histogram, target, 0.0, 100.0, 2)
        holder.deleteLater()

    def test_the_bars_a_filter_hid_are_hatched_and_what_is_left_out_is_said(self):
        holder, card = _shown_card(dict(_range(0.0, 100.0), id="w1"))
        unknown = [index < 12 for index in range(24)]
        card.set_bars(dict(self.BARS, unknown=unknown, outside=12, empty=3))
        assert card.histogram._unknown == unknown
        assert card.note.isVisible() and card.note.text() == "12 outside the range · 3 without value"
        card.set_bars(self.BARS)
        assert not card.note.isVisible() and card.histogram._unknown == []
        holder.deleteLater()

    def test_hatched_bins_are_drawn(self):
        histogram = histogram_module.RangeHistogramWidget()
        histogram.resize(250, 80)
        histogram.set_histogram([0] * 24, 0.0, 10.0)
        plain = histogram.grab().toImage()
        histogram.set_unknown([True] * 24)
        hatched = histogram.grab().toImage()
        row = 40
        assert any(plain.pixel(x, row) != hatched.pixel(x, row) for x in range(10, 240))
        histogram.deleteLater()

    def test_a_range_with_one_value_has_no_histogram_and_emits_nothing(self, strip):
        widget = dict(_range(0.0, 1.0), id="w1", minimum=5.0, maximum=5.0, low=5.0, high=5.0)
        emitted = []
        strip.changed.connect(emitted.append)
        strip.set_widgets([widget])
        strip.set_widgets([widget, _stat(2)])
        strip.set_widgets([widget])
        _run(strip_module.APPLY_DELAY_MS + 100)
        assert emitted == [] and strip.cards["w1"].histogram is None

    def test_a_card_drawn_again_keeps_its_bars_until_they_are_read(self, strip):
        widget = dict(_range(0.0, 100.0), id="w1")
        strip.set_widgets([widget])
        strip.set_bars("w1", self.BARS)
        strip.set_widgets([widget, _stat(2)])
        assert strip.cards["w1"].bars == self.BARS and not strip.cards["w1"].histogram.isHidden()
        strip.set_widgets([dict(widget, maximum=50.0, high=50.0), _stat(2)])  # other bounds: other bars
        assert strip.cards["w1"].bars is None


def _values(number, chosen=("a",)):
    return {"id": f"w{number}", "kind": model.VALUES, "title": "", "field": f"k{number}", "layer_id": "L1",
            "layer_name": "communes", "base": "", "values": ["a", "b", "c"], "chosen": list(chosen)}


def _stat(number):
    return {"id": f"w{number}", "kind": model.STAT, "title": "", "field": "", "layer_id": "L1",
            "layer_name": "communes", "base": "", "aggregate": "count"}


@pytest.fixture
def strip():
    holder = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(holder)
    widget = strip_module.WidgetsStrip(holder)
    layout.addWidget(widget)
    layout.addStretch(1)
    holder.resize(400, 700)
    holder.show()
    _run()
    yield widget
    holder.deleteLater()


class TestStrip:
    def test_as_high_as_the_cards_drawn_now_up_to_its_maximum(self, strip):
        strip.set_widgets([_values(1)])
        _run()
        one = strip._area.height()
        strip.set_widgets([_values(1), _values(2)])
        _run()
        assert strip._area.height() == strip_module.STRIP_MAX_HEIGHT > one
        strip.set_widgets([_stat(1)])
        _run()
        assert strip._area.height() == strip._inner.sizeHint().height() < one

    def test_a_value_ticked_just_before_a_redraw_is_applied_and_drawn_again(self, strip):
        strip.set_widgets([_values(1)])
        _run()
        emitted = []
        strip.changed.connect(emitted.append)
        strip.cards["w1"].values.item(1).setCheckState(Qt.CheckState.Checked)
        strip.set_widgets([_values(1), _stat(2)])  # read before the tick, as the controller does
        assert [state["chosen"] for state in emitted] == [["a", "b"]]
        card = strip.cards["w1"]
        assert [card.values.item(row).checkState() == Qt.CheckState.Checked for row in range(3)] == [True, True, False]

    def test_a_value_typed_without_enter_is_applied_before_a_redraw(self, strip):
        widget = dict(_range(0.0, 10.0), id="w1")
        strip.set_widgets([widget])
        _run()
        emitted = []
        strip.changed.connect(emitted.append)
        strip.cards["w1"].low.lineEdit().setText("4")  # typed, Enter not pressed
        strip.set_widgets([widget, _stat(2)])
        assert [state["low"] for state in emitted] == [4.0] and strip.cards["w1"].low.value() == 4.0

    def test_a_widget_removed_or_changed_meanwhile_keeps_its_filter(self, strip):
        strip.set_widgets([_values(1), _values(2)])
        _run()
        emitted = []
        strip.changed.connect(emitted.append)
        strip.cards["w1"].values.item(1).setCheckState(Qt.CheckState.Checked)
        strip.set_widgets([_values(2)])  # its ✕ (or an undo) took it out of the project first
        strip.cards["w2"].values.item(1).setCheckState(Qt.CheckState.Checked)
        strip.set_widgets([_values(2, chosen=["c"])])  # an undo brought another state back
        _run(strip_module.APPLY_DELAY_MS + 100)
        assert emitted == [] and strip.cards["w2"].widget["chosen"] == ["c"]

    def test_what_applying_before_a_redraw_answered_is_shown_on_the_new_card(self, strip):
        strip.set_widgets([_values(1)])
        _run()
        strip.changed.connect(lambda state: strip.set_error(state["id"], "Refused by the layer."))
        strip.cards["w1"].values.item(1).setCheckState(Qt.CheckState.Checked)
        strip.set_widgets([_values(1), _stat(2)])
        assert strip.cards["w1"].error.text() == "Refused by the layer."

    def test_an_error_shown_makes_room_for_itself(self, strip):
        strip.set_widgets([_stat(1), dict(_range(0.0, 1.0), id="w2")])
        _run()
        before = strip._area.height()
        strip.set_error("w2", "The layer is being edited: save or discard its edits to filter it. " * 2)
        _run()
        assert strip._area.height() > before and not strip._area.verticalScrollBar().isVisible()

    def test_the_layer_name_in_a_tooltip_is_not_read_as_html(self, strip):
        strip.set_widgets([dict(_values(1), layer_name='<img src="file:///x.png">')])
        tooltip = strip.cards["w1"].title.toolTip()
        assert "<img" not in tooltip and "&lt;img" in tooltip


@pytest.fixture
def thread():
    from_tokens = importlib.import_module(f"{_PKG}.ui.styles.mockup_design").tokens
    widget = thread_module.AgentThread(lambda: from_tokens(False), lambda: False, lambda: None)
    widget.resize(400, 600)
    widget.show()
    yield widget
    if not sip.isdeleted(widget):
        widget.deleteLater()


class TestThread:
    def test_fragments_are_drawn_together_and_the_end_at_once(self, thread):
        text = "Les routes **roads** dont `type` vaut primary.\n- un\n- deux\n" * 20
        thread.add_text(text[:1])
        label = thread._answer.widget
        drawn = []
        set_text = label.setText
        label.setText = lambda shown: (drawn.append(shown), set_text(shown))
        for start in range(1, len(text), 3):
            thread.add_text(text[start:start + 3])
        assert drawn == [] and thread.toPlainText() == text  # nothing drawn yet, nothing lost
        _run(thread_module.ANSWER_DELAY_MS + 100)
        assert len(drawn) == 1
        thread.add_text("Fin.")
        thread.end_answer()
        assert drawn[-1] == thread_module.plain_markdown(text + "Fin.").strip("\n") and len(drawn) == 2

    def test_a_long_answer_is_drawn_less_often(self, thread):
        thread.add_text("x" * 12000)
        assert thread._answer_timer.interval() == 12000 // thread_module.ANSWER_CHARS_PER_MS > 2 * thread_module.ANSWER_DELAY_MS

    def test_following_the_end_of_a_thread_deleted_meanwhile_raises_nothing(self, thread, monkeypatch):
        raised = []
        monkeypatch.setattr(sys, "excepthook", lambda *error: raised.append(error))
        thread.add_text("Une réponse")
        thread._follow_end()
        sip.delete(thread)  # the plugin unloaded while an answer was being written
        _run(thread_module.ANSWER_DELAY_MS + 100)
        assert raised == []

    def test_an_expression_in_a_tooltip_is_not_read_as_html(self, thread):
        thread.add_card("Filtre", True, '<b>"type"</b> = \'a\'\n  b', "1 / 2")
        label = thread._items[-1].widget.findChild(thread_module.ElidedLabel)
        assert label.toolTip() == ('<p style="white-space: pre-wrap;">&lt;b&gt;&quot;type&quot;&lt;/b&gt; = '
                                   '&#x27;a&#x27;\n  b</p>')
        assert thread_module.plain_tooltip("") == ""


_TEXTS = {"other": "Other", "answer": "Answer", "no_answer": "No answer", "close": "Close without answering"}


def _questions():
    questions_module = importlib.import_module(f"{_PKG}.core.agent.questions")
    return questions_module.parse_questions([
        {"question": "Which roads?", "header": "Roads",
         "options": [{"label": "Main only (Recommended)"}, {"label": "All"}]},
        {"question": "Which extras?", "header": "Extras", "multi_select": True,
         "options": [{"label": "Labels"}, {"label": "Zoom"}]}])


class TestQuestionCard:
    def test_answer_needs_each_question_then_freezes_with_the_choices(self, thread):
        card = thread.add_question_card(_TEXTS, _questions())
        answered = []
        card.answered.connect(answered.append)
        assert not card.answer_button.isEnabled()
        main = card._groups[0][0][0][0]
        main.click()
        assert not card.answer_button.isEnabled()  # the second question has no answer yet
        labels = card._groups[1][0][0][0]
        labels.click()
        assert card.answer_button.isEnabled()
        card.answer_button.click()
        assert answered == [[(["Main only (Recommended)"], ""), (["Labels"], "")]]
        assert card.done and not card.answer_button.isVisible()
        assert "Roads: Main only (Recommended)" in card.result.text()
        plain = thread.toPlainText()
        assert "? Which roads?" in plain and "Extras: Labels" in plain
        main.click()  # frozen: a click changes nothing, and nothing is emitted again
        assert len(answered) == 1 and card.selections()[0] == (["Main only (Recommended)"], "")

    def test_other_needs_its_text_and_gives_it_as_the_answer(self, thread):
        card = thread.add_question_card(_TEXTS, _questions()[:1])
        answered = []
        card.answered.connect(answered.append)
        _buttons, other, field = card._groups[0]
        other.click()
        assert field.isEnabled() and not card.answer_button.isEnabled()
        field.setText("the forest tracks")
        assert card.answer_button.isEnabled()
        field.returnPressed.emit()
        assert answered == [[([], "the forest tracks")]]

    def test_closing_the_card_declines(self, thread):
        card = thread.add_question_card(_TEXTS, _questions()[:1])
        declined = []
        card.declined.connect(lambda: declined.append(True))
        card.close_button.click()
        assert declined == [True] and card.done and card.result.text() == "No answer"
        assert "No answer" in thread.toPlainText()


class TestWidth:
    """The thread as wide as its frame, whatever it holds (no horizontal scroll bar: a wider content was cut)."""

    PATH = r"C:\\Users\\Simon\\Documents\\FilterMate\\exports\\layouts\\Ciliwung_buildings_within_100_m_landscape_A4.pdf"

    def test_a_long_word_wraps_and_the_thread_keeps_its_width(self, thread):
        thread.add_card("Layout exported", True, "pdf", "")
        thread.add_text("Exported to " + self.PATH)
        thread.end_answer()
        _run()
        assert thread.widget().width() <= thread.viewport().width()
        label = thread._items[-1].widget
        assert label.width() <= thread.viewport().width() and label.minimumSizeHint().width() < 300
        assert thread.toPlainText().endswith(self.PATH)  # the transcription keeps the word as it was

    def test_a_copy_of_the_long_word_is_the_word(self, thread):
        thread.add_text(self.PATH)
        thread.end_answer()
        label = thread._items[-1].widget
        label.setSelection(0, len(label.text()))
        assert thread_module.ZWSP in label.selectedText()
        QtWidgets.QApplication.clipboard().setText(label.selectedText())
        _run(50)
        assert QtWidgets.QApplication.clipboard().text() == self.PATH

    def test_a_copy_over_several_lines_is_cleaned_too(self, thread):
        """A QLabel gives its breaks as U+2029 in selectedText() and as \\n on the clipboard: they must still match."""
        text = f"Exported to\n{self.PATH}\n\nand to\n{self.PATH}"
        thread.add_text(text)
        thread.end_answer()
        label = thread._items[-1].widget
        label.setSelection(0, len(label.text()))
        selected = label.selectedText()
        assert thread_module.ZWSP in selected and "\u2029" in selected
        QtWidgets.QApplication.clipboard().setText(selected.replace("\u2029", "\n"))
        _run(50)
        assert QtWidgets.QApplication.clipboard().text() == text

    def test_a_copy_of_a_french_text_with_no_break_spaces_is_cleaned(self, thread):
        """Qt copies a no-break space as a space, selectedText() keeps it: 'Chemin\\u00a0: C:\\...' never matched."""
        from PyQt5 import QtTest
        text = f"Chemin\u00a0: {self.PATH}"
        thread.add_text(text)
        thread.end_answer()
        thread.show()
        label = thread._items[-1].widget
        label.setSelection(0, len(label.text()))
        assert "\u00a0" in label.selectedText() and thread_module.ZWSP in label.selectedText()
        QtWidgets.QApplication.clipboard().clear()
        label.setFocus()
        QtTest.QTest.keyClick(label, Qt.Key_C, Qt.ControlModifier)  # a real copy
        _run(50)
        assert QtWidgets.QApplication.clipboard().text() == f"Chemin : {self.PATH}"

    def test_a_text_of_another_origin_keeps_its_zwsp(self, thread):
        thread.add_text(self.PATH)
        thread.end_answer()
        label = thread._items[-1].widget
        label.setSelection(0, 5)
        other = "a\u200bb\nc"
        QtWidgets.QApplication.clipboard().setText(other)
        _run(50)
        assert QtWidgets.QApplication.clipboard().text() == other

    def test_a_long_link_is_cut_with_an_ellipsis_and_keeps_its_text_in_its_tooltip(self, thread):
        label = "Open the settings of the exports of the layouts in the tab of the configuration, section Layouts"
        thread.add_link(label, lambda: None)
        _run()
        button = thread.widget().findChild(QtWidgets.QPushButton, "pushButton_agent_link")
        assert thread.widget().width() <= thread.viewport().width()
        assert button.width() < button.sizeHint().width() and button.text().endswith("…")
        assert label in button.toolTip()

    def test_a_short_link_shows_its_whole_text(self, thread):
        thread.add_link("Open the settings", lambda: None)
        _run()
        button = thread.widget().findChild(QtWidgets.QPushButton, "pushButton_agent_link")
        assert button.text() == "Open the settings"

    def test_a_short_word_is_left_as_it_is(self):
        assert thread_module.breakable("Les bâtiments à moins de 100 m") == "Les bâtiments à moins de 100 m"


class TestActionBarSpacing:
    def test_the_same_gap_between_each_two_buttons_with_a_button_added_or_removed(self):
        bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        buttons = []
        for index in range(5):  # as in the .ui: a spacer between each two
            button = QtWidgets.QPushButton(bar)
            button.setFixedSize(34, 34)
            buttons.append(button)
            layout.addWidget(button)
            if index < 4:
                layout.addItem(QtWidgets.QSpacerItem(4, 20, QtWidgets.QSizePolicy.Expanding,
                                                     QtWidgets.QSizePolicy.Minimum))
        added = QtWidgets.QPushButton(bar)  # Compare, after the third one, without a spacer
        added.setFixedSize(34, 34)
        layout.insertWidget(layout.indexOf(buttons[2]) + 1, added)
        action_bar_module.even_action_spacing(layout)
        bar.show()

        def gaps():
            _run(30)
            shown = sorted((b for b in bar.findChildren(QtWidgets.QPushButton) if b.isVisible()), key=lambda b: b.x())
            return [after.x() - before.x() - 34 for before, after in zip(shown, shown[1:])]

        for width in (560, 360):
            bar.resize(width, 40)
            measured = gaps()
            assert len(measured) == 5 and max(measured) - min(measured) <= 1, measured
        added.setParent(None)
        action_bar_module.even_action_spacing(layout)
        measured = gaps()
        assert len(measured) == 4 and max(measured) - min(measured) <= 1, measured
        bar.deleteLater()
