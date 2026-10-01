# -*- coding: utf-8 -*-
"""Screen recordings of FilterMate in QGIS for the website background videos.

Usage (Windows QGIS driven from WSL or a Windows shell)::

    set FM_CLIP=hero
    set FM_VIDEO_OUT=C:\\Users\\Simon\\AppData\\Local\\Temp\\fm_video
    set FM_GPKG=C:\\Users\\Simon\\Documents\\bdtopo31\\BDT_3-5_GPKG_LAMB93_D031-ED2026-03-15.gpkg
    qgis-bin.exe --nologo --lang en --code scripts/site_videos.py

then ``scripts/site_video_render.py`` turns the recording into the MP4 and
poster used by the site.

The scenes are the use cases of ``website/stories.html`` played on the BD TOPO
3.5 GeoPackage of Haute-Garonne, driven through the real dock widget like
``scripts/recipe_screenshots.py``. Instead of screenshots, a ``Recorder``
grabs the QGIS main window about 15 times a second (popups and dialogs are
composited at their place) and logs, on the same clock, what the edit needs:

* ``point`` / ``click``: the widget the synthetic cursor moves to and clicks,
* ``camera``: the window region the virtual camera frames next,
* ``speed``: fast-forward factor while a filter task runs.

Every rectangle is in logical pixels of the main window client area; the
frames are physical pixels (``dpr`` in ``meta.json``).
"""
import faulthandler
import json
import os
import queue
import threading
import time
import traceback

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QTimer, Qt, QPoint, QRect
from qgis.PyQt.QtGui import QColor, QPainter
from qgis.PyQt.QtWidgets import (
    QApplication, QDockWidget, QLineEdit, QPushButton, QToolBar, QWidget,
)
from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRectangle, QgsProperty,
    QgsFeatureRequest, QgsExpression, QgsSymbol, QgsSingleSymbolRenderer,
)
from qgis.utils import iface, plugins

CLIP = os.environ.get('FM_CLIP', 'hero').lower()
ROOT = os.environ.get('FM_VIDEO_OUT', r'C:\Users\Simon\AppData\Local\Temp\fm_video')
GPKG = os.environ.get('FM_GPKG', r'C:\Users\Simon\Documents\bdtopo31\BDT_3-5_GPKG_LAMB93_D031-ED2026-03-15.gpkg')
OUT = os.path.join(ROOT, CLIP)
EXPORT_DIR = os.path.join(ROOT, 'export_out')
LOG = os.path.join(OUT, 'capture.log')
FPS = 15
WINDOW = (1760, 990)  # 16:9 client area, 2640x1485 frames at 150 % scaling
STATE = {}

STYLE = {  # layer name: (color, line/stroke width or point size, fill opacity)
    'epci': ('#6b7280', 1.2, 0.0),
    'commune': ('#6b7280', 0.8, 0.0),
    'zone_d_habitation': ('#f0a040', 0.6, 0.18),
    'zone_de_vegetation': ('#4c9a3c', None, 0.45),
    'foret_publique': ('#2f6f3e', None, 0.35),
    'zone_d_activite_ou_d_interet': ('#c9a0dc', 0.4, 0.35),
    'surface_hydrographique': ('#5aa9ff', None, 0.85),
    'batiment': ('#d64545', None, 1.0),
    'terrain_de_sport': ('#a3d977', None, 0.8),
    'cimetiere': ('#9aa0a6', None, 0.8),
    'equipement_de_transport': ('#b48ead', None, 0.8),
    'haie': ('#1f7a3a', 0.8, 1.0),
    'troncon_de_route': ('#3b3b3b', 0.6, 1.0),
    'troncon_de_voie_ferree': ('#7b4f2e', 1.0, 1.0),
    'troncon_hydrographique': ('#2e7bd6', 1.1, 1.0),
    'construction_lineaire': ('#b03fb0', 1.8, 1.0),
    'erp': ('#f2c200', 2.6, 1.0),
}

# Dense layers are only drawn below 1:120 000, so a department-wide opening
# shot renders in a second instead of drawing 1.2 M buildings.
DENSE = {'batiment', 'haie', 'troncon_hydrographique', 'zone_de_vegetation', 'troncon_de_route', 'zone_d_habitation',
         'construction_lineaire', 'foret_publique', 'zone_d_activite_ou_d_interet', 'terrain_de_sport',
         'cimetiere', 'equipement_de_transport', 'erp', 'troncon_de_voie_ferree'}

# toolbars left out of the footage (developer tools and editing, not FilterMate)
HIDDEN_TOOLBARS = ('reload', 'label', 'digitiz', 'snapping', 'mesh', 'shape', 'annotation', 'selection',
                   'vector', 'raster', 'database', 'web', 'help', 'data source')

DISPLAY = {  # readable display expression of the exploring pickers, per layer
    'commune': '"nom_officiel"',
    'epci': '"nom_officiel"',
    'troncon_hydrographique': 'coalesce("cpx_toponyme_de_cours_d_eau", "cleabs")',
    'surface_hydrographique': '"nature" || \' \' || "cleabs"',
    'troncon_de_route': 'coalesce("cpx_toponyme_route_nommee", "cpx_numero", "nature") || \' \' || "cleabs"',
    'zone_d_habitation': '"toponyme"',
    'batiment': '"usage_1" || \' \' || "cleabs"',
    'zone_de_vegetation': '"nature" || \' \' || "cleabs"',
    'erp': '"libelle"',
}

os.makedirs(OUT, exist_ok=True)
open(LOG, 'w').close()
# Stack of every thread every 40 s: shows where QGIS is when a step stalls.
STACKS = open(os.path.join(OUT, 'stacks.log'), 'w')
faulthandler.dump_traceback_later(40, repeat=True, file=STACKS)


def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f'{time.strftime("%H:%M:%S")} {m}\n')


