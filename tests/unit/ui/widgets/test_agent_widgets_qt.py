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
                           (".ui.styles", _ROOT / "ui" / "styles")):
            package = types.ModuleType(_PKG + name)
            package.__path__ = [str(path)]
            sys.modules[_PKG + name] = package
        modules = [importlib.import_module(f"{_PKG}.{name}")
                   for name in ("ui.widgets.agent_widgets_strip", "ui.widgets.agent_thread", "core.agent.widgets")]
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return (app, *modules)


_APP, strip_module, thread_module, model = _load()
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

    def test_a_bound_an_older_version_rounded_at_an_end_is_put_back_at_the_end(self):
        state = _moved(_range(0.125, 10.006, low=0.13), high=5.0)
        assert state["low"] == 0.125

    def test_whole_numbers_for_an_integer_field(self):
        widget = model.make([], model.RANGE, "L1", "communes", "", field="n", minimum=3, maximum=17, integer=True)
        assert model.condition(_moved(widget, low=5), _quote, repr) == '"n" >= 5'


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
