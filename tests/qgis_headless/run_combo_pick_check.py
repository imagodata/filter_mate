# -*- coding: utf-8 -*-
"""
Layer pick detector of the current-layer combo box, in a real QGIS (CI: official Docker images, Xvfb).

ConfigurationManager._stamp_user_layer_picks records ``_user_layer_pick`` only when a user input really
changed the layer, also while the combo's signals are blocked (post-filter window) and through the
type-to-find completer popup; also when a window check runs before the call the detector posted, and when
the combo takes the item only after its popup is closed (Qt 5 macOS). Built from the real functions
(extracted from the source, no plugin load)
on a QgsMapLayerComboBox with four memory layers:

    xvfb-run -a python3 tests/qgis_headless/run_combo_pick_check.py

Prints OK / BAD per gesture and exits 1 when one is BAD.
"""
import ast
import logging
import os
from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtWidgets import QVBoxLayout, QWidget
from qgis.PyQt.QtTest import QTest

app = QgsApplication([], True); app.initQgis()
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = open(os.path.join(REPO, 'ui', 'managers', 'configuration_manager.py'), encoding='utf-8').read()
tree = ast.parse(src)
ns = {'logger': logging.getLogger('probe'), 'QCoreApplication': QCoreApplication}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in ('_stamp_user_layer_picks', '_enable_layer_search'):
        node.decorator_list = []
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'cm', 'exec'), ns)

layers = [QgsVectorLayer('Point?crs=EPSG:2154', name, 'memory') for name in ('alpha', 'beta', 'gamma', 'delta')]
QgsProject.instance().addMapLayers(layers)
w = QWidget(); lay = QVBoxLayout(w)
combo = QgsMapLayerComboBox(); lay.addWidget(combo)
class D: pass


d = D()
d.comboBox_filtering_current_layer = combo
d.ended = 0
d.applied = []  # current_layer_changed calls: the pick reconciled when the panel had not applied it
d.current_layer_changed = lambda layer, manual_change=False: (d.applied.append(layer.name()), setattr(d, 'current_layer', layer))
d._end_post_filter_window = lambda: setattr(d, 'ended', d.ended + 1)
ns['_enable_layer_search'](combo)
ns['_stamp_user_layer_picks'](d)
w.show(); w.activateWindow(); combo.setFocus(); app.processEvents()
combo.blockSignals(True)


def name():
    return combo.currentLayer().name() if combo.currentLayer() else None


def step(label, fn, expect_pick):
    d.__dict__.pop('_user_layer_pick', None)
    d.ended = 0
    d.applied = []
    before = name()
    fn()
    for _ in range(5):
        app.processEvents()
    picked = getattr(d, '_user_layer_pick', None)
    got = picked is not None
    ok = got == expect_pick
    print(f"{'OK ' if ok else 'BAD'} {label:42s} {before}->{name()} recorded={got} window_ended={d.ended} "
          f"applied={d.applied}", flush=True)
    return ok


combo.setLayer(layers[1])
results = [
    step('Down key (changes)', lambda: QTest.keyClick(combo, Qt.Key.Key_Down), True),
    step('Home key (cursor only)', lambda: QTest.keyClick(combo, Qt.Key.Key_Home), False),
    step('End key (cursor only)', lambda: QTest.keyClick(combo, Qt.Key.Key_End), False),
    step('click in the search field', lambda: QTest.mouseClick(combo.lineEdit(), Qt.MouseButton.LeftButton), False),
    step('Return without change', lambda: QTest.keyClick(combo, Qt.Key.Key_Return), False),
]
combo.setCurrentIndex(combo.count() - 1)
results.append(step('Down at the last item', lambda: QTest.keyClick(combo, Qt.Key.Key_Down), False))
combo.setLayer(layers[0])


def search(text):
    combo.lineEdit().selectAll()
    QTest.keyClicks(combo.lineEdit(), text)
    for _ in range(5):
        app.processEvents()
    popup = combo.completer().popup()
    QTest.keyClick(popup, Qt.Key.Key_Down)
    QTest.keyClick(popup, Qt.Key.Key_Return)


results.append(step('search "gam" + Down + Return (completer)', lambda: search('gam'), True))


def window_check_in_the_same_pass():
    """A check of the post-filter / undo window due in the same pass of the event loop as the key press runs
    before the call the detector posted: it looks at the input first (it put the source layer back, CI 3.34)."""
    QTest.keyClick(combo, Qt.Key.Key_Down)
    getattr(d, '_record_pending_layer_pick', lambda: None)()
    d.seen_by_the_check = getattr(d, '_user_layer_pick', None) is not None


combo.setLayer(layers[0])
d.seen_by_the_check = None
results.append(step('Down + a window check before the posted call', window_check_in_the_same_pass, True))
results.append(bool(d.seen_by_the_check))
print(f"{'OK ' if d.seen_by_the_check else 'BAD'} {'  ... the window check saw the pick':42s} {d.seen_by_the_check}",
      flush=True)


def popup_closed_then_item_taken():
    """Qt 5 macOS order: the call posted by the click runs in hidePopup's own event loops, before the combo box
    takes the item (itemSelected comes after hidePopup)."""
    combo.showPopup()
    app.processEvents()
    QTest.keyClick(combo.view(), Qt.Key.Key_Shift)  # an input in the popup, looked at: no change yet
    for _ in range(5):
        app.processEvents()
    combo.hidePopup()
    combo.setCurrentIndex((combo.currentIndex() + 1) % combo.count())


combo.setLayer(layers[0])
results.append(step('popup closed, then the item taken (macOS)', popup_closed_then_item_taken, True))
print('ALL OK' if all(results) else 'SOME BAD', flush=True)
os._exit(0 if all(results) else 1)