# ------------------------------------------------------------------ recorder
class Recorder:
    """Grab the main window on a timer; JPEG encoding runs on a worker thread."""

    def __init__(self, out_dir, fps):
        self.frames_dir = os.path.join(out_dir, 'frames')
        os.makedirs(self.frames_dir, exist_ok=True)
        for name in os.listdir(self.frames_dir):
            os.remove(os.path.join(self.frames_dir, name))
        self.meta_path = os.path.join(out_dir, 'meta.json')
        self.interval = int(1000 / fps)
        self.times = []
        self.events = []
        self.windows = []  # extra top-level widgets to composite (dialogs)
        self.t0 = None
        self.queue = queue.Queue(maxsize=48)
        self.thread = threading.Thread(target=self._save_loop, daemon=True)
        self.timer = QTimer()
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._tick)

    @property
    def running(self):
        return self.t0 is not None

    def now(self):
        return time.perf_counter() - self.t0 if self.t0 is not None else 0.0

    def start(self):
        mw = iface.mainWindow()
        self.dpr = mw.devicePixelRatioF()
        self.size = (mw.width(), mw.height())
        self.t0 = time.perf_counter()
        self.thread.start()
        self.timer.start(self.interval)
        self._tick()
        log(f'recording {self.size} dpr={self.dpr}')

    def event(self, kind, **data):
        if self.running:
            data.update(t=round(self.now(), 3), kind=kind)
            self.events.append(data)

    def _save_loop(self):
        while True:
            item = self.queue.get()
            if item is None:
                return
            i, img = item
            img.save(os.path.join(self.frames_dir, f'{i:06d}.jpg'), 'JPG', 90)

    def _tick(self):
        try:
            mw = iface.mainWindow()
            pm = mw.grab()
            self.windows = [w for w in self.windows if w is not None and not sip.isdeleted(w)]
            extra = [w for w in self.windows if w.isVisible()]
            for w in (QApplication.activePopupWidget(), QApplication.activeModalWidget()):
                if w is not None and w is not mw and w.isVisible() and w not in extra:
                    extra.append(w)
            if extra:
                origin = mw.mapToGlobal(QPoint(0, 0))
                painter = QPainter(pm)
                for w in extra:
                    painter.drawPixmap(w.mapToGlobal(QPoint(0, 0)) - origin, w.grab())
                painter.end()
            self.times.append(round(self.now(), 4))
            self.queue.put((len(self.times) - 1, pm.toImage()))
        except Exception:
            log(traceback.format_exc())

    def stop(self):
        self.timer.stop()
        duration = self.now()
        self.queue.put(None)
        self.thread.join()
        meta = {'clip': CLIP, 'dpr': self.dpr, 'size': self.size, 'fps': FPS,
                'frames': self.times, 'events': self.events}
        with open(self.meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=1)
        log(f'stopped: {len(self.times)} frames in {duration:.1f} s '
            f'({len(self.times) / max(duration, 0.001):.1f} fps), {len(self.events)} events')


REC = Recorder(OUT, FPS)


# ------------------------------------------------------------------ geometry
def dock():
    return plugins['filter_mate'].app.dockwidget


def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]


def rect_of(widget):
    """Rectangle of a widget in logical coordinates of the main window client area."""
    mw = iface.mainWindow()
    p = widget.mapToGlobal(QPoint(0, 0)) - mw.mapToGlobal(QPoint(0, 0))
    return QRect(p, widget.size())


def resolve(target):
    """QRect for a region name, a dock widget attribute name, a list of those, or a callable."""
    if callable(target):
        target = target()
    if isinstance(target, QRect):
        return target
    if isinstance(target, QWidget):
        return rect_of(target)
    if isinstance(target, (list, tuple)):
        r = QRect()
        for t in target:
            r = r.united(resolve(t))
        return r
    mw = iface.mainWindow()
    if target == 'full':
        return QRect(0, 0, mw.width(), mw.height())
    if target == 'canvas':
        return rect_of(iface.mapCanvas())
    if target == 'dock':
        return rect_of(dock())
    if target == 'layers':
        return rect_of(iface.layerTreeView())
    return rect_of(getattr(dock(), target))


def box(r):
    return [r.x(), r.y(), r.width(), r.height()]


# ------------------------------------------------------------------ edit events
def cam(target, dur=1.4, pad=16, drift=1.0):
    """Frame a region: the camera eases there in `dur` s, then drifts (zoom factor per 10 s)."""
    def _s():
        r = resolve(target).adjusted(-pad, -pad, pad, pad)
        REC.event('camera', rect=box(r), dur=dur, drift=drift)
    return _s


def point(target):
    """Move the cursor to the centre of a widget (arrives before the next click)."""
    def _s():
        r = resolve(target)
        REC.event('point', x=r.center().x(), y=r.center().y())
    return _s


def click(target, fn=None):
    def _s():
        r = resolve(target)
        REC.event('click', x=r.center().x(), y=r.center().y())
        if fn is not None:
            return fn()
    return _s


def act(target, fn=None, lead=900, after=900):
    """Cursor travels to a widget, clicks it, then runs fn."""
    return [(after, point(target)), (lead, click(target, fn))]


def speed(factor):
    return lambda: REC.event('speed', factor=factor)


def mark(name):
    return lambda: REC.event('mark', name=name)


# ------------------------------------------------------------------ helpers from recipe_screenshots.py
def check_combo_items(combo, texts, uncheck_others=False):
    model = combo.model()
    for i in range(model.rowCount()):
        item = model.item(i)
        hit = any(t.lower() in item.text().lower() for t in texts)
        if hit:
            item.setCheckState(Qt.CheckState.Checked)
        elif uncheck_others:
            item.setCheckState(Qt.CheckState.Unchecked)


def set_combo_text(combo, text):
    i = combo.findText(text, Qt.MatchFlag.MatchContains)
    if i >= 0:
        combo.setCurrentIndex(i)


def fids_where(name, expr):
    return [f.id() for f in layer(name).getFeatures(QgsFeatureRequest(QgsExpression(expr)))]


def counts(names):
    out = {}
    for n in names:
        req = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry).setNoAttributes()
        out[n] = sum(1 for _ in layer(n).getFeatures(req))
    log(f'counts {out}')
    return out


def style_layer(vl, style):
    if not style:
        return
    color, width, opacity = style
    sym = QgsSymbol.defaultSymbol(vl.geometryType())
    sym.setColor(QColor(color))
    if vl.geometryType() == 0 and hasattr(sym, 'setSize') and width:
        sym.setSize(width)
    elif width is not None and hasattr(sym, 'setWidth'):
        sym.setWidth(width)
    if vl.geometryType() == 2:
        sl = sym.symbolLayer(0)
        if opacity == 0.0:
            sl.setBrushStyle(Qt.BrushStyle.NoBrush)
        else:
            sym.setOpacity(opacity)
        if hasattr(sl, 'setStrokeColor'):
            sl.setStrokeColor(QColor(color).darker(130))
            if width is not None:
                sl.setStrokeWidth(width)
    vl.setRenderer(QgsSingleSymbolRenderer(sym))


def tasks_running():
    return QgsApplication.taskManager().countActiveTasks() > 0


def rendering():
    return iface.mapCanvas().isDrawing()


def set_extent(rect):
    iface.mapCanvas().setExtent(QgsRectangle(rect))
    iface.mapCanvas().refresh()


def zoom_focus(scale):
    def _s():
        bb = layer(STATE['focus_layer']).getFeature(STATE['focus_fid']).geometry().boundingBox()
        bb.scale(scale)
        set_extent(bb)
    return _s


def zoom_layer(name, scale=1.02):
    def _s():
        bb = layer(name).extent()
        bb.scale(scale)
        set_extent(bb)
    return _s


# ------------------------------------------------------------------ scene steps
def setup(layer_names, focus_layer, focus_expr, scale=1.25, dense_scale=120000):
    """Load layers (bottom to top) and zoom on the focus feature (scale=None: whole layer)."""
    def _s():
        mw = iface.mainWindow()
        # QGIS saves its window layout on exit, in the user's own profile:
        # remember it so quit_when_idle() can put it back.
        STATE['ui'] = (mw.saveGeometry(), mw.saveState(), mw.isMaximized())
        mw.showNormal()
        mw.resize(*WINDOW)
        mw.move(0, 0)
        for d in mw.findChildren(QDockWidget):
            if d.objectName() in ('MessageLog', 'Browser', 'Browser2', 'ProcessingToolbox'):
                d.hide()
        for tb in mw.findChildren(QToolBar):
            name = (tb.objectName() + ' ' + tb.windowTitle()).lower()
            if any(k in name for k in HIDDEN_TOOLBARS):
                tb.hide()
        canvas = iface.mapCanvas()
        canvas.setRenderFlag(False)
        canvas.setCanvasColor(QColor('#f7f7f4'))
        canvas.setSelectionColor(QColor(255, 225, 0, 90))
        # No feature counts in the Layers panel: counting per symbol walks the
        # whole department (1.2 M buildings) in a task holding the GeoPackage,
        # and froze the main thread for minutes in the first recordings.
        for name in layer_names:
            vl = QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr')
            QgsProject.instance().addMapLayer(vl)
            node = QgsProject.instance().layerTreeRoot().findLayer(vl.id())
            if node:
                node.setCustomProperty('showFeatureCount', False)
            vl.setLabelsEnabled(False)
            vl.setScaleBasedVisibility(name in DENSE and dense_scale is not None)
            if name in DENSE and dense_scale:
                vl.setMinimumScale(dense_scale)
                vl.setMaximumScale(0)
            try:
                style_layer(vl, STYLE.get(name))
            except Exception:
                log(traceback.format_exc())
        fids = fids_where(focus_layer, focus_expr)
        log(f'focus {focus_layer} {focus_expr} -> {fids}')
        STATE['focus_fid'] = fids[0]
        STATE['focus_layer'] = focus_layer
        if scale is None:
            bb = layer(focus_layer).extent()
            bb.scale(1.04)
        else:
            bb = layer(focus_layer).getFeature(fids[0]).geometry().boundingBox()
            bb.scale(scale)
        set_extent(bb)
        canvas.setRenderFlag(True)
    return _s


def open_plugin():
    plugins['filter_mate'].run()


def size_dock():
    d = dock()
    d.setMinimumWidth(0)
    iface.mainWindow().resizeDocks([d], [413], Qt.Orientation.Horizontal)


def source(name):
    def _s():
        iface.setActiveLayer(layer(name))  # returns True: must not re-arm the step
    return _s


def single_mode(tracking=True, selecting=False):
    def _s():
        d = dock()
        d.mGroupBox_exploring_single_selection.setChecked(True)
        name = iface.activeLayer().name()
        if DISPLAY.get(name):
            d.mFieldExpressionWidget_exploring_single_selection.setExpression(DISPLAY[name])
        d.pushButton_checkable_exploring_tracking.setChecked(tracking)
        d.pushButton_checkable_exploring_selecting.setChecked(selecting)
    return _s


def restyle(name, fill, stroke, width, selection_alpha=None):
    """Polygon symbol with a translucent fill and an opaque outline (and the selection colour)."""
    def _s():
        vl = layer(name)
        sym = QgsSymbol.defaultSymbol(vl.geometryType())
        sl = sym.symbolLayer(0)
        if fill is None:
            sl.setBrushStyle(Qt.BrushStyle.NoBrush)
        else:
            sl.setFillColor(QColor(*fill))
        sl.setStrokeColor(QColor(stroke))
        sl.setStrokeWidth(width)
        vl.setRenderer(QgsSingleSymbolRenderer(sym))
        vl.triggerRepaint()
        if selection_alpha is not None:
            iface.mapCanvas().setSelectionColor(QColor(255, 216, 61, selection_alpha))
    return _s


def pick_focus():
    dock().mFeaturePickerWidget_exploring_single_selection.setFeature(STATE['focus_fid'])
    hide_popup()


def picker_edit():
    return dock().mFeaturePickerWidget_exploring_single_selection.findChild(QLineEdit)


def type_into(get_edit, text, per_char=110, clear=True):
    """Type text one key at a time (real key events, so completers react)."""
    steps = []
    if clear:
        steps.append((0, lambda: (get_edit().setFocus(), get_edit().selectAll())))
    for ch in text:
        steps.append((per_char, (lambda c: lambda: type_char(get_edit(), c))(ch)))
    return steps


def type_char(edit, ch):
    """One key press; accented characters are inserted (a QTest key click on 'é' closed QGIS)."""
    from qgis.PyQt.QtTest import QTest
    if ch.isascii():
        QTest.keyClicks(edit, ch)
    else:
        edit.insert(ch)


def hide_popup():
    w = QApplication.activePopupWidget()
    if w is not None:
        w.hide()


def open_combo(name):
    return lambda: getattr(dock(), name).showPopup()


def check_one_by_one(name, texts, per_item=160, uncheck_others=True):
    """Check the items of a checkable combo one after the other (the popup shows them tick)."""
    def items():
        combo = getattr(dock(), name)
        model = combo.model()
        return combo, [model.item(i) for i in range(model.rowCount())]

    def uncheck():
        if uncheck_others:
            combo, its = items()
            for it in its:
                it.setCheckState(Qt.CheckState.Unchecked)

    def check_nth(k):
        def _s():
            combo, its = items()
            wanted = [it for it in its if texts is None or any(t.lower() in it.text().lower() for t in texts)]
            if k < len(wanted):
                view = combo.view()
                if view.isVisible():
                    r = view.visualRect(wanted[k].index())
                    r = QRect(view.viewport().mapToGlobal(r.topLeft()) - iface.mainWindow().mapToGlobal(QPoint(0, 0)),
                              r.size())
                    REC.event('click', x=r.x() + 14, y=r.center().y())
                wanted[k].setCheckState(Qt.CheckState.Checked)
        return _s

    n = 16 if texts is None else len(texts)
    return [(0, uncheck)] + [(per_item, check_nth(k)) for k in range(n)]


def combo_check(name, texts, per_item=380):
    """Open a checkable combo, tick the wanted items one by one, close it."""
    return act(name, open_combo(name)) + check_one_by_one(name, texts, per_item) + [(700, hide_popup)]


def combo_choose(name, text, keep=1200):
    """Open an ordinary combo and visibly choose one entry."""
    def show():
        combo = getattr(dock(), name)
        combo.showPopup()

        def place_inside_window():
            popup = combo.view().window()
            mw = iface.mainWindow()
            origin = mw.mapToGlobal(QPoint(0, 0))
            anchor = combo.mapToGlobal(QPoint(0, 0))
            x = min(anchor.x(), origin.x() + mw.width() - popup.width())
            y = max(origin.y(), anchor.y() - popup.height() - 2)
            popup.move(x, y)

        # QComboBox creates and sizes its private popup during showPopup().
        QTimer.singleShot(0, place_inside_window)

    def choose():
        combo = getattr(dock(), name)
        index = combo.findText(text, Qt.MatchFlag.MatchContains)
        if index < 0:
            log(f'combo entry not found: {name} -> {text}')
            hide_popup()
            return
        view = combo.view()
        model_index = combo.model().index(index, 0)
        r = to_main(view.viewport(), view.visualRect(model_index))
        REC.event('point', x=r.center().x(), y=r.center().y())
        REC.event('click', x=r.center().x(), y=r.center().y())
        combo.setCurrentIndex(index)
        hide_popup()

    return act(name, show) + [(keep, choose), hold(350)]


def to_main(widget, r):
    """QRect r in widget viewport coordinates -> main window coordinates."""
    return QRect(widget.mapToGlobal(r.topLeft()) - iface.mainWindow().mapToGlobal(QPoint(0, 0)), r.size())


def tree_item(name):
    """Rectangle of a layer's row in the Layers panel."""
    def _r():
        view = iface.layerTreeView()
        node = QgsProject.instance().layerTreeRoot().findLayer(layer(name).id())
        try:
            idx = view.node2index(node)
        except AttributeError:
            idx = view.layerTreeModel().node2index(node)
        return to_main(view.viewport(), view.visualRect(idx))
    return _r


def pick_layer(name):
    """Click a layer in the Layers panel: it becomes FilterMate's source layer."""
    return act(tree_item(name), source(name))


def multi_widget():
    w = dock().checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
    return w, w.list_widgets[w.layer.id()]


def multi_item(text):
    def _r():
        _w, lw = multi_widget()
        items = lw.findItems(text, Qt.MatchFlag.MatchStartsWith)
        if not items:
            return rect_of(lw)
        lw.scrollToItem(items[0])
        r = lw.visualItemRect(items[0])
        return to_main(lw.viewport(), QRect(r.x(), r.y(), 28, r.height()))
    return _r


def multi_check(texts, per_item=900):
    """Tick features in the multiple selection list, one click each."""
    steps = []
    for t in texts:
        def _check(t=t):
            w, lw = multi_widget()
            items = lw.findItems(t, Qt.MatchFlag.MatchStartsWith)
            if items:
                items[0].setCheckState(Qt.CheckState.Checked)
                w._emit_checked_items_update()
            else:
                log(f'multi item not found: {t}')
        steps += act(multi_item(t), _check, lead=650, after=per_item - 650)
    return steps


def multi_mode():
    d = dock()
    d.mGroupBox_exploring_multiple_selection.setChecked(True)
    name = iface.activeLayer().name()
    if DISPLAY.get(name):
        d.mFieldExpressionWidget_exploring_multiple_selection.setExpression(DISPLAY[name])


def select_all_multi():
    multi_widget()[0].select_all('Select All')


def custom_edit():
    return dock().mFieldExpressionWidget_exploring_custom_selection.findChild(QLineEdit)


def custom_mode():
    dock().mGroupBox_exploring_custom_selection.setChecked(True)


def typed_custom(expr, per_char=45):
    """Type a custom selection expression, then commit it like Enter would."""
    return act(custom_edit, custom_mode) + type_into(custom_edit, expr, per_char) + [(400, custom(expr))]


def toolbox_button(text):
    """The header button of a page of the Filtering / Exporting / Configuration toolbox."""
    def _r():
        from qgis.PyQt.QtWidgets import QAbstractButton
        for b in dock().toolBox_tabTools.findChildren(QAbstractButton):
            if text.lower() in b.text().lower():
                return rect_of(b)
        return rect_of(dock().toolBox_tabTools)
    return _r


def refresh_targets():
    d = dock()
    d.checkableComboBoxLayer_filtering_layers_to_filter.checkedItemsChangedEvent()


def filtering_tab():
    d = dock()
    d.toolBox_tabTools.setCurrentIndex(0)


def enable(name, on=True):
    return lambda: getattr(dock(), name).setChecked(on)


def custom(expr):
    def _s():
        d = dock()
        d.mGroupBox_exploring_custom_selection.setChecked(True)
        d.mFieldExpressionWidget_exploring_custom_selection.setExpression(expr)
    return _s


def buffer_value(v):
    def _s():
        d = dock()
        d.pushButton_checkable_filtering_buffer_value.setChecked(True)
        d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(v)
    return _s


def buffer_off():
    dock().pushButton_checkable_filtering_buffer_value.setChecked(False)


def buffer_expr(expr, btype=None):
    def _s():
        d = dock()
        d.pushButton_checkable_filtering_buffer_value.setChecked(True)
        w = d.mPropertyOverrideButton_filtering_buffer_value_property
        w.setToProperty(QgsProperty.fromExpression(expr))
        w.setActive(True)
        d.filtering_buffer_property_changed()
        if btype:
            d.pushButton_checkable_filtering_buffer_type.setChecked(True)
            set_combo_text(d.comboBox_filtering_buffer_type, btype)
    return _s


def buffer_expr_dialog(expr, keep_menu=1500, keep_dialog=3000):
    """Show the real property menu and expression editor for a buffer expression.

    The expression is installed first so the editor opens pre-filled.  QGIS
    implements both the property menu and the editor as separate top-level
    widgets; the recorder composites them over the main-window grab.
    """
    def _s():
        buffer_expr(expr)()
        button = dock().mPropertyOverrideButton_filtering_buffer_value_property
        state = {}

        def inspect_menu():
            menu = QApplication.activePopupWidget()
            if menu is None:
                log('buffer property menu not found')
                return
            state['menu'] = menu
            if menu not in REC.windows:
                REC.windows.append(menu)
            actions = [a for a in menu.actions() if a.isVisible()]
            log(f'buffer property menu entries {[a.text() for a in actions]}')

            def label(a):
                return a.text().replace('&', '').strip().lower().rstrip('.…')
            action = next(
                (a for a in actions if a.isEnabled() and label(a) == 'edit'),
                None,
            )
            if action is None:
                action = next(
                    (a for a in actions if a.isEnabled() and label(a) == 'expression'),
                    None,
                )
            state['action'] = action
            if action is not None:
                ar = to_main(menu, menu.actionGeometry(action))
                REC.event('point', x=ar.center().x(), y=ar.center().y())
                menu.setActiveAction(action)

        def inspect_dialog(tries=0):
            dialog = QApplication.activeModalWidget()
            if dialog is None or dialog is iface.mainWindow():
                if tries < 10:
                    QTimer.singleShot(150, lambda: inspect_dialog(tries + 1))
                else:
                    log('buffer expression dialog not found')
                return
            state['dialog'] = dialog
            if dialog not in REC.windows:
                REC.windows.append(dialog)
            REC.event('camera', rect=box(rect_of(dialog).adjusted(-25, -25, 25, 25)),
                      dur=1.0, drift=1.0)
            buttons = [b for b in dialog.findChildren(QPushButton) if b.isVisible()]
            ok = next((b for b in buttons if b.isDefault()), None)
            state['ok'] = ok
            if ok is not None:
                r = rect_of(ok)
                QTimer.singleShot(
                    keep_dialog - 700,
                    lambda: REC.event('point', x=r.center().x(), y=r.center().y()),
                )
                QTimer.singleShot(
                    keep_dialog - 200,
                    lambda: REC.event('click', x=r.center().x(), y=r.center().y()),
                )
            QTimer.singleShot(keep_dialog, close_dialog)

        def close_dialog():
            dialog = state.get('dialog')
            if dialog is not None and not sip.isdeleted(dialog):
                dialog.accept()
            if dialog in REC.windows:
                REC.windows.remove(dialog)

        def activate_expression():
            menu = state.get('menu')
            action = state.get('action')
            if action is None:
                if menu is not None:
                    menu.close()
                return
            ar = to_main(menu, menu.actionGeometry(action))
            REC.event('click', x=ar.center().x(), y=ar.center().y())
            QTimer.singleShot(150, inspect_dialog)
            menu.close()
            action.trigger()  # opens a nested modal loop until close_dialog()
            if menu in REC.windows:
                REC.windows.remove(menu)

        QTimer.singleShot(150, inspect_menu)
        QTimer.singleShot(keep_menu, activate_expression)
        button.click()  # opens a nested popup loop; timers above continue to run

    return _s


def combine(source_op=None, target_op=None):
    def _s():
        d = dock()
        d.pushButton_checkable_filtering_current_layer_combine_operator.setChecked(True)
        if source_op:
            set_combo_text(d.comboBox_filtering_source_layer_combine_operator, source_op)
        if target_op:
            set_combo_text(d.comboBox_filtering_other_layers_combine_operator, target_op)
    return _s


def click_filter():
    dock().pushButton_action_filter.click()


def click_undo():
    dock().pushButton_action_undo_filter.click()


def click_unfilter():
    dock().pushButton_action_unfilter.click()


def wait_idle():
    """Re-armed while a task runs or the canvas draws."""
    return lambda: tasks_running() or rendering()


def rec_start():
    iface.mapCanvas().waitWhileRendering()
    REC.start()


def stop_recording():
    faulthandler.cancel_dump_traceback_later()
    REC.stop()


def restore_ui():
    """Give the user's window layout back (toolbars, docks, size) before QGIS saves it."""
    if 'ui' not in STATE:
        return
    geometry, state, maximized = STATE.pop('ui')
    mw = iface.mainWindow()
    mw.restoreState(state)
    mw.restoreGeometry(geometry)
    if maximized:
        mw.showMaximized()


def quit_when_idle():
    """Quit once no task runs: quitting under a running export hangs QGIS."""
    if tasks_running():
        return True
    restore_ui()
    QgsProject.instance().setDirty(False)
    QgsApplication.instance().quit()


def finish():
    stop_recording()
    QTimer.singleShot(500, quit_when_idle)


def refocus():
    """FilterMate zooms on the filtered extent; put the scene's framing back (as the stories do)."""
    if STATE.get('scene_scale'):
        zoom_focus(STATE['scene_scale'])()


def run_filter(fast=4.0):
    """Click Filter, fast-forward while the task runs, restore the framing, let the canvas redraw."""
    return act('pushButton_action_filter', click_filter) + [
        (300, speed(fast)), (1500, wait_idle()), (0, refocus), (600, wait_idle()), (400, speed(1.0)),
    ]


def scope(scope_layer, target_names=None):
    """Unrecorded opening: restrict the target layers to the focus commune or EPCI."""
    return [
        (500, source(scope_layer)), (1500, single_mode(tracking=False)), (2500, pick_focus),
        (500, filtering_tab),
        (500, enable('pushButton_checkable_filtering_layers_to_filter')),
        (300, lambda: check_combo_items(dock().checkableComboBoxLayer_filtering_layers_to_filter,
                                        target_names or [''], uncheck_others=True)),
        (300, refresh_targets),
        (300, enable('pushButton_checkable_filtering_geometric_predicates')),
        (300, lambda: check_combo_items(dock().comboBox_filtering_geometric_predicates, ['intersect'], True)),
        (300, buffer_off),
        (500, click_filter), (3000, wait_idle()), (1500, lambda: None),
        (0, lambda: layer(scope_layer).removeSelection()), (500, wait_idle()),
    ]


def boot(layers, focus_layer, focus_expr, scale=1.25, dense_scale=120000):
    return [(1000, setup(layers, focus_layer, focus_expr, scale, dense_scale)),
            (3000, open_plugin), (8000, size_dock), (1500, wait_idle())]


# ------------------------------------------------------------------ clips
S1_LAYERS = ['commune', 'zone_de_vegetation', 'surface_hydrographique', 'zone_d_habitation', 'terrain_de_sport',
             'cimetiere', 'equipement_de_transport', 'batiment', 'haie', 'troncon_hydrographique',
             'troncon_de_route', 'construction_lineaire', 'erp']
S1_TARGETS = [n for n in S1_LAYERS if n != 'commune']

def noop():
    return None


def hold(ms):
    return (ms, noop)


def gb_check(name):
    """The check box in the title of a collapsible group box."""
    def _r():
        r = rect_of(getattr(dock(), name))
        return QRect(r.x() + 8, r.y() + 4, 26, 26)
    return _r


def spin_edit():
    return dock().mQgsDoubleSpinBox_filtering_buffer_value.findChild(QLineEdit)


def typed_buffer(value):
    """Click the buffer distance, type it, commit it."""
    return (act('mQgsDoubleSpinBox_filtering_buffer_value', lambda: spin_edit().setFocus())
            + type_into(spin_edit, str(value), per_char=200) + [(300, buffer_value(value))])


def settle(fast=2.0):
    """Fast-forward until the tasks and the canvas are idle."""
    return [(300, speed(fast)), (800, wait_idle()), (300, speed(1.0))]


def show_map(ms=3200, drift=1.04):
    return [(0, cam('canvas', dur=1.6, drift=drift)), hold(ms)]


def recorded_scene(scale):
    """After an unrecorded scope: frame the focus feature and start recording."""
    def remember():
        STATE['scene_scale'] = scale
    return [(0, remember), (500, zoom_focus(scale)), (1500, wait_idle()), (500, rec_start),
            (0, cam('full', dur=0, drift=1.03)), hold(900)]


def ending(verify=None):
    """Closing wide shot, stop recording, log the counts the site quotes, quit when idle."""
    steps = [(0, cam('full', dur=1.6)), (2200, stop_recording)]
    if verify:
        steps.append((0, lambda: counts(verify)))
    return steps + [(500, quit_when_idle)]


EXPLORE_ZONE = ['mGroupBox_exploring_single_selection', 'mGroupBox_exploring_custom_selection']
FILTER_ZONE = ['pushButton_checkable_filtering_layers_to_filter', 'mQgsDoubleSpinBox_filtering_buffer_value']
ACTION_ZONE = ['pushButton_action_filter', 'pushButton_checkable_filtering_buffer_value']
TARGETS = 'checkableComboBoxLayer_filtering_layers_to_filter'
PREDICATES = 'comboBox_filtering_geometric_predicates'


def targets(names):
    return (act('pushButton_checkable_filtering_layers_to_filter',
                enable('pushButton_checkable_filtering_layers_to_filter'))
            + combo_check(TARGETS, names, per_item=300) + [(200, refresh_targets)])


def predicates(names):
    return (act('pushButton_checkable_filtering_geometric_predicates',
                enable('pushButton_checkable_filtering_geometric_predicates'))
            + combo_check(PREDICATES, names))


def and_targets():
    return act('pushButton_checkable_filtering_current_layer_combine_operator', combine(None, 'AND'))


S1_LAYERS = ['commune', 'zone_de_vegetation', 'surface_hydrographique', 'zone_d_habitation', 'terrain_de_sport',
             'cimetiere', 'equipement_de_transport', 'batiment', 'haie', 'troncon_hydrographique',
             'troncon_de_route', 'construction_lineaire', 'erp']
S1_TARGETS = [n for n in S1_LAYERS if n != 'commune']

# hero: from the whole department to one commune, then one click filters 12 layers.
HERO = boot(S1_LAYERS, 'commune', '"nom_officiel" = \'Saint-Gaudens\'', scale=None) + [
    (0, restyle('commune', (138, 143, 134, 30), '#6b7280', 0.5, selection_alpha=140)),
    (500, source('commune')), (1500, single_mode(tracking=True, selecting=True)), (1500, filtering_tab),
    (1000, rec_start), (0, cam('full', dur=0, drift=1.04)),
    (1200, cam(EXPLORE_ZONE, dur=1.6, pad=30)),
] + act(picker_edit) + type_into(picker_edit, 'Saint-Gau', per_char=140) + [
    (900, pick_focus)] + settle() + show_map(2600, 1.03) + [
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(S1_TARGETS) + predicates(['intersect']) + [
    (200, buffer_off), (400, cam(ACTION_ZONE, dur=1.3, pad=40)),
] + run_filter() + [
    (200, cam('canvas', dur=1.8, drift=1.05)), hold(4200),
    (0, cam('layers', dur=1.4)), hold(2600),
] + ending(S1_TARGETS)

# explore: the three exploring modes on the communes of the department.
EXPLORE_LAYERS = ['epci', 'commune', 'surface_hydrographique', 'troncon_hydrographique']
EXPLORE = boot(EXPLORE_LAYERS, 'commune', '"nom_officiel" = \'Toulouse\'', scale=None) + [
    (0, restyle('commune', (138, 143, 134, 40), '#5b636b', 0.5, selection_alpha=180)),
    (0, restyle('epci', None, '#39474f', 1.2)),
    (500, source('commune')), (1500, single_mode(tracking=True)), (1000, rec_start),
    (0, cam('full', dur=0, drift=1.03)), (1000, cam(EXPLORE_ZONE, dur=1.5, pad=30)),
] + act('pushButton_checkable_exploring_selecting', enable('pushButton_checkable_exploring_selecting')) \
    + act(picker_edit) + type_into(picker_edit, 'Toulou', per_char=150) + [
    (900, pick_focus)] + settle() + show_map(2800) + [
    (0, cam(['mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection'], dur=1.4, pad=30)),
] + act(gb_check('mGroupBox_exploring_multiple_selection'), multi_mode) + [hold(1500)] + [
    (0, cam('mGroupBox_exploring_multiple_selection', dur=1.2, pad=30)),
] + multi_check(['Blagnac', 'Colomiers', 'Tournefeuille', 'Balma']) + settle() + show_map(3000) + [
    (0, cam(EXPLORE_ZONE, dur=1.4, pad=30)),
] + typed_custom('"population" > 20000') \
    + act('pushButton_checkable_exploring_selecting', enable('pushButton_checkable_exploring_selecting', False)) \
    + act('pushButton_checkable_exploring_selecting', enable('pushButton_checkable_exploring_selecting'), after=500) \
    + act('pushButton_exploring_zoom', lambda: dock().pushButton_exploring_zoom.click()) \
    + settle() + show_map(3200) + ending()

S3_LAYERS = ['commune', 'zone_d_habitation', 'surface_hydrographique', 'batiment', 'troncon_hydrographique',
             'troncon_de_route', 'erp']
S3_FLOOD_TARGETS = ['batiment', 'erp', 'troncon_de_route']

# buffer (story 3): what the Garonne can reach in Grenade, 300 m then 100 m, then Undo.
BUFFER = boot(S3_LAYERS, 'commune', '"nom_officiel" = \'Grenade\'', 1.2) + scope('commune') + recorded_scene(1.2) \
    + pick_layer('surface_hydrographique') + [
    (1200, cam(['mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection'], dur=1.4, pad=30)),
] + act(gb_check('mGroupBox_exploring_multiple_selection'), multi_mode) + [
    (2500, select_all_multi), hold(1200), (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(S3_FLOOD_TARGETS) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(300) + and_targets() + [
    (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + show_map(3500) + [
    (0, cam(FILTER_ZONE, dur=1.3, pad=40)),
] + typed_buffer(100) + [(300, cam(ACTION_ZONE, dur=1.0, pad=40))] + run_filter() + [
    (0, lambda: counts(S3_FLOOD_TARGETS))] + show_map(3000) + [
    (0, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + act('pushButton_action_undo_filter', click_undo) + settle(4.0) + [(0, refocus)] + settle() + show_map(3000) \
    + ending(S3_FLOOD_TARGETS)

S2_LAYERS = ['commune', 'zone_d_habitation', 'batiment', 'troncon_de_voie_ferree', 'troncon_de_route', 'erp']
NOISE_EXPR = 'CASE WHEN "importance" = \'1\' THEN 300 WHEN "importance" = \'2\' THEN 250 ELSE 100 END'

# noise (story 2): buildings exposed to major-road noise in Muret, buffer by expression.
NOISE = boot(S2_LAYERS, 'commune', '"nom_officiel" = \'Muret\'', 1.2) + scope('commune') + recorded_scene(1.2) \
    + pick_layer('troncon_de_route') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom('"importance" IN (\'1\', \'2\')') + settle() + show_map(2400) + [
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['batiment', 'erp']) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) \
    + act('mPropertyOverrideButton_filtering_buffer_value_property', buffer_expr_dialog(NOISE_EXPR),
          lead=900, after=900) \
    + act('pushButton_checkable_filtering_buffer_type',
          enable('pushButton_checkable_filtering_buffer_type')) \
    + combo_choose('comboBox_filtering_buffer_type', 'Flat') \
    + and_targets() + [(400, cam(ACTION_ZONE, dur=1.2, pad=40))] + run_filter() + show_map(3500) + [
    (0, zoom_focus(0.5))] + settle() + show_map(3500, 1.05) + ending(['batiment', 'erp', 'troncon_de_route'])

S4_LAYERS = ['epci', 'commune', 'surface_hydrographique', 'troncon_hydrographique', 'troncon_de_route',
             'construction_lineaire']

# bridges (story 4): roads and structures crossing a permanent watercourse in Toulouse Métropole.
BRIDGES = boot(S4_LAYERS, 'epci', '"nom_officiel" = \'Toulouse Métropole\'', 1.1, dense_scale=400000) \
    + scope('epci') + recorded_scene(1.1) \
    + pick_layer('troncon_hydrographique') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom('"persistance" = \'Permanent\'') + settle() + [
    (0, cam('full', dur=1.0)), hold(1200),
] + act('pushButton_exploring_identify', lambda: dock().pushButton_exploring_identify.click(),
        lead=700, after=100) + [
    hold(2600),
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['troncon_de_route', 'construction_lineaire']) + predicates(['cross']) + and_targets() + [
    (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + show_map(3500) + [(0, zoom_focus(0.22))] + settle() + show_map(4000, 1.05) \
    + ending(['troncon_de_route', 'construction_lineaire'])

S5_LAYERS = ['commune', 'foret_publique', 'zone_de_vegetation', 'zone_d_habitation', 'batiment', 'haie',
             'troncon_de_route']
WOOD_EXPR = ('"nature" IN (\'Bois\', \'Forêt fermée de feuillus\', \'Forêt fermée de conifères\', '
             '\'Forêt fermée mixte\', \'Forêt ouverte\')')

# brush (story 5): woodland and hedges within 50 m of a home in Bagnères-de-Luchon, then woods only.
BRUSH = boot(S5_LAYERS, 'commune', '"nom_officiel" = \'Bagnères-de-Luchon\'', 1.15) + scope('commune') \
    + recorded_scene(1.15) + pick_layer('batiment') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom('"usage_1" = \'Résidentiel\'') + settle() + [
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['zone_de_vegetation', 'haie']) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(50) + and_targets() + [
    (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + show_map(3000) + pick_layer('zone_de_vegetation') + [
    (1500, cam(EXPLORE_ZONE, dur=1.4, pad=30)),
] + typed_custom(WOOD_EXPR, per_char=18) + [
    (400, cam(FILTER_ZONE, dur=1.3, pad=40)),
] + act('pushButton_checkable_filtering_current_layer_combine_operator', combine('AND', None)) + [
    (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [(0, zoom_focus(0.35))] + settle() + show_map(4000, 1.05) + ending(['zone_de_vegetation', 'haie'])

S6_LAYERS = ['commune', 'zone_de_vegetation', 'zone_d_activite_ou_d_interet', 'zone_d_habitation', 'batiment',
             'troncon_de_route']
S6_SCOPE_TARGETS = ['zone_de_vegetation', 'batiment', 'troncon_de_route']
S6_TARGETS = ['zone_d_habitation', 'zone_d_activite_ou_d_interet']
PAVED_EXPR = '"nature" NOT IN (\'Chemin\', \'Sentier\', \'Escalier\', \'Piste cyclable\', \'Route empierrée\')'


def s6_processing_scope():
    import processing
    res = processing.run('filtermate:batch_filter', {'INPUT_LAYERS': [layer(n) for n in S6_TARGETS],
                                                     'EXPRESSION': '"insee_commune" = \'31020\''})
    log(f'processing result {res}')


# hamlets (story 6): places more than 200 m from any paved road in Aspet.
HAMLETS = boot(S6_LAYERS, 'commune', '"nom_officiel" = \'Aspet\'', 1.15) + scope('commune', S6_SCOPE_TARGETS) + [
    (500, s6_processing_scope), (3000, wait_idle()),
] + recorded_scene(1.15) + pick_layer('troncon_de_route') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom(PAVED_EXPR, per_char=22) + settle() + [
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(S6_TARGETS) + predicates(['disjoint']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(200) + and_targets() + [
    (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + show_map(4500, 1.05) + ending(S6_TARGETS)

FAV_NAME = 'PPRI Garonne 300 m'


def no_auto_zoom():
    """Skip FilterMate's zoom after applying a favorite during this recording.

    On the 2.9 GB GeoPackage it ends in layer.extent() on the main thread with a
    20,000-character subset and froze QGIS for minutes (2026-09-30); the scene
    restores its own framing anyway.
    """
    import filter_mate.adapters.auto_zoom as auto_zoom
    auto_zoom.auto_zoom_to_filtered = lambda *args, **kwargs: False


def fav_indicator():
    return dock().favorites_indicator_label


def fav_menu(hover, then=None, keep=1700):
    """Open the favorites menu under the star, glide to an entry, close it, then run `then`."""
    def _s():
        ind = fav_indicator()

        def place():
            m = QApplication.activePopupWidget()
            if m is None:
                log('favorites menu not found')
                return
            m.move(ind.mapToGlobal(QPoint(ind.width() - m.sizeHint().width(), ind.height() + 2)))
            entry = next((a for a in m.actions() if hover.lower() in a.text().lower()), None)
            log(f'menu entries {[a.text() for a in m.actions()]} -> {entry.text() if entry else None}')
            if entry is not None:
                r = to_main(m, m.actionGeometry(entry))
                REC.event('point', x=r.center().x(), y=r.center().y())
                QTimer.singleShot(900, lambda: (m.setActiveAction(entry),
                                                REC.event('click', x=r.center().x(), y=r.center().y())))
            QTimer.singleShot(keep, m.close)
        QTimer.singleShot(150, place)
        dock()._favorites_ctrl.handle_indicator_clicked()
        if then is not None:
            then()
    return _s


def fav_add():
    log(f'favorite added {dock()._favorites_ctrl.add_current_to_favorites(FAV_NAME)}')


def fav_apply():
    ctrl = dock()._favorites_ctrl
    for f in ctrl.get_all_favorites():
        if getattr(f, 'name', '') == FAV_NAME:
            log(f'apply favorite {f.id}: {ctrl.apply_favorite(f.id)}')
            return


def fav_cleanup():
    ctrl = dock()._favorites_ctrl
    for f in ctrl.get_all_favorites():
        if getattr(f, 'name', '') == FAV_NAME:
            log(f'remove favorite {f.id}: {ctrl.remove_favorite(f.id)}')


# favorites (story 7): save the 300 m result of story 3, clear everything, replay it.
FAVORITES = boot(S3_LAYERS, 'commune', '"nom_officiel" = \'Grenade\'', 1.2) + [(0, no_auto_zoom)] + scope('commune') + [
    (500, source('surface_hydrographique')), (2000, multi_mode), (3000, select_all_multi), hold(4000),
    (500, filtering_tab),
    (300, lambda: check_combo_items(dock().checkableComboBoxLayer_filtering_layers_to_filter, S3_FLOOD_TARGETS, True)),
    (300, refresh_targets),
    (300, lambda: check_combo_items(dock().comboBox_filtering_geometric_predicates, ['intersect'], True)),
    (300, buffer_value(300)), (300, combine(None, 'AND')),
    (500, click_filter), (3000, wait_idle()), hold(1500),
] + recorded_scene(1.2) + [
    (0, cam(['favorites_indicator_label', 'mGroupBox_exploring_single_selection'], dur=1.4, pad=30)),
] + act(fav_indicator, fav_menu('add', fav_add)) + [hold(1200)] + show_map(2200) + [
    (0, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + act('pushButton_action_unfilter', click_unfilter) + settle(3.0) + [(0, refocus)] + settle() + show_map(2600) + [
    (0, cam(['favorites_indicator_label', 'mGroupBox_exploring_single_selection'], dur=1.4, pad=30)),
] + act(fav_indicator, fav_menu(FAV_NAME, fav_apply)) + settle(3.0) + [(0, refocus)] + settle() + show_map(3500) + [
    (0, fav_cleanup)] + ending()

EXPORT_ZONE = ['pushButton_checkable_exporting_layers', 'pushButton_checkable_exporting_zip']


def folder_edit():
    return dock().lineEdit_exporting_output_folder


def export_with_recap():
    """Click Export; the recap dialog is modal, so a timer confirms it."""
    def confirm():
        from qgis.PyQt.QtWidgets import QPushButton
        w = getattr(dock(), '_export_recap_dialog', None) or QApplication.activeModalWidget()
        log(f'recap {w}')
        if w is None:
            return
        buttons = [b for b in w.findChildren(QPushButton) if b.isVisible()]
        ok = next((b for b in buttons if b.isDefault()), buttons[-1] if buttons else None)
        if ok is not None:
            r = rect_of(ok)
            REC.event('camera', rect=box(rect_of(w).adjusted(-30, -30, 30, 30)), dur=1.2, drift=1.0)
            QTimer.singleShot(1500, lambda: REC.event('point', x=r.center().x(), y=r.center().y()))
            QTimer.singleShot(2500, lambda: REC.event('click', x=r.center().x(), y=r.center().y()))
        QTimer.singleShot(2800, w.accept)
    QTimer.singleShot(1200, confirm)
    dock().pushButton_action_export.click()


def export_layers_changed():
    dock().checkableComboBoxLayer_exporting_layers.checkedItemsChangedEvent()


def export_datatype():
    set_combo_text(dock().comboBox_exporting_datatype, 'GPKG')


def export_zip():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    dock().lineEdit_exporting_zip.setText(os.path.join(EXPORT_DIR, 'saint_gaudens.zip'))


# export (story 1): the commune dossier as one GeoPackage with styles, zipped.
EXPORT = boot(S1_LAYERS, 'commune', '"nom_officiel" = \'Saint-Gaudens\'', 1.3) + scope('commune') \
    + recorded_scene(1.3) + [(0, cam('dock', dur=1.4, pad=10))] \
    + act(toolbox_button('export'), lambda: dock().toolBox_tabTools.setCurrentIndex(1)) + [
    (1200, cam(EXPORT_ZONE, dur=1.4, pad=40)),
] + act('pushButton_checkable_exporting_layers', enable('pushButton_checkable_exporting_layers')) \
    + combo_check('checkableComboBoxLayer_exporting_layers', S1_TARGETS, per_item=220) + [(200, export_layers_changed)] \
    + act('pushButton_checkable_exporting_projection', enable('pushButton_checkable_exporting_projection'), after=500) \
    + act('pushButton_checkable_exporting_styles', enable('pushButton_checkable_exporting_styles'), after=500) \
    + act('pushButton_checkable_exporting_datatype', enable('pushButton_checkable_exporting_datatype'), after=500) \
    + [(300, export_datatype)] \
    + act('pushButton_checkable_exporting_output_folder', enable('pushButton_checkable_exporting_output_folder')) \
    + act(folder_edit, lambda: folder_edit().clear()) + type_into(folder_edit, EXPORT_DIR, per_char=25, clear=False) \
    + act('pushButton_checkable_exporting_zip', enable('pushButton_checkable_exporting_zip')) + [(300, export_zip)] + [
    (400, cam(['pushButton_action_export', 'pushButton_checkable_exporting_zip'], dur=1.2, pad=40)),
] + act('pushButton_action_export', export_with_recap) + [hold(1500)] + settle(3.0) + show_map(3000) + ending()

S8_LAYERS = ['commune', 'batiment', 'troncon_hydrographique', 'troncon_de_route', 'erp']
S8_TARGETS = ['batiment', 'troncon_de_route', 'troncon_hydrographique', 'erp']
CHANGED_EXPR = '"date_modification" >= \'2025-03-15\''


def toolbox_dock():
    for d in iface.mainWindow().findChildren(QDockWidget):
        if d.objectName() == 'ProcessingToolbox':
            return d


def toolbox_search():
    return toolbox_dock().findChild(QLineEdit)


def show_toolbox():
    d = toolbox_dock()
    d.show()
    d.raise_()
    iface.mainWindow().resizeDocks([d], [360], Qt.Orientation.Horizontal)


def s8_dialog():
    import processing
    dlg = processing.createAlgorithmDialog('filtermate:batch_filter', {
        'INPUT_LAYERS': [layer(n) for n in S8_TARGETS], 'EXPRESSION': CHANGED_EXPR})
    dlg.resize(860, 640)
    mw = iface.mainWindow()
    dlg.move(mw.mapToGlobal(QPoint(420, 160)))
    dlg.show()
    STATE['proc'] = dlg
    REC.windows.append(dlg)


def run_button():
    from qgis.PyQt.QtWidgets import QPushButton
    dlg = STATE['proc']
    return next((b for b in dlg.findChildren(QPushButton) if b.isVisible() and b.text().replace('&', '') == 'Run'),
                dlg)


def s8_run():
    import processing
    REC.windows.remove(STATE['proc'])
    STATE['proc'].close()
    res = processing.run('filtermate:batch_filter', {'INPUT_LAYERS': [layer(n) for n in S8_TARGETS],
                                                     'EXPRESSION': CHANGED_EXPR})
    log(f'processing result {res}')


# processing (story 8): the batch filter of the Processing toolbox, department-wide.
# Toulouse framed tight and dense layers shown up to 1:200 000: at 1.6 x the commune the
# canvas was at 1:147 000 and the filtered buildings and roads were not drawn at all.
PROCESSING = boot(S8_LAYERS, 'commune', '"nom_officiel" = \'Toulouse\'', 1.0, dense_scale=200000) \
    + recorded_scene(1.0) + [
    (0, show_toolbox), (600, cam(lambda: rect_of(toolbox_dock()), dur=1.4, pad=20)),
] + act(toolbox_search) + type_into(toolbox_search, 'filtermate', per_char=120) + [
    hold(1200), (0, s8_dialog), (400, cam(lambda: rect_of(STATE['proc']), dur=1.4, pad=30)), hold(1500),
] + act(run_button, s8_run) + settle(3.0) + [(0, refocus)] + settle() + show_map(4500, 1.05) + ending(S8_TARGETS)

CLIPS = {'hero': HERO, 'explore': EXPLORE, 'buffer': BUFFER, 'noise': NOISE, 'bridges': BRIDGES,
         'brush': BRUSH, 'hamlets': HAMLETS, 'favorites': FAVORITES, 'export': EXPORT, 'processing': PROCESSING}
STEPS = CLIPS[CLIP]


def run_steps(i=0, tries=0):
    if i >= len(STEPS):
        return
    delay, fn = STEPS[i]

    # A step returning True is a wait: it is re-armed every 250 ms (100 s at most).
    def go():
        if tries == 0:
            log(f'--- step {i} {getattr(fn, "__name__", fn)}')
        again = False
        try:
            again = fn() is True
        except Exception:
            log(traceback.format_exc())
        if again and tries < 400:
            run_steps(i, tries + 1)
        else:
            run_steps(i + 1)
    QTimer.singleShot(delay if tries == 0 else 250, go)


log(f'clip {CLIP}, {len(STEPS)} steps')
QTimer.singleShot(15000, run_steps)
