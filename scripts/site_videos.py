# -*- coding: utf-8 -*-
"""Screen recordings of FilterMate in QGIS for the website background videos.

Usage (Windows QGIS driven from WSL or a Windows shell)::

    set FM_CLIP=hero
    set FM_VIDEO_OUT=C:\\Users\\Simon\\AppData\\Local\\Temp\\fm_video
    set FM_GPKG=C:\\Users\\Simon\\Documents\\bdtopo31\\BDT_3-5_GPKG_LAMB93_D031-ED2026-03-15.gpkg
    qgis-bin.exe --nologo --lang en --code scripts/site_videos.py

then ``scripts/site_video_render.py`` turns the recording into the MP4 and
poster used by the site. ``scripts/site_videos_headless.sh`` records the same
clips without a screen, in the Docker image of QGIS (nothing opens on the desk).

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
# light or dark: the QGIS theme of the recording profile (the site shows the one matching its own theme)
THEME = os.environ.get('FM_THEME', 'light').lower()
DARK = THEME == 'dark'
ROOT = os.environ.get('FM_VIDEO_OUT', r'C:\Users\Simon\AppData\Local\Temp\fm_video')
GPKG = os.environ.get('FM_GPKG', r'C:\Users\Simon\Documents\bdtopo31\BDT_3-5_GPKG_LAMB93_D031-ED2026-03-15.gpkg')
# FM_MEASURE=1: replay a scene for its logged counts only, no frame grabbed, in fm_video\\measure\\<clip>
# FM_PLACE_RIVER / FM_PLACE_NOISE / FM_PLACE_EXPORT: the commune of the buffer and favorites, noise and export clips
PLACE_RIVER = os.environ.get('FM_PLACE_RIVER', 'Grenade')
PLACE_NOISE = os.environ.get('FM_PLACE_NOISE', 'Muret')
PLACE_EXPORT = os.environ.get('FM_PLACE_EXPORT', 'Saint-Gaudens')
# FM_PG: a PostgreSQL connection ("host=... dbname=... user=... password=..."); the layers then come from PostGIS
PG = os.environ.get('FM_PG', '')
MEASURE = bool(os.environ.get('FM_MEASURE'))
OUT = os.path.join(ROOT, 'measure' if MEASURE else '', CLIP + ('-dark' if DARK else ''))
EXPORT_DIR = os.path.join(ROOT, 'export_out')
LOG = os.path.join(OUT, 'capture.log')
FPS = 15
WINDOW = (1760, 990)  # 16:9 client area, 2640x1485 frames at 150 % scaling
# The dock at the least width its normal profile allows (ui/config: min_width 380): the map gets the rest.
DOCK_WIDTH = int(os.environ.get('FM_DOCK_WIDTH', '380'))
# The window no taller than the dock needs (fit_window): FM_FIT=0 keeps the 1760 x 990 of the first takes.
FIT = os.environ.get('FM_FIT', '1') != '0'
MIN_WINDOW_HEIGHT = 720
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
    'parcelle': ('#2b3a42', 0.45, 0.0),
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
        if MEASURE:
            self.t0 = time.perf_counter()
            log('measure only: no frames')
            return
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
            if (mw.width(), mw.height()) != self.size:
                # A dock minimum can resize the window (seen when a point cloud panel shows up).
                log(f'window resized to {mw.width()}x{mw.height()}, back to {self.size}')
                mw.resize(*self.size)
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
        if MEASURE:
            log('stopped (measure only)')
            return
        self.timer.stop()
        duration = self.now()
        self.queue.put(None)
        self.thread.join()
        meta = {'clip': CLIP, 'theme': THEME, 'dpr': self.dpr, 'size': self.size, 'fps': FPS,
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
    def _s():
        REC.event('mark', name=name)
    _s.mark = name   # texted() finds the stills of a scene by their name
    return _s


def note(label, names):
    """Log the feature counts of layers under a label (the numbers quoted by the stories)."""
    def _s():
        out = {}
        for n in names:
            req = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry).setNoAttributes()
            out[n] = sum(1 for _ in layer(n).getFeatures(req))
        log(f'note {label} {out}')
    return (0, _s)


def note_expr(label, name, expr):
    """Log how many features of a (filtered) layer match an expression."""
    def _s():
        n = sum(1 for _ in layer(name).getFeatures(QgsFeatureRequest(QgsExpression(expr))))
        log(f'note {label} {{{name!r}: {n}}}')
    return (0, _s)


def still(name):
    """A step image of the stories, cut from the recording by site_video_render.py (img/stories/<name>.webp)."""
    return (0, mark('still:' + name))


# The English text of the edit, drawn by site_video_render.py over the picture.
def title(text):
    """The question of the take, kept in a corner of the edited video."""
    def _s():
        REC.event('title', text=text)
    _s.text = True
    return (0, _s)


def caption(text, style='step'):
    """One line at the bottom of the edited video, until the next one ('' clears it). 'N · text' numbers the step."""
    def _s():
        REC.event('caption', text=text, style=style)
    _s.text = True
    return (0, _s)


def result(template, names=()):
    """The line the take ends on, its counts read from the layers at that moment:
    '{batiment:,} buildings · {erp:,} public buildings'."""
    def _s():
        text = template.format(**counts(names)) if names else template
        REC.event('caption', text=text, style='result')
        log(f'result {text}')
    return (0, _s)


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


def zoom_rect(xmin, ymin, xmax, ymax):
    """Frame a map rectangle and keep it as the scene framing (refocus() returns to it)."""
    def _s():
        STATE['scene_rect'] = QgsRectangle(xmin, ymin, xmax, ymax)
        set_extent(STATE['scene_rect'])
    return _s


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
def prepare_window():
    """Recording window: fixed size, no developer docks or toolbars, plain canvas; returns the canvas."""
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
    quiet_message_bar()
    canvas = iface.mapCanvas()
    canvas.setRenderFlag(False)
    canvas.setCanvasColor(QColor('#1d2428' if DARK else '#f7f7f4'))
    canvas.setSelectionColor(QColor(255, 225, 0, 90))
    return canvas


def setup(layer_names, focus_layer, focus_expr, scale=1.25, dense_scale=120000):
    """Load layers (bottom to top) and zoom on the focus feature (scale=None: whole layer)."""
    def _s():
        canvas = prepare_window()
        # No feature counts in the Layers panel: counting per symbol walks the
        # whole department (1.2 M buildings) in a task holding the GeoPackage,
        # and froze the main thread for minutes in the first recordings.
        for name in layer_names:
            if PG:
                vl = QgsVectorLayer(f'{PG} key=\'fid\' table="public"."{name}" (geom)', name, 'postgres')
                log(f'postgres layer {name} valid={vl.isValid()} count={vl.featureCount()}')
            else:
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
        STATE['boot_extent'] = QgsRectangle(bb)
        set_extent(bb)
        canvas.setRenderFlag(True)
    return _s


def quiet_message_bar():
    """No QGIS notices (downloaded fonts...) in the footage: cleared before recording starts.

    Inspecting a message from the bar's widgetAdded signal crashed QGIS 4.2 (access violation
    while FilterMate pushed its success message), so the bar is only cleared.
    """
    iface.messageBar().clearWidgets()


def open_plugin():
    """Start FilterMate in the recording profile (a fresh profile has it installed, not enabled)."""
    import qgis.utils
    from qgis.PyQt.QtCore import QSettings
    settings = QSettings()
    settings.setValue('FilterMate/discord_welcome_dismissed', True)  # modal dialogs would block the steps
    settings.setValue('FilterMate/whats_new_seen', 99)
    if 'filter_mate' not in plugins:
        qgis.utils.updateAvailablePlugins()
        started = qgis.utils.loadPlugin('filter_mate') and qgis.utils.startPlugin('filter_mate')
        log(f'plugin started: {started}')
    plugins['filter_mate'].run()


def size_dock():
    """The dock as a new install shows it, DOCK_WIDTH wide: every section in it, EXPLORING and FILTERING open."""
    d = dock()
    panels = getattr(d, '_fm_panels', None)
    if panels is not None and panels.detached():
        log(f'sections apart at the start: {panels.groups()}, merged back')
        panels.attach_all()
    sections = getattr(d, '_fm_sections', None)
    if sections is not None:
        sections.open_top('exploring')
    d.toolBox_tabTools.setCurrentWidget(d.FILTERING)
    d.setMinimumWidth(0)
    iface.mainWindow().resizeDocks([d], [DOCK_WIDTH], Qt.Orientation.Horizontal)


def rows_need(pages=('FILTERING',), show=False):
    """The height the lower stack of the dock needs to show the rows of ``pages`` (FILTERING, EXPORTING) without a
    scroll bar: its rail, the tallest of them, their margins (as fit_stacks of scripts/guide_screenshots.py).
    ``show``: each page is opened to be measured, then the first one again (hidden, EXPORTING asked 56 px more than
    its rows take once shown)."""
    d = dock()
    sections = getattr(d, '_fm_sections', None)
    if sections is None:
        return 0
    tallest = 0
    for name in pages:
        page = getattr(d, name)
        if show:
            d.toolBox_tabTools.setCurrentWidget(page)
            QApplication.processEvents()
            if page.layout() is not None:
                page.layout().activate()
        tallest = max(tallest, page.sizeHint().height(), page.minimumSizeHint().height())
    if show and pages:
        d.toolBox_tabTools.setCurrentWidget(getattr(d, pages[0]))
        QApplication.processEvents()
    return sections.bottom_rail.height() + tallest + 22


def dock_void(pages=None, need=None):
    """The empty band of the dock: what its lower stack holds beyond the rows of ``pages``. A window taller than the
    dock needs shows it in every frame: under the rows when they are packed at the top of their section
    (SECTION_HEIGHT = fit), between them when they spread over its height (fill, the default). ``pages`` None: the
    band of the section the dock shows, read on that section (its viewport against what its rows ask), which also
    holds with the headers stacked; 0 for CONFIGURATION, whose tree takes the height it is given."""
    d = dock()
    if pages is None:
        page = d.toolBox_tabTools.currentWidget()
        if page is None or page not in (d.FILTERING, d.EXPORTING) or page.parentWidget() is None:
            return 0
        return page.parentWidget().height() - max(page.sizeHint().height(), page.minimumSizeHint().height())
    sizes = d.splitter_main.sizes()
    if need is None:
        need = rows_need(pages) if pages else 0
    return sizes[1] - need if need and len(sizes) > 1 else 0


def fit_stacks(pages=('FILTERING',), need=None):
    """The lower stack of the dock as tall as the rows of ``pages``, EXPLORING the rest; the dock is told that
    share, as a drag of the handle between them does (it comes back to it after AGENT was opened)."""
    d = dock()
    if need is None:
        need = rows_need(pages)
    total = sum(d.splitter_main.sizes())
    if 0 < need < total:
        d.splitter_main.setSizes([total - need, need])
        sections = getattr(d, '_fm_sections', None)
        if sections is not None and hasattr(sections, '_share'):
            sections._share = (total - need) / total


def fit_window(pages=('FILTERING',), spare=0):
    """Unrecorded: the window loses the height of the empty band of the dock, and the width that keeps it 16:9; the
    lower stack is then as tall as the rows of ``pages`` and EXPLORING keeps its height. The dock in one piece, no
    empty band, and a larger interface in the frame. The dock is told that share of its two stacks, as a drag of
    their handle does: it comes back to it after AGENT was opened. Nothing moves when there is no band to lose.
    ``spare``: pixels of that band the window keeps, given to EXPLORING (a take that sets a section apart needs the
    height of one more title bar and rail)."""
    def _s():
        if not FIT or not pages:
            return
        mw, d = iface.mainWindow(), dock()
        need = rows_need(pages, show=True)
        void = dock_void(pages, need)
        height = max(MIN_WINDOW_HEIGHT, mw.height() - max(0, void - spare))
        height -= height % 9
        if void > 0 and height < mw.height():
            mw.resize(height * 16 // 9, height)

        def stacks():
            if void > 0:
                fit_stacks(pages, need)
            mw.resizeDocks([d], [DOCK_WIDTH], Qt.Orientation.Horizontal)
            if STATE.get('boot_extent') is not None:
                set_extent(STATE['boot_extent'])
            QTimer.singleShot(500, lambda: log(
                f'window fitted: {mw.width()}x{mw.height()} (empty band was {void}), stacks '
                f'{d.splitter_main.sizes()}, rows need {need}, band left {dock_void(pages, need)}'))
        QTimer.singleShot(600, stacks)
    return _s


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


def combo_check(name, texts, per_item=380, close_after=700, lead=900, after=900):
    """Open a checkable combo, tick the wanted items one by one, close it."""
    return (act(name, open_combo(name), lead=lead, after=after) + check_one_by_one(name, texts, per_item)
            + [(close_after, hide_popup)])


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


def select_all_multi_menu(keep=1800):
    """Open the multiple-selection context menu and activate Select All."""
    def open_menu():
        picker, feature_list = multi_widget()
        menu = picker.context_menu
        r = rect_of(feature_list)
        menu.popup(iface.mainWindow().mapToGlobal(r.center()))
        if menu not in REC.windows:
            REC.windows.append(menu)

        def highlight():
            action = next(
                (a for a in menu.actions() if a.text().replace('&', '').strip() == 'Select All'),
                None,
            )
            if action is None:
                log(f'Select All action not found: {[a.text() for a in menu.actions()]}')
                menu.close()
                return
            STATE['multi_select_all_action'] = action
            ar = to_main(menu, menu.actionGeometry(action))
            REC.event('point', x=ar.center().x(), y=ar.center().y())
            menu.setActiveAction(action)

        def activate():
            action = STATE.pop('multi_select_all_action', None)
            if action is not None:
                ar = to_main(menu, menu.actionGeometry(action))
                REC.event('click', x=ar.center().x(), y=ar.center().y())
                action.trigger()
            menu.close()
            if menu in REC.windows:
                REC.windows.remove(menu)

        QTimer.singleShot(200, highlight)
        QTimer.singleShot(keep, activate)

    return act(lambda: multi_widget()[1], open_menu) + [hold(keep + 350)]


def custom_edit():
    return dock().mFieldExpressionWidget_exploring_custom_selection.findChild(QLineEdit)


def custom_mode():
    dock().mGroupBox_exploring_custom_selection.setChecked(True)


def typed_custom(expr, per_char=45):
    """Type a custom selection expression, then commit it like Enter would."""
    return act(custom_edit, custom_mode) + type_into(custom_edit, expr, per_char) + [(400, custom(expr))]


SECTION_KEYS = ('agent', 'exploring', 'filtering', 'exporting', 'configuration')


def section_key(text):
    return next(key for key in SECTION_KEYS if key.startswith(text.lower()[:5]))


def chip(key, holder=None):
    """The chip of a section in the rail of the dock (or of the panel ``holder``)."""
    if holder is not None:
        return holder.rail.chip(key)
    sections = dock()._fm_sections
    rail = sections.top_rail if key in ('agent', 'exploring') else sections.bottom_rail
    return rail.chip(key)


def toolbox_button(text):
    """What opens the Filtering / Exporting / Configuration page: its chip in the rail of the dock (the default since
    5.1), or its header in the tool box when the headers are stacked (APP.DOCKWIDGET.SECTION_HEADERS)."""
    def _r():
        from qgis.PyQt.QtWidgets import QAbstractButton
        sections = getattr(dock(), '_fm_sections', None)
        if sections is not None and not sections.stacked:
            return rect_of(chip(section_key(text)))
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
            QTimer.singleShot(1500, lambda: REC.event('mark', name='still:s2-02'))  # story 2 step image
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
    quiet_message_bar()
    REC.start()


def stop_recording():
    faulthandler.cancel_dump_traceback_later()
    REC.stop()
    try:  # read before a take is published: a dock in one piece, with no empty band
        mw = iface.mainWindow()
        panels = getattr(dock(), '_fm_panels', None)
        log(f'layout at the end: window {mw.width()}x{mw.height()}, dock {dock().width()}x{dock().height()}, '
            f'empty band {dock_void()}, sections apart {panels.detached() if panels is not None else ()}, '
            f'rows {dock().property("fm_section_height") or "?"}')
    except Exception:
        log(traceback.format_exc())


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
    if STATE.get('scene_rect') is not None:
        set_extent(STATE['scene_rect'])
    elif STATE.get('scene_scale'):
        zoom_focus(STATE['scene_scale'])()


def filtered():
    """Nothing to do: the place in a scene where a filter is over (texted() puts the result line there)."""
    return None


def run_filter(fast=4.0):
    """Click Filter, fast-forward while the task runs, restore the framing, let the canvas redraw."""
    return act('pushButton_action_filter', click_filter) + [
        (300, speed(fast)), (1500, wait_idle()), (0, refocus), (600, wait_idle()), (400, speed(1.0)), (0, filtered),
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


def boot(layers, focus_layer, focus_expr, scale=1.25, dense_scale=120000, fit=('FILTERING',), spare=0):
    """``fit``: the sections of the lower stack the take opens; the window is fitted to the tallest (fit_window,
    which keeps ``spare`` pixels more)."""
    return [(1000, setup(layers, focus_layer, focus_expr, scale, dense_scale)),
            (3000, open_plugin), (8000, size_dock), (1500, wait_idle()),
            (500, fit_window(fit, spare)), (2500, wait_idle())]


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


def targets(names, per_item=300, close_after=700, lead=900, after=900):
    return (act('pushButton_checkable_filtering_layers_to_filter',
                enable('pushButton_checkable_filtering_layers_to_filter'), lead=lead, after=after)
            + combo_check(TARGETS, names, per_item=per_item, close_after=close_after, lead=lead, after=after)
            + [(200, refresh_targets)])


def predicates(names, per_item=380, close_after=700, lead=900, after=900):
    return (act('pushButton_checkable_filtering_geometric_predicates',
                enable('pushButton_checkable_filtering_geometric_predicates'), lead=lead, after=after)
            + combo_check(PREDICATES, names, per_item=per_item, close_after=close_after, lead=lead, after=after))


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
    still('s1-01'), (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(S1_TARGETS) + predicates(['intersect']) + [
    (200, buffer_off), hold(500), still('s1-02'), (400, cam(ACTION_ZONE, dur=1.3, pad=40)),
] + run_filter() + [
    (200, cam('canvas', dur=1.8, drift=1.05)), hold(2500), still('s1-03'), hold(1700),
    (0, cam('layers', dur=1.4)), hold(2600),
] + ending(S1_TARGETS)

# metropole (teaser 5.1.1): from the whole department to Toulouse Métropole, then one click filters 12 layers.
SM_LAYERS = ['epci'] + S1_TARGETS
METROPOLE = boot(SM_LAYERS, 'epci', '"nom_officiel" = \'Toulouse Métropole\'', scale=None, dense_scale=400000) + [
    (0, restyle('epci', (138, 143, 134, 30), '#6b7280', 0.8, selection_alpha=140)),
    (500, source('epci')), (1500, single_mode(tracking=True, selecting=True)), (1500, filtering_tab),
    (1000, rec_start), (0, cam('full', dur=0, drift=1.04)),
    (1200, cam(EXPLORE_ZONE, dur=1.6, pad=30)),
] + act(picker_edit) + type_into(picker_edit, 'Toulouse M', per_char=140) + [
    (900, pick_focus)] + settle() + show_map(2600, 1.03) + [
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(S1_TARGETS) + predicates(['intersect']) + [
    (200, buffer_off), hold(500), (400, cam(ACTION_ZONE, dur=1.3, pad=40)),
] + run_filter() + [
    (200, cam('canvas', dur=1.8, drift=1.05)), hold(2500), hold(1700),
    (0, cam('layers', dur=1.4)), hold(2600),
] + ending(S1_TARGETS)

# explore: the three exploring modes on the communes of the department.
EXPLORE_LAYERS = ['epci', 'commune', 'surface_hydrographique', 'troncon_hydrographique']
EXPLORE = boot(EXPLORE_LAYERS, 'commune', '"nom_officiel" = \'Toulouse\'', scale=None) + [
    (0, restyle('commune', (138, 143, 134, 40), '#5b636b', 0.5, selection_alpha=180)),
    (0, restyle('epci', None, '#39474f', 1.2)),
    (500, source('commune')), (1500, single_mode(tracking=True)), (1000, rec_start),
    (0, cam('full', dur=0, drift=1.03)),
    title('Three ways to pick features'), caption('1 · Single selection: type a name, the map follows'),
    (1000, cam(EXPLORE_ZONE, dur=1.5, pad=30)),
] + act('pushButton_checkable_exploring_selecting', enable('pushButton_checkable_exploring_selecting')) \
    + act(picker_edit) + type_into(picker_edit, 'Toulou', per_char=150) + [
    (900, pick_focus)] + settle() + show_map(2800) + [
    caption('2 · Multiple selection: tick several'),
    (0, cam(['mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection'], dur=1.4, pad=30)),
] + act(gb_check('mGroupBox_exploring_multiple_selection'), multi_mode) + [hold(1500)] + [
    (0, cam('mGroupBox_exploring_multiple_selection', dur=1.2, pad=30)),
] + multi_check(['Blagnac', 'Colomiers', 'Tournefeuille', 'Balma']) + settle() + show_map(3000) + [
    caption('3 · Custom selection: any expression'), (0, cam(EXPLORE_ZONE, dur=1.4, pad=30)),
] + typed_custom('"population" > 20000') + [caption('4 · Selecting and Zoom: straight to the result')] \
    + act('pushButton_checkable_exploring_selecting', enable('pushButton_checkable_exploring_selecting', False)) \
    + act('pushButton_checkable_exploring_selecting', enable('pushButton_checkable_exploring_selecting'), after=500) \
    + act('pushButton_exploring_zoom', lambda: dock().pushButton_exploring_zoom.click()) \
    + settle() + show_map(3200) + ending()

S3_LAYERS = ['commune', 'zone_d_habitation', 'surface_hydrographique', 'batiment', 'troncon_hydrographique',
             'troncon_de_route', 'erp']
S3_FLOOD_TARGETS = ['batiment', 'erp', 'troncon_de_route']

# buffer (story 3): what the Garonne can reach in Grenade (FM_PLACE_RIVER), 300 m then 100 m, then Undo.
BUFFER = boot(S3_LAYERS, 'commune', f'"nom_officiel" = \'{PLACE_RIVER}\'', 1.2) + scope('commune') + recorded_scene(1.2) \
    + pick_layer('surface_hydrographique') + [
    (1200, cam(['mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection'], dur=1.4, pad=30)),
] + act(gb_check('mGroupBox_exploring_multiple_selection'), multi_mode) + [
    hold(2500),
] + select_all_multi_menu() + [hold(400), still('s3-01'), (0, cam(FILTER_ZONE, dur=1.4, pad=40))] \
    + targets(S3_FLOOD_TARGETS) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(300) + and_targets() + [
    hold(500), still('s3-02'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [note('300 m', S3_FLOOD_TARGETS)] + show_map(3500) + [
    still('s3-03'), (0, cam(FILTER_ZONE, dur=1.3, pad=40)),
] + typed_buffer(100) + [(300, cam(ACTION_ZONE, dur=1.0, pad=40))] + run_filter() + [
    note('100 m', S3_FLOOD_TARGETS)] + show_map(3000) + [
    still('s3-04'), (0, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + act('pushButton_action_undo_filter', click_undo) + settle(4.0) + [(0, refocus)] + settle() + show_map(3000) \
    + [still('s3-05')] \
    + ending(S3_FLOOD_TARGETS)


# compare: the water of Blagnac and 100 m around (300 m in the teaser of 5.1.1), then Compare: before left of the line,
# after right.
def swipe_item():
    for it in iface.mapCanvas().scene().items():
        if type(it).__name__ == 'SwipeItem':
            return it
    return None


def swipe_to(fraction):
    def _s():
        it = swipe_item()
        if it is None:
            log('no swipe item')
            return
        it.set_fraction(fraction)
        canvas = iface.mapCanvas()
        r = to_main(canvas, QRect(int(canvas.width() * fraction), canvas.height() // 2, 1, 1))
        REC.event('point', x=r.center().x(), y=r.center().y())
    return _s


def swipe_ready():
    def _s():
        it = swipe_item()
        return it is None or it.busy
    _s.max_tries = 120
    return _s


def sweep(a, b, ms=2600, steps=40):
    return [(ms // steps, swipe_to(a + (b - a) * (i + 1) / steps)) for i in range(steps)]


def compare_button():
    return dock().findChild(QPushButton, 'pushButton_action_compare')


def click_compare():
    compare_button().click()


# The filter is set up and run before the recording (story 3 shows how); the take is Compare itself.
COMPARE = boot(S3_LAYERS, 'commune', '"nom_officiel" = \'Blagnac\'', 1.2) + scope('commune') + [
    (500, source('surface_hydrographique')), (2000, multi_mode), (3000, select_all_multi), hold(4000),
    (500, filtering_tab),
    # The rows of FILTERING are kept per source layer: the targets and the predicates are switched on for this one
    # (without it the task filters the source only, in 0.01 s, and the take shows the scope instead of the band).
    (300, enable('pushButton_checkable_filtering_layers_to_filter')),
    (300, lambda: check_combo_items(dock().checkableComboBoxLayer_filtering_layers_to_filter, S3_FLOOD_TARGETS, True)),
    (300, refresh_targets),
    (300, enable('pushButton_checkable_filtering_geometric_predicates')),
    (300, lambda: check_combo_items(dock().comboBox_filtering_geometric_predicates, ['intersect'], True)),
    (300, buffer_value(100)), (300, combine(None, 'AND')),
    (500, click_filter), (3000, wait_idle()), hold(1500), note('staged 100 m', S3_FLOOD_TARGETS),
] + recorded_scene(1.2) + [title('Before and after, side by side'),
                           caption('1 · A filter is on: 100 m around the water')] + show_map(2200) + [
    caption('2 · Click Compare'), (0, quiet_message_bar), (0, cam(ACTION_ZONE, dur=1.2, pad=40))] \
    + act(compare_button, click_compare) + [
    (500, swipe_ready()), caption('3 · Drag the line: before on the left, after on the right'),
    (0, cam('canvas', dur=1.4)), hold(1000)] \
    + sweep(0.5, 0.15) + [hold(600)] + sweep(0.15, 0.85, ms=3600, steps=56) + [hold(600)] + sweep(0.85, 0.5, ms=1800, steps=28) \
    + [hold(1000), caption('4 · Click Compare again to close'), (0, lambda: log(f'swipe item {swipe_item()} busy={getattr(swipe_item(), "busy", None)}')),
       (0, cam(ACTION_ZONE, dur=1.2, pad=40))] \
    + act(compare_button, click_compare) + [hold(800)] + ending(S3_FLOOD_TARGETS)


# postgis (teaser 5.1.1): the same question on PostGIS layers (FM_PG): the Garonne and 300 m around in Blagnac.
def dock_head():
    r = rect_of(dock())
    return QRect(r.x(), r.y(), r.width(), 360)


POSTGIS = boot(S3_LAYERS, 'commune', '"nom_officiel" = \'Blagnac\'', 1.2) + scope('commune') + recorded_scene(1.2) \
    + pick_layer('surface_hydrographique') + [
    (1200, cam(dock_head, dur=1.4, pad=10)), hold(2200),
    (0, cam(['mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection'], dur=1.2, pad=30)),
] + act(gb_check('mGroupBox_exploring_multiple_selection'), multi_mode) + [
    hold(1200),
] + select_all_multi_menu() + [hold(400), (0, cam(FILTER_ZONE, dur=1.4, pad=40))] \
    + targets(S3_FLOOD_TARGETS) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(300) + and_targets() + [
    hold(500), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [(0, quiet_message_bar)] + show_map(3500) + [(0, cam(dock_head, dur=1.3, pad=10)), hold(2200)] \
    + ending(S3_FLOOD_TARGETS)

S2_LAYERS = ['commune', 'zone_d_habitation', 'batiment', 'troncon_de_voie_ferree', 'troncon_de_route', 'erp']
NOISE_EXPR = 'CASE WHEN "importance" = \'1\' THEN 300 WHEN "importance" = \'2\' THEN 250 ELSE 100 END'

# noise (story 2): buildings exposed to major-road noise in Muret, buffer by expression.
NOISE = boot(S2_LAYERS, 'commune', f'"nom_officiel" = \'{PLACE_NOISE}\'', 1.2) + scope('commune') + recorded_scene(1.2) \
    + pick_layer('troncon_de_route') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom('"importance" IN (\'1\', \'2\')') + settle() + show_map(2400) + [
    note_expr('major roads', 'troncon_de_route', '"importance" IN (\'1\', \'2\')'),
    still('s2-01'), (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['batiment', 'erp']) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) \
    + act('mPropertyOverrideButton_filtering_buffer_value_property', buffer_expr_dialog(NOISE_EXPR),
          lead=900, after=900) \
    + combo_choose('comboBox_filtering_buffer_type', 'Flat') \
    + and_targets() + [hold(500), still('s2-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40))] + run_filter() \
    + show_map(3500) + [still('s2-04'), (0, zoom_focus(0.5))] + settle() + show_map(3500, 1.05) + [still('s2-05')] \
    + ending(['batiment', 'erp', 'troncon_de_route'])

S4_LAYERS = ['epci', 'commune', 'surface_hydrographique', 'troncon_hydrographique', 'troncon_de_route',
             'construction_lineaire']

# bridges (story 4): roads and structures crossing a permanent watercourse in Toulouse Métropole.
BRIDGES = boot(S4_LAYERS, 'epci', '"nom_officiel" = \'Toulouse Métropole\'', 1.1, dense_scale=400000) \
    + scope('epci') + recorded_scene(1.1) \
    + pick_layer('troncon_hydrographique') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom('"persistance" = \'Permanent\'') + settle() + [
    note('scope', ['troncon_de_route', 'troncon_hydrographique', 'construction_lineaire', 'commune']),
    note_expr('permanent', 'troncon_hydrographique', '"persistance" = \'Permanent\''),
    still('s4-01'), (0, cam('full', dur=1.0)), hold(1200),
] + act('pushButton_exploring_identify', lambda: dock().pushButton_exploring_identify.click(),
        lead=700, after=100) + [
    hold(900), still('s4-02'), hold(1700),
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['troncon_de_route', 'construction_lineaire']) + predicates(['cross']) + and_targets() + [
    hold(500), still('s4-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + show_map(3500) + [still('s4-04'), (0, zoom_focus(0.22))] + settle() + show_map(4000, 1.05) \
    + [still('s4-05')] \
    + ending(['troncon_de_route', 'construction_lineaire'])

S5_LAYERS = ['commune', 'foret_publique', 'zone_de_vegetation', 'zone_d_habitation', 'batiment', 'haie',
             'troncon_de_route']
WOOD_EXPR = ('"nature" IN (\'Bois\', \'Forêt fermée de feuillus\', \'Forêt fermée de conifères\', '
             '\'Forêt fermée mixte\', \'Forêt ouverte\')')

# brush (story 5): woodland and hedges within 50 m of a home in Bagnères-de-Luchon, then woods only.
BRUSH = boot(S5_LAYERS, 'commune', '"nom_officiel" = \'Bagnères-de-Luchon\'', 1.15) + scope('commune') \
    + recorded_scene(1.15) + pick_layer('batiment') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom('"usage_1" = \'Résidentiel\'') + settle() + [
    note('scope', ['batiment', 'zone_de_vegetation', 'haie']),
    note_expr('homes', 'batiment', '"usage_1" = \'Résidentiel\''),
    still('s5-01'), (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['zone_de_vegetation', 'haie']) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(50) + and_targets() + [
    (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [note('50 m', ['zone_de_vegetation', 'haie'])] + show_map(3000) + [still('s5-02')] \
    + pick_layer('zone_de_vegetation') + [
    (1500, cam(EXPLORE_ZONE, dur=1.4, pad=30)),
] + typed_custom(WOOD_EXPR, per_char=18) + [
    (400, cam(FILTER_ZONE, dur=1.3, pad=40)),
] + act('pushButton_checkable_filtering_current_layer_combine_operator', combine('AND', None)) + [
    hold(500), still('s5-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [(0, zoom_focus(0.35))] + settle() + show_map(4000, 1.05) + [still('s5-04')] \
    + ending(['zone_de_vegetation', 'haie'])

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
] + recorded_scene(1.15) + [note('scope', S6_TARGETS + ['troncon_de_route']), still('s6-01')] \
    + pick_layer('troncon_de_route') + [(1500, cam(EXPLORE_ZONE, dur=1.4, pad=30))] \
    + typed_custom(PAVED_EXPR, per_char=22) + settle() + [
    note_expr('paved', 'troncon_de_route', PAVED_EXPR), still('s6-02'),
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(S6_TARGETS, per_item=650, close_after=1200) \
    + predicates(['disjoint'], per_item=900, close_after=1200) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(200) + and_targets() + [
    hold(500), still('s6-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + show_map(4500, 1.05) + [still('s6-04')] + ending(S6_TARGETS)

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
FAVORITES = boot(S3_LAYERS, 'commune', f'"nom_officiel" = \'{PLACE_RIVER}\'', 1.2) + [(0, no_auto_zoom)] + scope('commune') + [
    (500, source('surface_hydrographique')), (2000, multi_mode), (3000, select_all_multi), hold(4000),
    (500, filtering_tab),
    # The rows of FILTERING are kept per source layer: the targets and the predicates are switched on for this one
    # (without it the task filters the source only, in 0.01 s, and the take shows the scope instead of the band).
    (300, enable('pushButton_checkable_filtering_layers_to_filter')),
    (300, lambda: check_combo_items(dock().checkableComboBoxLayer_filtering_layers_to_filter, S3_FLOOD_TARGETS, True)),
    (300, refresh_targets),
    (300, enable('pushButton_checkable_filtering_geometric_predicates')),
    (300, lambda: check_combo_items(dock().comboBox_filtering_geometric_predicates, ['intersect'], True)),
    (300, buffer_value(300)), (300, combine(None, 'AND')),
    (500, click_filter), (3000, wait_idle()), hold(1500), note('staged 300 m', S3_FLOOD_TARGETS),
] + recorded_scene(1.2) + [
    (0, cam(['favorites_indicator_label', 'mGroupBox_exploring_single_selection'], dur=1.4, pad=30)),
] + act(fav_indicator, fav_menu('add', fav_add)) + [(1000, mark('still:s7-01')), hold(200)] + show_map(2200) + [
    (0, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + act('pushButton_action_unfilter', click_unfilter) + settle(3.0) + [(0, refocus)] + settle() + show_map(2600) + [
    still('s7-02'),
    (0, cam(['favorites_indicator_label', 'mGroupBox_exploring_single_selection'], dur=1.4, pad=30)),
] + act(fav_indicator, fav_menu(FAV_NAME, fav_apply)) + [(1000, mark('still:s7-03'))] + settle(3.0) + [(0, refocus)] + settle() + show_map(3500) + [
    still('s7-04'), (0, fav_cleanup)] + ending(S3_FLOOD_TARGETS)

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
    dock().lineEdit_exporting_zip.setText(os.path.join(EXPORT_DIR, PLACE_EXPORT.lower().replace('-', '_').replace(' ', '_') + '.zip'))


# export (story 1): the commune dossier as one GeoPackage with styles, zipped.
EXPORT = boot(S1_LAYERS, 'commune', f'"nom_officiel" = \'{PLACE_EXPORT}\'', 1.3) + scope('commune') \
    + recorded_scene(1.3) + [note('scope', S1_TARGETS), (0, cam('dock', dur=1.4, pad=10))] \
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
    hold(900), still('s1-04'),
] + act('pushButton_action_export', export_with_recap) + [(2400, mark('still:s1-05'))] + settle(3.0) + show_map(3000) \
    + ending()

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
    """Unrecorded: the Processing toolbox under the Layers panel, left of the map. (Above the dock of FilterMate it
    took half of the dock's column: the dock was squeezed to 360 px by 600 and the window could not be fitted.)
    The two share the height the Layers panel had: given more, they made the window 45 px taller than its 16:9."""
    mw, d = iface.mainWindow(), toolbox_dock()
    size = (mw.width(), mw.height())
    layers = mw.findChild(QDockWidget, 'Layers')
    column = layers.height() if layers is not None else 0
    d.show()
    if layers is not None:
        mw.splitDockWidget(layers, d, Qt.Orientation.Vertical)
        mw.resizeDocks([layers, d], [190, max(column - 196, 240)], Qt.Orientation.Vertical)
        mw.resizeDocks([layers], [330], Qt.Orientation.Horizontal)
    mw.resizeDocks([dock()], [DOCK_WIDTH], Qt.Orientation.Horizontal)

    def settle():
        if (mw.width(), mw.height()) != size:
            mw.resize(*size)
        # the window grew and came back: the stacks of the dock moved by 19 px on the way
        QTimer.singleShot(250, fit_stacks)
        QTimer.singleShot(600, lambda: log(
            f'toolbox {rect_of(d)}, dock {rect_of(dock())}, map {rect_of(iface.mapCanvas())}, '
            f'window {mw.width()}x{mw.height()} (fitted {size[0]}x{size[1]}), stacks {dock().splitter_main.sizes()}'))
    QTimer.singleShot(600, settle)


def s8_dialog():
    import processing
    dlg = processing.createAlgorithmDialog('filtermate:batch_filter', {
        'INPUT_LAYERS': [layer(n) for n in S8_TARGETS], 'EXPRESSION': CHANGED_EXPR})
    dlg.resize(860, 640)
    mw = iface.mainWindow()
    dlg.move(mw.mapToGlobal(QPoint(345, 130)))
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
    + [(0, show_toolbox), (2500, wait_idle())] + recorded_scene(1.0) + [
    (600, cam(lambda: rect_of(toolbox_dock()), dur=1.4, pad=20)),
] + act(toolbox_search) + type_into(toolbox_search, 'filtermate', per_char=120) + [
    hold(1200), still('s8-01'), (0, s8_dialog), (400, cam(lambda: rect_of(STATE['proc']), dur=1.4, pad=30)), hold(2800),
    still('s8-02'),
] + act(run_button, s8_run) + settle(3.0) + [(0, refocus)] + settle() + show_map(4500, 1.05) + [still('s8-03')] \
    + ending(S8_TARGETS)


# ------------------------------------------------------------------ FilterMate 5: raster and LiDAR
# Fenouillet / Saint-Alban (Toulouse Métropole, since November 2026; Estavar before): one square kilometre,
# 571000-572000 x 6289000-6290000, cut from the IGN LiDAR HD (COPC), the DTM interpolated from its ground points
# (0.5 m), its slope in percent, BD TOPO and Etalab cadastre. The files keep the names they had for Estavar
# (mnt_village.tif, pente_village.tif, estavar.gpkg, estavar_village.copc.laz); scripts/site_videos.sh documents
# how the Estavar ones were made, the Toulouse Métropole ones come from the same steps on another square.
FM5_DIR = os.environ.get('FM5_DIR', os.path.join(ROOT, 'data'))
FM5_DTM = os.path.join(FM5_DIR, 'mnt_village.tif')
FM5_SLOPE = os.path.join(FM5_DIR, 'pente_village.tif')
FM5_GPKG = os.path.join(FM5_DIR, 'estavar.gpkg')
FM5_TILE = os.path.join(FM5_DIR, 'estavar_village.copc.laz')
# FM5_EXTENT ("xmin,ymin,xmax,ymax"), FM5_DTM_RANGE ("low,high" in metres), FM5_SLOPE_MIN (%), FM5_HEIGHT (m),
# FM5_SURVEY_EXPR, FM5_SURVEY_RECT, FM5_SURVEY_ZIP: another square kilometre than Fenouillet (Estavar was
# 617000,6152100,618000,6153100 with 1200,1315, slope 30, height 9, "nature" = 'Eglise', 617207,6152391,617507,6152691)
FM5_EXTENT = tuple(float(v) for v in os.environ.get('FM5_EXTENT', '571000,6289000,572000,6290000').split(','))
_DTM_LOW, _DTM_HIGH = (float(v) for v in os.environ.get('FM5_DTM_RANGE', '122,135').split(','))
# The square is flat (122-135 m): the steep ground is the embankments and banks, 15 % rather than the 30 % of Estavar.
FM5_SLOPE_MIN = float(os.environ.get('FM5_SLOPE_MIN', '15'))
DTM_COLORS = [(round(_DTM_LOW + f * (_DTM_HIGH - _DTM_LOW), 1), c) for f, c in
              ((0.0, '#3f7d4f'), (0.217, '#8fb46a'), (0.435, '#d8d39a'), (0.696, '#c8a27a'), (1.0, '#f3efe8'))]
FM5_STYLE = {'troncon_de_route': ('#e07b24', 1.1, 1.0)}  # readable on the hillshade, light or dark
SLOPE_COLORS = [(0, '#f4f1e4'), (15, '#e8d48c'), (30, '#de8f3c'), (60, '#ad3a2c'), (100, '#5c1a22')]


# The buildings of Fenouillet cover the square (a commercial zone): grey where they are only the setting.
FM5_QUIET_BUILDINGS = [(0, restyle('batiment', (150, 150, 150, 150), '#6b6b6b', 0.2))]


def ramp_layer(path, name, colors, opacity):
    from qgis.core import (QgsColorRampShader, QgsRasterLayer, QgsRasterShader,
                           QgsSingleBandPseudoColorRenderer)
    rl = QgsRasterLayer(path, name, 'gdal')
    fn = QgsColorRampShader(colors[0][0], colors[-1][0])
    fn.setClip(False)
    fn.setColorRampItemList([QgsColorRampShader.ColorRampItem(v, QColor(c), f'{v}') for v, c in colors])
    shader = QgsRasterShader()
    shader.setRasterShaderFunction(fn)
    renderer = QgsSingleBandPseudoColorRenderer(rl.dataProvider(), 1, shader)
    # The bounds of the ramp: unset, the legend of the layer tree reads "nan" (seen in the take of story 15).
    renderer.setClassificationMin(colors[0][0])
    renderer.setClassificationMax(colors[-1][0])
    renderer.setOpacity(opacity)
    rl.setRenderer(renderer)
    return rl


def hillshade_layer(name):
    from qgis.core import QgsHillshadeRenderer, QgsRasterLayer
    rl = QgsRasterLayer(FM5_DTM, name, 'gdal')
    renderer = QgsHillshadeRenderer(rl.dataProvider(), 1, 315.0, 40.0)
    renderer.setZFactor(1.6)
    if DARK:
        renderer.setOpacity(0.55)
    rl.setRenderer(renderer)
    return rl


def style_point_cloud(pc=None, hidden=(0, 1, 2, 7, 18, 64, 65, 66, 67)):
    """Classified rendering without the ground and unclassified points: the hillshade shows through.

    Built here: at load time the layer only has the provisional extent renderer. ``hidden``: the classes not drawn.
    """
    try:
        from qgis.core import QgsPointCloudClassifiedRenderer
        pc = pc or layer('lhd')
        renderer = QgsPointCloudClassifiedRenderer('Classification', QgsPointCloudClassifiedRenderer.defaultCategories())
        categories = renderer.categories()
        for category in categories:
            if category.value() in hidden:
                category.setRenderState(False)
        renderer.setCategories(categories)
        renderer.setPointSize(1.6)
        pc.setRenderer(renderer)
        pc.triggerRepaint()
    except Exception:
        log(traceback.format_exc())


def setup5(layer_names, hidden=(), margin=1.03):
    """Load the Estavar layers (bottom to top), hide `hidden` in the legend, frame the square kilometre."""
    def _s():
        canvas = prepare_window()
        for name in layer_names:
            if name == 'hillshade':
                ml = hillshade_layer(name)
            elif name == 'mnt':
                ml = ramp_layer(FM5_DTM, name, DTM_COLORS, 0.62)
            elif name == 'pente':
                ml = ramp_layer(FM5_SLOPE, name, SLOPE_COLORS, 0.72)
            elif name in ('ortho', 'ortho_rvb', 'ortho_irc'):
                from qgis.core import QgsRasterLayer
                ml = QgsRasterLayer(os.path.join(FM5_DIR, 'ortho_irc.tif' if name == 'ortho_irc' else 'ortho_rvb.tif'),
                                    name, 'gdal')
            elif name == 'lhd':
                from qgis.core import QgsPointCloudLayer
                ml = QgsPointCloudLayer(FM5_TILE, name, 'copc')
            else:
                ml = QgsVectorLayer(f'{FM5_GPKG}|layername={name}', name, 'ogr')
                ml.setLabelsEnabled(False)
                style_layer(ml, FM5_STYLE.get(name, STYLE.get(name)))
            log(f'layer {name} valid={ml.isValid()}')
            QgsProject.instance().addMapLayer(ml)
            if name in hidden:
                node = QgsProject.instance().layerTreeRoot().findLayer(ml.id())
                node.setItemVisibilityChecked(False)
        bb = QgsRectangle(*FM5_EXTENT)
        bb.scale(margin)
        STATE['scene_rect'] = QgsRectangle(bb)
        STATE['boot_extent'] = QgsRectangle(bb)
        set_extent(bb)
        canvas.setRenderFlag(True)
    return _s


def boot5(layers, hidden=(), fit=('FILTERING',)):
    return [(1000, setup5(layers, hidden)), (3000, open_plugin), (8000, size_dock), (1500, wait_idle()),
            (500, fit_window(fit)), (2500, wait_idle())]


def coverage():
    return dock()._controller_integration.coverage_controller


def wait_current(name):
    """Re-armed until FilterMate shows the EXPLORING page of the raster / point cloud `name`."""
    since = []

    def _s():
        if not since:
            since.append(time.time())
        active = coverage().active_layer
        ready = active is not None and active.name() == name and not tasks_running()
        return not (ready and time.time() - since[0] > 2.0)
    return _s


def wait_long():
    """wait_idle() for minutes, not 100 s: PDAL computes the height above ground first."""
    fn = wait_idle()
    fn.max_tries = 4 * 60 * 10
    return fn


def coverage_host():
    return dock().findChild(QWidget, 'stackedWidget_exploring_coverage')


def group_check(get_group):
    """The check box in the title of a panel group box."""
    def _r():
        r = rect_of(get_group())
        return QRect(r.x() + 4, r.y() + 2, 26, 24)
    return _r


def open_group(get_group):
    def _s():
        g = get_group()
        g.setChecked(True)
        if hasattr(g, 'setCollapsed'):
            g.setCollapsed(False)
    return _s


def raster_panel():
    return coverage()._raster_panel


def pc_panel():
    return coverage()._pc_panel


def spin_line(get_spin):
    return lambda: get_spin().findChild(QLineEdit)


def ensure_visible(get_widget, margin=40):
    """Scroll the EXPLORING area so a widget is in view (the dock is shorter than the panels)."""
    def _s():
        from qgis.PyQt.QtWidgets import QScrollArea
        w = get_widget()
        p = w.parentWidget()
        while p is not None and not isinstance(p, QScrollArea):
            p = p.parentWidget()
        if p is not None:
            p.ensureWidgetVisible(w, margin, margin)
    return _s


def typed_spin(get_spin, value, per_char=160):
    """Click a spin box, type the value, commit it."""
    def commit():
        get_spin().setValue(value)
    text = f'{value:g}'
    return (act(get_spin, lambda: (spin_line(get_spin)().setFocus(), spin_line(get_spin)().selectAll()))
            + type_into(spin_line(get_spin), text, per_char) + [(300, commit)])


def click_selecting():
    dock().pushButton_checkable_exploring_selecting.click()


def coverage_spin():
    return dock().findChild(QWidget, 'mQgsSpinBox_filtering_coverage_min')


def class_condition(code, dtm, hag, story):
    """ATTRIBUTES group: "Classification = code" AND height above the DTM >= hag.

    CLASSES, ATTRIBUTES and EXPRESSION are exclusive groups of the panel; the height is ANDed
    with the active one, so a class and a height go together through a condition.
    """
    group = lambda: pc_panel()._ranges_group  # noqa: E731
    row = lambda: pc_panel()._condition_rows[-1]  # noqa: E731

    def set_condition():
        from filter_mate.core.domain.point_cloud_attributes import OP_EQUAL, JOIN_AND
        row().set_condition({'attribute': 'Classification', 'op': OP_EQUAL, 'low': float(code), 'high': None,
                             'join': JOIN_AND})
        pc_panel()._changed()
        log(f'condition {row().condition()}')

    return (act(group_check(group), open_group(group)) + [
        hold(500), (0, ensure_visible(lambda: pc_panel()._add_condition_button)), hold(300),
        (0, cam(group, dur=1.2, pad=30)),
    ] + act(lambda: pc_panel()._add_condition_button, lambda: pc_panel()._add_condition_button.click())
        + [hold(700)] + act(lambda: row()._attribute_combo, set_condition, lead=800) + [hold(1300), still(f'{story}-01')]
        + act('pushButton_checkable_exploring_selecting', click_selecting) + settle() + show_map(2800) + [
        (0, cam(group, dur=1.2, pad=30)), (0, ensure_visible(lambda: pc_panel()._hag_spin)),
    ] + act(lambda: pc_panel()._hag_check, lambda: pc_panel()._hag_check.setChecked(True))
        + typed_spin(lambda: pc_panel()._hag_spin, hag)
        + act(lambda: pc_panel()._hag_layer_combo, lambda: pc_panel()._hag_layer_combo.setLayer(layer(dtm)))
        + [hold(1200), (0, lambda: log(f'hag settings {pc_panel().hag_settings()} expression {pc_panel().expression()}')),
           still(f'{story}-02')])


def run_filter_long(fast=8.0):
    """run_filter() when PDAL computes the height above ground before the filter."""
    return act('pushButton_action_filter', click_filter) + [
        (300, speed(fast)), (1500, wait_long()), (0, refocus), (600, wait_idle()), (400, speed(1.0)), (0, filtered),
    ]


def fm5_scene(cloud_hidden=None):
    """Start recording on the whole square kilometre. ``cloud_hidden``: the classes of lhd not drawn (default: the
    ground, the unclassified points and the noise)."""
    def style_cloud():
        if QgsProject.instance().mapLayersByName('lhd'):
            style_point_cloud() if cloud_hidden is None else style_point_cloud(hidden=cloud_hidden)
    return [(500, wait_idle()), (0, style_cloud), (0, refocus), (800, wait_idle()), (500, rec_start),
            (0, cam('full', dur=0, drift=1.03)), hold(1200),
            (0, cam('canvas', dur=1.4, drift=1.03)), hold(1400)]


def to_exploring(name):
    return pick_layer(name) + [(300, wait_current(name)), hold(800), (0, cam(coverage_host, dur=1.4, pad=24)), hold(900)]


def combo_pick(get_combo, data, keep=1200):
    """Open a combo of a panel and visibly choose the entry holding `data`."""
    def show():
        get_combo().showPopup()

    def choose():
        combo = get_combo()
        index = combo.findData(data)
        if index < 0:
            log(f'combo entry not found: {data}')
            hide_popup()
            return
        view = combo.view()
        r = to_main(view.viewport(), view.visualRect(combo.model().index(index, 0)))
        REC.event('point', x=r.center().x(), y=r.center().y())
        REC.event('click', x=r.center().x(), y=r.center().y())
        combo.setCurrentIndex(index)
        hide_popup()

    return act(get_combo, show) + [(keep, choose), hold(350)]


# slope (story 9): slope of the DTM computed on the fly (Compute on: Slope %) >= FM5_SLOPE_MIN -> parcels at
# least half on it. The pente layer is only the backdrop: a derivative has no map preview.
SLOPE = boot5(['hillshade', 'pente', 'mnt', 'parcelle', 'batiment'], hidden=('mnt',)) + FM5_QUIET_BUILDINGS + [
    (0, restyle('parcelle', None, '#1d4ed8', 0.7))] + fm5_scene() \
    + to_exploring('mnt') + combo_pick(lambda: raster_panel()._derivative_combo, 'slope_percent') + [
    hold(900), still('s9-01'),
] + act(group_check(lambda: raster_panel()._range_group), open_group(lambda: raster_panel()._range_group)) + [
    hold(600), (0, ensure_visible(lambda: raster_panel()._max_spin)), hold(300),
    (0, cam(lambda: raster_panel()._range_group, dur=1.2, pad=30)),
] + typed_spin(lambda: raster_panel()._min_spin, FM5_SLOPE_MIN) + [hold(1300), still('s9-02'), (0, cam(FILTER_ZONE, dur=1.4, pad=40))] \
    + targets(['parcelle']) + predicates(['intersect']) + typed_spin(coverage_spin, 50, per_char=250) + [
    hold(600), still('s9-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [(0, lambda: counts(['parcelle', 'batiment'])), (0, quiet_message_bar)] + show_map(4500, 1.05) \
    + [still('s9-04')] \
    + ending(['parcelle'])

# heights (story 10): building points (class 6) more than FM5_HEIGHT m above the DTM (PDAL) -> buildings with
# at least half of their footprint under such points.
HEIGHTS = boot5(['hillshade', 'mnt', 'lhd', 'batiment'], hidden=('mnt',)) + fm5_scene() + to_exploring('lhd') \
    + class_condition(6, 'mnt', int(os.environ.get('FM5_HEIGHT', '7')), 's10') + [(0, cam(FILTER_ZONE, dur=1.4, pad=40))] \
    + targets(['batiment']) + predicates(['intersect']) + typed_spin(coverage_spin, 50, per_char=250) + [
    (200, buffer_off), hold(500), still('s10-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter_long() + [(0, lambda: counts(['batiment'])), (0, quiet_message_bar)] + show_map(4500, 1.05) + [still('s10-04')] \
    + ending(['batiment'])

# pruning (story 11): high vegetation (class 5) more than 8 m above the DTM -> road segments within 3 m.
PRUNING = boot5(['hillshade', 'mnt', 'lhd', 'batiment', 'troncon_de_route'], hidden=('mnt',)) + FM5_QUIET_BUILDINGS \
    + fm5_scene() \
    + to_exploring('lhd') + class_condition(5, 'mnt', 8, 's11') + [(0, cam(FILTER_ZONE, dur=1.4, pad=40))] \
    + targets(['troncon_de_route']) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(3) + [
    hold(500), still('s11-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter_long() + [(0, lambda: counts(['troncon_de_route'])), (0, quiet_message_bar)] + show_map(4500, 1.05) + [still('s11-04')] \
    + ending(['troncon_de_route'])


# sam (teaser 5.1.1): three clicks of SAM 2.1 on the orthophoto draw three buildings, which then filter the parcels.
# FM_SAM_POINTS ("x,y;x,y") and FM_SAM_RECT: the clicks and the frame, by default three roofs of Fenouillet (FM5_DIR)
SAM_POINTS = [tuple(float(v) for v in xy.split(',')) for xy in
              os.environ.get('FM_SAM_POINTS', '571404,6289272;571245,6289540;571331,6289646').split(';')]
SAM_RECT = tuple(float(v) for v in os.environ.get('FM_SAM_RECT', '571180,6289120,571560,6289700').split(','))


def detector_button():
    return dock().findChild(QWidget, 'pushButton_checkable_exploring_raster_detector')


def sam_ready():
    from filter_mate.adapters.qgis.coverage_layers import segmentation
    panel = raster_panel()
    panel._runtime_asked = True
    state = segmentation.model_state()
    panel.set_segmentation_readiness(state.runtime, state.installed)
    panel._engine_combo.setCurrentIndex(panel._engine_combo.findData('sam'))
    log(f'sam runtime={state.runtime} installed={state.installed} ready={panel.segmentation_ready()} '
        f'engine={panel.object_engine()}')


def sam_click(x, y):
    def _s():
        from qgis.core import QgsPointXY
        canvas = iface.mapCanvas()
        pt = QgsPointXY(x, y)
        px = canvas.getCoordinateTransform().transform(pt)
        r = to_main(canvas, QRect(int(px.x()), int(px.y()), 1, 1))
        REC.event('point', x=r.center().x(), y=r.center().y())
        REC.event('click', x=r.center().x(), y=r.center().y())
        ctrl = coverage()._segmentation_controller()
        if not ctrl.on_map():
            log(f'sam tool not on the map ({type(canvas.mapTool()).__name__}): activated')
            ctrl.activate()
        log(f'sam click {x} {y} tool {type(canvas.mapTool()).__name__}')
        ctrl.tool.pointPicked.emit(pt, True, False)
    return _s


def sam_done(n):
    def _s():
        ctrl = coverage()._segmentation_controller()
        done = ctrl._task is None and raster_panel().segment_count() >= n
        if done:
            log(f'sam objects {raster_panel().segment_count()}')
        return not done
    _s.max_tries = 240
    return _s


def sam_clicks():
    steps = []
    for i, (x, y) in enumerate(SAM_POINTS):
        steps += [(900, sam_click(x, y)), (300, speed(3.0)), (500, sam_done(i + 1)), (200, speed(1.0)), hold(1400)]
    return steps


SAM = boot5(['ortho', 'parcelle']) + fm5_scene() + to_exploring('ortho') \
    + act(group_check(lambda: raster_panel()._pipette_group), open_group(lambda: raster_panel()._pipette_group)) + [
    hold(600), (0, sam_ready), (0, ensure_visible(lambda: raster_panel()._engine_combo)), hold(300),
    (0, cam(lambda: raster_panel()._pipette_group, dur=1.2, pad=30)),
] + act(lambda: raster_panel()._target_buttons['object'], lambda: raster_panel()._target_buttons['object'].click()) + [
    hold(1200), (0, lambda: log(f'target {raster_panel().pick_target()} engine {raster_panel().object_engine()}')),
    (0, zoom_rect(*SAM_RECT)),
] + settle() + show_map(1500) + act(detector_button, lambda: detector_button().isChecked() or detector_button().click()) + [hold(900)] \
    + sam_clicks() + show_map(2500) + [(0, cam(FILTER_ZONE, dur=1.4, pad=40))] \
    + targets(['parcelle']) + predicates(['intersect']) + [
    hold(500), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [(0, lambda: counts(['parcelle']))] + show_map(4000, 1.05) + ending(['parcelle'])


# agent (teaser 5.1.1): one request typed in AGENT, answered by a local Ollama model, then Undo this turn.
AGENT_MODEL = os.environ.get('FM_AGENT_MODEL', 'qwen3:8b')
AGENT_REQUEST = os.environ.get('FM_AGENT_REQUEST', 'Keep the communes with more than 20000 inhabitants')


def agent_chat():
    d = dock()
    if getattr(d, '_agent_chat', None) is None:
        log('agent panel installed by the script')
        d.install_agent_panel(plugins['filter_mate'])
    return d._agent_chat


def agent_panel():
    return agent_chat().panel


def agent_setup():
    from qgis.core import QgsSettings
    from filter_mate.adapters.agent.settings import AgentSettings, save_settings, load_settings
    chat = agent_chat()
    QgsSettings().setValue('FilterMate/agent/setup_offered_version', chat.plugin_version())
    save_settings(AgentSettings(preset='ollama', model=AGENT_MODEL, consent=True,
                                consent_target='http://localhost:11434', local_filtering_only=True,
                                tool_families=False))
    chat._settings_dialog = lambda: False
    chat.open_settings = lambda: False
    chat._refresh_ready()
    chat.new_conversation()
    log(f'agent settings {load_settings()}')


def agent_open():
    dock()._fm_sections.open_top('agent')


def agent_done():
    def _s():
        busy = agent_chat().chat_busy() or agent_panel()._working
        if not busy:
            log('agent thread: ' + agent_panel().thread.toPlainText().replace('\n', ' | ')[:900])
        return busy
    _s.max_tries = 1600
    return _s


AGENT = boot(['epci', 'commune', 'surface_hydrographique'], 'commune', '"nom_officiel" = \'Toulouse\'', scale=None) + [
    (500, agent_setup), (800, agent_open), (1500, wait_idle()), (500, rec_start), (0, cam('full', dur=0, drift=1.03)),
    hold(1200), (0, cam(agent_panel, dur=1.4, pad=12)),
] + act(lambda: agent_panel().input, lambda: agent_panel().input.setFocus()) \
    + type_into(lambda: agent_panel().input, AGENT_REQUEST, per_char=55) + [hold(500)] \
    + act(lambda: agent_panel().send_button, lambda: agent_panel().send_button.click()) + [
    (500, speed(6.0)), (1500, agent_done()), (300, speed(1.0)), hold(3000),
    (0, lambda: counts(['commune'])), (0, cam('full', dur=1.6)), hold(3200), (0, cam(agent_panel, dur=1.3, pad=12)),
    hold(1200), (0, lambda: log(f'undo offered {agent_panel().undo_offered()}')),
] + act(lambda: agent_panel().undo_button, lambda: agent_panel().undo_button.click()) + settle() + [
    (0, cam('full', dur=1.4)), hold(2500)] + ending(['commune'])


def zip_edit():
    return dock().lineEdit_exporting_zip


SURVEY_ZIP = os.path.join(EXPORT_DIR, os.environ.get('FM5_SURVEY_ZIP', 'fenouillet_batiment.zip'))


# survey (story 12): the tallest building of the square (17.4 m; the church at Estavar) and 50 m around clip the DTM
# and the LiDAR, then both are exported.
SURVEY = boot5(['hillshade', 'mnt', 'lhd', 'parcelle', 'batiment'], fit=('FILTERING', 'EXPORTING')) + FM5_QUIET_BUILDINGS + fm5_scene() \
    + pick_layer('batiment') + [
    (1500, cam(EXPLORE_ZONE, dur=1.4, pad=30)),
] + typed_custom(os.environ.get('FM5_SURVEY_EXPR', '"hauteur" >= 17'), per_char=70) + settle() + show_map(2000) + [
    still('s12-01'), (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['mnt', 'lhd']) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(50) + [
    hold(500), still('s12-02'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter() + [(0, zoom_rect(*(float(v) for v in os.environ.get('FM5_SURVEY_RECT', '571414,6289121,571714,6289421').split(','))))] + settle() + show_map(4000, 1.05) + [
    still('s12-03'),
    (0, cam('dock', dur=1.4, pad=10)),
] + act(toolbox_button('export'), lambda: dock().toolBox_tabTools.setCurrentIndex(1)) + [
    (1200, cam(EXPORT_ZONE, dur=1.4, pad=40)),
] + act('pushButton_checkable_exporting_layers', enable('pushButton_checkable_exporting_layers')) \
    + combo_check('checkableComboBoxLayer_exporting_layers', ['mnt', 'lhd'], per_item=500) \
    + [(200, export_layers_changed)] \
    + act('pushButton_checkable_exporting_output_folder', enable('pushButton_checkable_exporting_output_folder')) \
    + act(folder_edit, lambda: folder_edit().clear()) + type_into(folder_edit, EXPORT_DIR, per_char=25, clear=False) \
    + act('pushButton_checkable_exporting_zip', enable('pushButton_checkable_exporting_zip')) \
    + act(zip_edit, lambda: (os.makedirs(EXPORT_DIR, exist_ok=True), zip_edit().clear())) \
    + type_into(zip_edit, SURVEY_ZIP, per_char=25, clear=False) \
    + [(400, cam(['pushButton_action_export', 'pushButton_checkable_exporting_zip'], dur=1.2, pad=40))] \
    + [hold(600), still('s12-04'), (0, lambda: log(f"export props {dock().project_props.get('EXPORTING')}"))] \
    + act('pushButton_action_export', export_with_recap) + [hold(1500)] \
    + settle(4.0) + [(0, wait_long()), result('One ZIP: the terrain model (GeoTIFF) and the point cloud (LAZ)')] \
    + show_map(3000) + ending()


# ------------------------------------------------------------------ stories 13 to 15: a raster or a cloud filters another
# coverage layer (the squares of Fenouillet: ortho_irc / ortho_rvb 0.25 m, lhd, mnt 0.5 m).
def menu_pick(get_button, text, keep=1700):
    """Open the menu of a tool button where a click would, glide to the entry ``text`` and trigger it."""
    def open_menu():
        button = get_button()
        menu = button.menu()
        menu.popup(button.mapToGlobal(QPoint(0, button.height())))
        if menu not in REC.windows:
            REC.windows.append(menu)
        log(f'menu of {button.objectName()}: {[a.text() for a in menu.actions() if not a.isSeparator()]}')

        def entry():
            return next((a for a in menu.actions() if a.text().replace('&', '').strip() == text), None)

        def highlight():
            action = entry()
            if action is None:
                log(f'menu entry not found: {text}')
                return
            r = to_main(menu, menu.actionGeometry(action))
            REC.event('point', x=r.center().x(), y=r.center().y())
            menu.setActiveAction(action)

        def activate():
            action = entry()
            if action is not None:
                r = to_main(menu, menu.actionGeometry(action))
                REC.event('click', x=r.center().x(), y=r.center().y())
            menu.close()
            if menu in REC.windows:
                REC.windows.remove(menu)
            if action is not None:
                action.trigger()
                log(f'menu entry triggered: {text}')

        QTimer.singleShot(350, highlight)
        QTimer.singleShot(keep, activate)

    return act(get_button, open_menu) + [hold(keep + 600)]


def legend_visible(name, on):
    """Tick or untick a layer in the Layers panel (the cursor goes to its check box)."""
    def box_rect():
        r = tree_item(name)()
        return QRect(r.x(), r.y(), 22, r.height())

    def toggle():
        node = QgsProject.instance().layerTreeRoot().findLayer(layer(name).id())
        node.setItemVisibilityChecked(on)
    return act(box_rect, toggle, lead=700, after=700)


def raster_kept(name):
    """Pixels of the raster layer ``name`` that are not NoData (its mask), read from the file it shows now."""
    from osgeo import gdal
    ml = layer(name)
    ds = gdal.Open(ml.source())
    mask = ds.GetRasterBand(1).GetMaskBand().ReadAsArray()
    kept = int((mask > 0).sum())
    gt = ds.GetGeoTransform()
    out = {'source': ml.source(), 'size': (ds.RasterXSize, ds.RasterYSize), 'kept': kept,
           'kept_m2': round(kept * abs(gt[1] * gt[5]), 1)}
    log(f'raster kept {name} {out}')
    return out


def raster_base(name, path):
    """The same count on the original file: the share kept is read against it."""
    from osgeo import gdal
    ds = gdal.Open(path)
    mask = ds.GetRasterBand(1).GetMaskBand().ReadAsArray()
    total = int((mask > 0).sum())
    log(f'raster base {name} {path} size {(ds.RasterXSize, ds.RasterYSize)} valid {total}')
    return total


def cloud_kept(name):
    from filter_mate.adapters.qgis.coverage_layers.target_appliers import derived_point_count
    ml = layer(name)
    n = derived_point_count(ml)
    log(f'cloud kept {name} {n} points, source {ml.source()} subset {ml.subsetString()!r}')
    return n


def result_with(text_of):
    """The closing line of a take, written from what ``text_of()`` measures at that moment."""
    def _s():
        try:
            text = text_of()
        except Exception:
            log(traceback.format_exc())
            return
        REC.event('caption', text=text, style='result')
        log(f'result {text}')
    _s.text = True
    return (0, _s)


def ending_coverage(report):
    """ending() for coverage targets: the counts are logged by ``report`` once the recording is over."""
    return [(0, cam('full', dur=1.6)), (2200, stop_recording), (0, report), (500, quit_when_idle)]


def band_chip(number):
    return lambda: raster_panel()._band_rows[number]['chip']


def log_raster_state():
    panel = raster_panel()
    log(f'raster roles {panel.band_roles()} mode {panel.active_mode()} kept ratio {panel.kept_ratio()} '
        f'expression {panel._expression_edit.toPlainText()!r}')


# ndvi (story 13): the colour infrared orthophoto, NDVI > 0.3 (its bands told as IRC) -> clips the RGB orthophoto.
def ndvi_result():
    kept = raster_kept('ortho_rvb')
    total = STATE.get('rvb_total') or raster_base('ortho_rvb', os.path.join(FM5_DIR, 'ortho_rvb.tif'))
    STATE['rvb_total'] = total
    return f'NDVI > 0.3: {kept["kept_m2"] / 10000:.1f} ha of the RGB orthophoto kept ({100 * kept["kept"] / total:.0f} %)'


def ndvi_report():
    raster_base('ortho_rvb', os.path.join(FM5_DIR, 'ortho_rvb.tif'))
    raster_kept('ortho_rvb')
    log_raster_state()


# The result is read closer, on the gardens and the trees along the motorway (FM_NDVI_DETAIL: xmin,ymin,xmax,ymax).
NDVI_DETAIL = tuple(float(v) for v in os.environ.get('FM_NDVI_DETAIL', '571600,6289600,572000,6289900').split(','))

NDVI = boot5(['ortho_rvb', 'ortho_irc']) + fm5_scene() + to_exploring('ortho_irc') + [
    (0, cam(lambda: raster_panel()._bands_group, dur=1.2, pad=30)), hold(600),
] + menu_pick(band_chip(1), 'Every band: IRC') + [
    hold(900), (0, log_raster_state), still('s13-01'),
] + act(group_check(lambda: raster_panel()._expression_group), open_group(lambda: raster_panel()._expression_group)) + [
    hold(600), (0, ensure_visible(lambda: raster_panel()._insert_button)), hold(300),
    (0, cam(lambda: raster_panel()._expression_group, dur=1.2, pad=30)),
] + menu_pick(lambda: raster_panel()._insert_button, 'Vegetation (NDVI > 0.3)') + [hold(900)] \
    + act('pushButton_checkable_exploring_selecting', click_selecting) + settle(3.0) + show_map(2600) + [
    (0, cam(lambda: raster_panel()._expression_group, dur=1.2, pad=30)), hold(900),
    (0, log_raster_state), still('s13-02'), (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['ortho_rvb']) + predicates(['intersect']) + [
    (200, buffer_off), hold(500), still('s13-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter_long() + legend_visible('ortho_irc', False) + settle() + show_map(1500, 1.05) + [
    (0, zoom_rect(*NDVI_DETAIL))] + settle() + show_map(1200, 1.05) + [
    (300, speed(4.0)), result_with(ndvi_result), (0, speed(1.0)), hold(3000), still('s13-04'),
] + ending_coverage(ndvi_report)


# roofs (story 14): the RGB orthophoto, the pipette on "Clicked object" (colour engine): a click on a roof, a
# Ctrl+click on its neighbour -> the LiDAR points beneath them. FM_ROOF_POINTS ("x,y;x,y"), FM_ROOF_RECT: the clicks
# and the frame, by default the two terracotta roofs of the business park of Fenouillet.
ROOF_POINTS = [tuple(float(v) for v in xy.split(',')) for xy in
               os.environ.get('FM_ROOF_POINTS', '571330,6289645;571366,6289670').split(';')]
ROOF_RECT = tuple(float(v) for v in os.environ.get('FM_ROOF_RECT', '571200,6289520,571480,6289740').split(','))


def roof_click(x, y, extend):
    """A click of the pixel picker on the map (Ctrl+click when ``extend``): the signal a real click emits."""
    def _s():
        from qgis.core import QgsPointXY
        canvas = iface.mapCanvas()
        pt = QgsPointXY(x, y)
        px = canvas.getCoordinateTransform().transform(pt)
        r = to_main(canvas, QRect(int(px.x()), int(px.y()), 1, 1))
        REC.event('point', x=r.center().x(), y=r.center().y())
        REC.event('click', x=r.center().x(), y=r.center().y())
        tool = coverage()._pixel_tool
        if tool is None or canvas.mapTool() is not tool:
            log(f'pixel picker not on the map ({type(canvas.mapTool()).__name__})')
            return
        tool.show_marker(pt)
        tool.picked.emit(pt, extend)
        log(f'roof click {x} {y} extend={extend}')
    return _s


def roofs_found(n):
    def _s():
        found = raster_panel().detected_objects()
        done = not tasks_running() and found is not None and (found[0] or 0) >= n
        if done:
            log(f'roof objects {found}')
        return not done
    _s.max_tries = 240
    return _s


def object_target():
    panel = raster_panel()
    panel._runtime_asked = True  # no offer to install SAM: the colour engine, as a new install without the model
    panel._target_buttons['object'].click()
    log(f'target {panel.pick_target()} engine {panel.object_engine()}')


def detector_on():
    """The object detector of the rail on the map (it may already show down for the target chosen in PIPETTE)."""
    if not detector_button().isChecked():
        detector_button().click()
    tool = coverage()._pixel_tool
    log(f'detector checked {detector_button().isChecked()} tool on map {tool is not None and iface.mapCanvas().mapTool() is tool}')


def roofs_result():
    n = cloud_kept('lhd')
    found = raster_panel().detected_objects() or (None, None, False)
    area = f' · {found[1]:,.0f} m²' if found[1] else ''
    return f'{n:,} LiDAR points beneath the 2 roofs{area}'


def roofs_report():
    cloud_kept('lhd')
    log(f'roof objects {raster_panel().detected_objects()}')


ROOFS = boot5(['ortho_rvb', 'lhd'], hidden=('lhd',)) + fm5_scene(cloud_hidden=(7, 18)) + to_exploring('ortho_rvb') + [
    (0, zoom_rect(*ROOF_RECT)),
] + settle() + show_map(1800) + [
    (0, cam(lambda: raster_panel()._bands_group, dur=1.2, pad=30)), hold(1500), (0, log_raster_state),
    still('s14-01'),
] + act(group_check(lambda: raster_panel()._pipette_group), open_group(lambda: raster_panel()._pipette_group)) + [
    hold(600), (0, ensure_visible(lambda: raster_panel()._target_buttons['object'])), hold(300),
    (0, cam(lambda: raster_panel()._pipette_group, dur=1.2, pad=30)),
] + act(lambda: raster_panel()._target_buttons['object'], object_target) + [hold(900)] \
    + act(detector_button, detector_on) + [hold(900)] + [
    (900, roof_click(*ROOF_POINTS[0], False)), (300, speed(3.0)), (500, roofs_found(1)), (200, speed(1.0)), hold(1600),
    (900, roof_click(*ROOF_POINTS[1], True)), (300, speed(3.0)), (500, roofs_found(2)), (200, speed(1.0)), hold(1600),
    (0, cam(lambda: raster_panel()._pipette_group, dur=1.2, pad=30)), hold(1200), still('s14-02'),
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['lhd']) + predicates(['intersect']) + [
    (200, buffer_off), hold(500), still('s14-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter_long() + [(0, zoom_rect(*ROOF_RECT))] + legend_visible('lhd', True) + settle() + show_map(1500, 1.05) \
    + legend_visible('ortho_rvb', False) + settle() + show_map(1200, 1.05) + [
    (300, speed(4.0)), result_with(roofs_result), (0, speed(1.0)), hold(3000), still('s14-04'),
] + ending_coverage(roofs_report)


# ground (story 15): the cloud, CLASSES / Selection: Ground (class 2) -> clips the DTM.
def mnt_opaque():
    ml = layer('mnt')
    ml.renderer().setOpacity(0.9)
    ml.triggerRepaint()


def ground_result():
    kept = raster_kept('mnt')
    total = STATE.get('mnt_total') or raster_base('mnt', FM5_DTM)
    STATE['mnt_total'] = total
    return f'DTM beneath the ground points: {100 * kept["kept"] / total:.0f} % of its pixels kept'


def ground_report():
    raster_base('mnt', FM5_DTM)
    raster_kept('mnt')
    log(f'classes {pc_panel()._class_summary_label.text()!r} expression {pc_panel().expression()!r}')


def log_classes():
    log(f'classes {pc_panel()._class_summary_label.text()!r} expression {pc_panel().expression()!r}')


GROUND = boot5(['mnt', 'lhd']) + [(0, mnt_opaque)] + fm5_scene(cloud_hidden=(0, 1, 7, 18, 64, 65, 66, 67)) \
    + to_exploring('lhd') + [
    (0, ensure_visible(lambda: pc_panel()._classes_list)), hold(300),
    (0, cam(lambda: pc_panel()._classes_group, dur=1.2, pad=30)), hold(1800), (0, log_classes), still('s15-01'),
] + menu_pick(lambda: pc_panel()._quick_button, 'Ground') + [hold(900), (0, log_classes)] \
    + act('pushButton_checkable_exploring_selecting', click_selecting) + settle(3.0) + show_map(2600) + [
    (0, cam(lambda: pc_panel()._classes_group, dur=1.2, pad=30)), hold(900), still('s15-02'),
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['mnt']) + predicates(['intersect']) + [
    (200, buffer_off), hold(500), still('s15-03'), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter_long() + legend_visible('lhd', False) + settle() + show_map(1500, 1.05) + [
    (300, speed(4.0)), result_with(ground_result), (0, speed(1.0)), hold(3000), still('s15-04'),
] + ending_coverage(ground_report)


# wires (story 16): a LiDAR survey with classified wires (Wellington, New Zealand, NZTM 2000), loaded twice. The
# vegetation copy keeps class 5 alone (filtered alone), the network copy keeps the wire conductors (class 14; no class 13
# in this survey); a 10 m buffer around the wire footprint clips the vegetation copy. FM_WIRES_DIR: the folder of
# wellington_lines.copc.laz (mounted with FM_DOCKER_ARGS="-v <folder>:/wires:ro").
WIRES_DIR = os.environ.get('FM_WIRES_DIR', '/wires')
WIRES_TILE = os.path.join(WIRES_DIR, 'wellington_lines.copc.laz')
WIRES_DETAIL = tuple(float(v) for v in os.environ.get('FM_WIRES_DETAIL', '1746820,5429380,1747040,5429640').split(','))
WIRES_EXTENT = tuple(float(v) for v in os.environ.get('FM_WIRES_EXTENT', '1746880,5429040,1747360,5429760').split(','))


def style_cloud_classes(pc, shown, size=1.6, colours=None):
    """Classified rendering of ``pc`` drawing only the classes ``shown`` (``colours``: code -> colour)."""
    from qgis.core import QgsPointCloudClassifiedRenderer
    renderer = QgsPointCloudClassifiedRenderer('Classification', QgsPointCloudClassifiedRenderer.defaultCategories())
    categories = renderer.categories()
    for category in categories:
        category.setRenderState(category.value() in shown)
        if colours and category.value() in colours:
            category.setColor(QColor(colours[category.value()]))
    renderer.setCategories(categories)
    renderer.setPointSize(size)
    pc.setRenderer(renderer)
    pc.triggerRepaint()


def setup_wires():
    from qgis.core import QgsCoordinateReferenceSystem, QgsPointCloudLayer
    canvas = prepare_window()
    QgsProject.instance().setCrs(QgsCoordinateReferenceSystem('EPSG:2193'))
    for name in ('lhd_vegetation', 'lhd_reseau'):
        ml = QgsPointCloudLayer(WIRES_TILE, name, 'copc')
        log(f'layer {name} valid={ml.isValid()} crs={ml.crs().authid() or ml.crs().description()} '
            f'points={ml.pointCount()}')
        QgsProject.instance().addMapLayer(ml)
    log(f'project crs {QgsProject.instance().crs().authid()}')
    bb = QgsRectangle(*WIRES_EXTENT)
    bb.scale(1.03)
    STATE['scene_rect'] = QgsRectangle(bb)
    STATE['boot_extent'] = QgsRectangle(bb)
    set_extent(bb)
    canvas.setRenderFlag(True)


def wires_style():
    # the vegetation copy: everything above the ground; the network copy: its wires only, in amber
    style_cloud_classes(layer('lhd_vegetation'), (3, 4, 5, 6), 1.4)
    style_cloud_classes(layer('lhd_reseau'), (13, 14), 1.4, {13: '#b45309', 14: '#d97706'})


def class_item(code):
    def _item():
        return next(item for item in pc_panel()._class_items() if int(item.data(Qt.ItemDataRole.UserRole)) == code)
    return _item


def only_class(code):
    """Selection > No class, then the box of ``code`` ticked, as a user does."""
    item = class_item(code)

    def scroll():
        item().listWidget().scrollToItem(item())

    def rect():
        view = item().listWidget()
        r = to_main(view.viewport(), view.visualItemRect(item()))
        return QRect(r.x(), r.y(), 24, r.height())  # its check box

    def check():
        item().setCheckState(Qt.CheckState.Checked)
        log(f'class {code} checked: {pc_panel()._checked_codes()} expression {pc_panel().expression()!r}')
    return (menu_pick(lambda: pc_panel()._quick_button, 'No class') + [hold(500), (0, scroll), hold(200)]
            + act(rect, check) + [hold(900)])


def log_cloud(name):
    def _s():
        from filter_mate.adapters.qgis.coverage_layers.target_appliers import derived_point_count
        ml = layer(name)
        log(f'cloud {name} points {derived_point_count(ml)} subset {ml.subsetString()!r} source {ml.source()}')
    return _s


def cloud_points(path, classes, label):
    """Points of the classes ``classes`` ("5:5") in the file ``path``, counted by PDAL."""
    import subprocess
    stages = [path, {'type': 'filters.range', 'limits': f'Classification[{classes}]'},
              {'type': 'filters.stats', 'dimensions': 'Classification'}]
    out = subprocess.run(['pdal', 'pipeline', '--stdin', '--metadata', 'STDOUT'], input=json.dumps(stages),
                         capture_output=True, text=True, timeout=600)
    try:
        n = int(json.loads(out.stdout)['stages']['filters.stats']['statistic'][0]['count'])
    except Exception:
        log(f'pdal count {label} failed: {out.stderr[-400:]} {out.stdout[-300:]}')
        return -1
    log(f'cloud points {label} classes {classes}: {n} ({path})')
    return n


def wires_result():
    n = cloud_points(layer('lhd_vegetation').source(), '5:5', 'lhd_vegetation in the corridor')
    return f'{n:,} high vegetation points within 10 m of the wires'


def wires_report():
    for name in ('lhd_reseau', 'lhd_vegetation'):
        log_cloud(name)()
    cloud_points(layer('lhd_vegetation').source(), '5:5', 'lhd_vegetation in the corridor')
    cloud_points(layer('lhd_vegetation').source(), '0:255', 'lhd_vegetation file, every class')
    cloud_points(layer('lhd_reseau').source(), '14:14', 'lhd_reseau now')
    cloud_points(WIRES_TILE, '5:5', 'survey')
    cloud_points(WIRES_TILE, '14:14', 'survey')
    cloud_points(WIRES_TILE, '13:13', 'survey')


WIRES = [(1000, setup_wires), (3000, open_plugin), (8000, size_dock), (1500, wait_idle()),
         (500, fit_window(('FILTERING',))), (2500, wait_idle()), (0, wires_style)] + [
    (500, wait_idle()), (0, refocus), (800, wait_idle()), (500, rec_start),
    (0, cam('full', dur=0, drift=1.03)), hold(1200), (0, cam('canvas', dur=1.4, drift=1.03)), hold(1400),
] + to_exploring('lhd_vegetation') + [
    (0, ensure_visible(lambda: pc_panel()._classes_list)), hold(300),
    (0, cam(['layers', lambda: pc_panel()._classes_group], dur=1.2, pad=20)), hold(1800), (0, log_classes),
    still('s16-01'),
    (0, cam(lambda: pc_panel()._classes_group, dur=1.2, pad=30)),
] + only_class(5) + [(0, log_classes), (0, cam('dock', dur=1.2, pad=10))] \
    + act('pushButton_checkable_filtering_layers_to_filter', enable('pushButton_checkable_filtering_layers_to_filter', False)) \
    + [hold(600)] + run_filter_long() + [(0, log_cloud('lhd_vegetation'))] + show_map(2000) + [
    (0, cam('dock', dur=1.2, pad=10)), hold(600), still('s16-02'),
] + to_exploring('lhd_reseau') + [
    (0, ensure_visible(lambda: pc_panel()._classes_list)), hold(300),
    (0, cam(lambda: pc_panel()._classes_group, dur=1.2, pad=30)), hold(900),
] + only_class(14) + [(0, log_classes)] + act('pushButton_checkable_exploring_selecting', click_selecting) \
    + settle(3.0) + show_map(2400) + [
    (0, cam(lambda: pc_panel()._classes_group, dur=1.2, pad=30)), hold(900), still('s16-03'),
    (0, cam(FILTER_ZONE, dur=1.4, pad=40)),
] + targets(['lhd_vegetation']) + predicates(['intersect']) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0)) + typed_buffer(10) + [
    hold(500), (400, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + run_filter_long() + settle() + show_map(1500, 1.05) + [
    (300, speed(4.0)), result_with(wires_result), (0, speed(1.0)), hold(2000), (0, zoom_rect(*WIRES_DETAIL)),
] + settle() + show_map(2500, 1.04) + [still('s16-04')] + ending_coverage(wires_report)


# ------------------------------------------------------------------ FilterMate 5.1: the dock, its panels, its settings
# The sections of the dock (rail of chips by default) leave it for panels of QGIS, share a panel, come back; the
# layout settings apply at once; the setup with no model asks where the sections go. The menus and cards shown
# are the real ones: a step opens them where a click would, glides to the entry, then triggers it.
def section_panels():
    return dock()._fm_panels


def panel_of(key):
    return section_panels().panel(key)


def section_menu(key, command, holder=None, keep=1700):
    """Right click on the chip of ``key`` (in the dock, or in the rail of the panel ``holder``, a callable): the menu
    of the section opens at the chip, the cursor glides to the entry ``action_section_<command>`` and clicks it."""
    def target():
        return chip(key, holder() if holder is not None else None)

    def open_menu():
        where = target()
        parent = holder() if holder is not None else dock()
        menu = section_panels().build_menu(key, parent)
        if menu is None:
            log(f'no menu for {key}')
            return
        STATE['section_menu'] = menu
        menu.popup(where.mapToGlobal(QPoint(where.width() // 2, where.height() // 2)))
        if menu not in REC.windows:
            REC.windows.append(menu)
        log(f'menu of {key}: {[a.objectName() for a in menu.actions() if not a.isSeparator()]}')

        def entry():
            return next((a for a in menu.actions() if a.objectName() == 'action_section_' + command), None)

        def highlight():
            action = entry()
            if action is None:
                log(f'menu entry not found: {command}')
                return
            r = to_main(menu, menu.actionGeometry(action))
            REC.event('point', x=r.center().x(), y=r.center().y())
            menu.setActiveAction(action)

        def activate():
            action = entry()
            if action is not None:
                r = to_main(menu, menu.actionGeometry(action))
                REC.event('click', x=r.center().x(), y=r.center().y())
            menu.close()
            if menu in REC.windows:
                REC.windows.remove(menu)
            if action is not None:
                action.trigger()
                log(f'{command} {key}: groups {section_panels().groups()}')

        QTimer.singleShot(350, highlight)
        QTimer.singleShot(keep, activate)

    return act(target, open_menu) + [hold(keep + 600)]


def chip_click(key, holder=None):
    """A left click on a chip: its section opens (in the dock, or in the panel ``holder``)."""
    def target():
        return chip(key, holder() if holder is not None else None)
    return act(target, lambda: target().click())


def under_layers(key):
    """The panel of ``key`` dragged by its title under the Layers panel, left of the map (a QGIS gesture: the cursor
    glides from the title to the bottom of the Layers panel, the panel lands there). FilterMate then gives it the
    height of its rows, and the Layers panel the rest."""
    def title():
        r = rect_of(panel_of(key))
        return QRect(r.x() + 20, r.y(), 140, 22)

    def spot():
        r = rect_of(iface.mainWindow().findChild(QDockWidget, 'Layers'))
        return QRect(r.x() + r.width() // 2, r.bottom() - 40, 1, 1)

    def drop():
        window = iface.mainWindow()
        layers = window.findChild(QDockWidget, 'Layers')
        STATE['layers_width'] = layers.width()
        window.splitDockWidget(layers, panel_of(key), Qt.Orientation.Vertical)
        QTimer.singleShot(1500, lambda: log(
            f'{key} under the Layers panel: {rect_of(panel_of(key))}, layers {rect_of(layers)}'))

    return [(600, point(title)), (700, lambda: REC.event('click', x=title().center().x(), y=title().center().y())),
            (900, point(spot)), (500, drop)]


def layers_width_back():
    """The Layers panel at the width it had before a panel of FilterMate shared its column."""
    width = STATE.pop('layers_width', None)
    if width:
        window = iface.mainWindow()
        window.resizeDocks([window.findChild(QDockWidget, 'Layers')], [width], Qt.Orientation.Horizontal)


def panels_log(label):
    """Log where the dock and the panels are, and the band under the rows of each rigid section shown."""
    def _s():
        lines = [f'dock {rect_of(dock())}']
        for key in ('agent', 'exploring', 'filtering', 'exporting', 'configuration'):
            panel = panel_of(key)
            if panel is not None and f'{key} ' not in ' '.join(lines):
                lines.append(f'{key} {rect_of(panel)}')
        log(f'{label}: ' + ', '.join(lines) + f', groups {section_panels().groups()}')
    return _s


def merge_all():
    """Back to the dock, whatever is apart (end of a take: the next one starts from the dock of a new install)."""
    if section_panels().detached():
        section_panels().attach_all()


def staged(scale, target_names=('batiment', 'troncon_de_route'), predicate='intersect'):
    """Unrecorded: Muret picked in EXPLORING, FILTERING set on some targets (so its page is not empty), the commune
    framed at ``scale``."""
    def remember():
        STATE['scene_scale'] = scale
    return [
        (0, restyle('commune', None, '#5b636b', 0.8, selection_alpha=120)),
        (500, source('commune')), (1500, single_mode(tracking=False)), (1500, pick_focus), (500, filtering_tab),
        (500, enable('pushButton_checkable_filtering_layers_to_filter')),
        (300, lambda: check_combo_items(dock().checkableComboBoxLayer_filtering_layers_to_filter, list(target_names),
                                        uncheck_others=True)),
        (300, refresh_targets),
        (300, enable('pushButton_checkable_filtering_geometric_predicates')),
        (300, lambda: check_combo_items(dock().comboBox_filtering_geometric_predicates, [predicate], True)),
        (0, remember), (500, zoom_focus(scale)), (1500, wait_idle()), (500, rec_start),
        (0, cam('full', dur=0, drift=1.03))]


def staged_then(scale, *steps):
    """staged(), with ``steps`` run just before the recording starts."""
    base = staged(scale)
    return base[:-2] + list(steps) + base[-2:]


def tick_communes(names):
    """Unrecorded: communes ticked in the multiple selection list."""
    def _s():
        w, lw = multi_widget()
        for name in names:
            items = lw.findItems(name, Qt.MatchFlag.MatchStartsWith)
            if items:
                items[0].setCheckState(Qt.CheckState.Checked)
        w._emit_checked_items_update()
    return _s


PANELS_LAYERS = ['commune', 'zone_de_vegetation', 'surface_hydrographique', 'batiment', 'troncon_de_route']

# panels: FILTERING leaves the dock by the menu of its chip and takes the height of its rows under it, EXPORTING
# joins its panel, which follows the section it shows; the panel goes under the Layers panel, where it fits too;
# then every section merges back into the dock. EXPLORING is in multiple selection: its list takes the height the
# dock gives it, whatever is set apart (with a single selection that height stayed empty under its groups). The
# window is not fitted: a section in its own panel needs the height of one more title bar and of its buttons.
PANELS = boot(PANELS_LAYERS, 'commune', '"nom_officiel" = \'Muret\'', 1.15, fit=None) + staged_then(
    1.15, (300, multi_mode), (2500, wait_idle()), (300, tick_communes(['Muret', 'Seysses', 'Eaunes'])),
    (800, wait_idle()), (300, fit_stacks), (900, wait_idle())) + [
    title('The sections become QGIS panels'), caption('1 · FILTERING leaves the dock: a panel as tall as its rows'),
    hold(1400), (0, cam('dock', dur=1.4, pad=12)), hold(800),
] + section_menu('filtering', 'detach') + [
    hold(900), (0, panels_log('filtering apart')), (0, cam('full', dur=1.4)), hold(2000),
    caption('2 · EXPORTING joins it: the panel follows the section it shows'),
    (0, cam(lambda: [dock(), panel_of('filtering')], dur=1.3, pad=12)),
] + section_menu('exporting', 'group_filtering') + [hold(1500), (0, panels_log('exporting joined'))] \
    + chip_click('filtering', lambda: panel_of('filtering')) + [
    hold(1300), (0, cam('full', dur=1.4)), caption('3 · Dragged under the Layers panel, it fits there too'),
    hold(600)] \
    + under_layers('filtering') + [hold(2800), (0, panels_log('under layers')),
                                   caption('4 · Merge everything back into the dock'),
                                   (0, cam(lambda: panel_of('filtering'), dur=1.3, pad=12)), hold(600)] \
    + section_menu('filtering', 'attach_all', holder=lambda: panel_of('filtering'))[:-1] + [
    # back to the whole window as the entry is clicked: the place the panel leaves is an empty part of the Layers panel
    hold(1700), (0, cam('full', dur=1.0)), hold(500), (0, layers_width_back), hold(900)] + chip_click('filtering') + [
    (500, fit_stacks), hold(2600), (0, stop_recording), (0, merge_all), (500, quit_when_idle)]


def explo_chooser():
    """The chooser of the current layer EXPLORING shows once it is away from FILTERING."""
    from qgis.PyQt.QtWidgets import QComboBox
    return dock().frame_exploring.findChild(QComboBox, 'comboBox_exploring_current_layer')


def chooser_pick(name, keep=1300):
    """Open the chooser of EXPLORING and choose the layer ``name`` in its list (as a click there does)."""
    def show():
        explo_chooser().showPopup()

    def choose():
        combo = explo_chooser()
        index = next((i for i in range(combo.count()) if combo.itemText(i).split(' [')[0] == name), -1)
        if index < 0:
            log(f'layer not in the chooser: {name} {[combo.itemText(i) for i in range(combo.count())]}')
            hide_popup()
            return
        view = combo.view()
        r = to_main(view.viewport(), view.visualRect(combo.model().index(index, 0)))
        REC.event('point', x=r.center().x(), y=r.center().y())
        REC.event('click', x=r.center().x(), y=r.center().y())
        hide_popup()
        combo.setCurrentIndex(index)
        combo.activated.emit(index)
        log(f'chooser -> {combo.currentText()}, current layer {iface.activeLayer().name()}')

    return act(explo_chooser, show) + [(keep, choose), hold(400)]


EXPLO_LAYERS = PANELS_LAYERS


def pick_where(name, expr):
    """The single selection picker of EXPLORING set on the feature of ``name`` matching ``expr``."""
    def _s():
        fids = fids_where(name, expr)
        log(f'pick {name} {expr} -> {fids[:3]}')
        if fids:
            dock().mFeaturePickerWidget_exploring_single_selection.setFeature(fids[0])
        hide_popup()
    return _s


# exploring-panel: EXPLORING in its own panel, with its chooser of the current layer: the buildings chosen there
# (their page follows), the communes chosen again, Portet-sur-Garonne picked with tracking on: the map follows; then
# EXPLORING back into the dock.
EXPLORING_PANEL = boot(EXPLO_LAYERS, 'commune', '"nom_officiel" = \'Muret\'', 1.0, spare=60) + staged(1.0) + [
    (0, lambda: iface.mapCanvas().setSelectionColor(QColor(255, 216, 61, 120))),
    title('EXPLORING in its own panel'), caption('1 · EXPLORING leaves the dock'),
    hold(1200), (0, cam('dock', dur=1.4, pad=12)), hold(700),
] + section_menu('exploring', 'detach') + [
    hold(900), (0, panels_log('exploring apart')), (0, cam('full', dur=1.4)), hold(1600),
    caption('2 · Its own layer chooser: buildings, then communes'),
    (0, cam(lambda: panel_of('exploring'), dur=1.3, pad=12)), hold(500),
] + chooser_pick('batiment') + [hold(2200)] + chooser_pick('commune') + [
    hold(1200), caption('3 · Tracking on: pick a commune, the map follows')] \
    + act('pushButton_checkable_exploring_tracking', enable('pushButton_checkable_exploring_tracking')) \
    + act('pushButton_checkable_exploring_selecting', enable('pushButton_checkable_exploring_selecting'), after=500) \
    + act(picker_edit) + type_into(picker_edit, 'Portet', per_char=130) + [
    (900, pick_where('commune', '"nom_officiel" = \'Portet-sur-Garonne\''))] + settle() + show_map(3200, 1.04) + [
    caption('4 · Back into the dock'), (0, cam(lambda: panel_of('exploring'), dur=1.3, pad=12)), hold(400),
] + section_menu('exploring', 'attach', holder=lambda: panel_of('exploring')) + [
    hold(400), (0, cam('full', dur=1.4)), hold(2400), (0, stop_recording), (0, merge_all), (500, quit_when_idle)]


def config_search():
    from qgis.PyQt.QtWidgets import QLineEdit as _Edit
    return dock().config_view_container.findChild(_Edit)


def config_item(path):
    """Value item of a key path of the CONFIGURATION tree (a key shown under its display name keeps it in UserRole)."""
    parent, item = dock().config_model.invisibleRootItem(), None
    for key in path:
        rows = [row for row in range(parent.rowCount())
                if key in (parent.child(row, 0).data(Qt.ItemDataRole.UserRole), parent.child(row, 0).text())]
        if not rows:
            return None
        item, parent = parent.child(rows[0], 1), parent.child(rows[0], 0)
    return item


def view_index(view, item):
    """Index of ``item`` in the tree of CONFIGURATION (JsonView keeps its model in an attribute named ``model``)."""
    from qgis.PyQt.QtWidgets import QTreeView
    model = QTreeView.model(view)
    return model.mapFromSource(item.index()) if hasattr(model, 'mapFromSource') else item.index()


def config_value_rect(path):
    def _r():
        view = dock().config_view
        item = config_item(path)
        if item is None:
            return rect_of(view)
        index = view_index(view, item)
        view.scrollTo(index)
        return to_main(view.viewport(), view.visualRect(index))
    return _r


def config_choose(path, value, keep=1300):
    """Open the editor of a choice of the CONFIGURATION tree, choose ``value`` in its list, commit it: the setting
    applies at once (as a choice of the user does)."""
    def editor():
        from qgis.PyQt.QtWidgets import QComboBox
        view = dock().config_view
        return next((c for c in view.viewport().findChildren(QComboBox) if c.isVisible()), None)

    def open_editor():
        view = dock().config_view
        item = config_item(path)
        index = view_index(view, item)
        view.setCurrentIndex(index)
        view.edit(index)

        def popup():
            combo = editor()
            if combo is None:
                log(f'no editor for {path}')
                return
            combo.showPopup()
        QTimer.singleShot(250, popup)

    def choose():
        combo = editor()
        if combo is None:
            hide_popup()
            return
        i = combo.findText(value)
        if i < 0:
            i = combo.findText(value, Qt.MatchFlag.MatchContains)
        if combo.view().isVisible() and i >= 0:
            r = to_main(combo.view().viewport(), combo.view().visualRect(combo.model().index(i, 0)))
            REC.event('point', x=r.center().x(), y=r.center().y())
            REC.event('click', x=r.center().x(), y=r.center().y())
        hide_popup()
        combo.setCurrentIndex(i)
        view = dock().config_view
        view.commitData(combo)
        from qgis.PyQt.QtWidgets import QAbstractItemDelegate
        view.closeEditor(combo, QAbstractItemDelegate.EndEditHint.NoHint)
        log(f'{".".join(path)} -> {value}: {config_item(path).data(Qt.ItemDataRole.UserRole).get("value")}')

    return act(config_value_rect(path), open_editor) + [(keep, choose), hold(500)]


def config_find(text):
    """Click the search field of CONFIGURATION and type the name of a setting: the tree goes to it."""
    return act(config_search, lambda: config_search().setFocus()) + type_into(config_search, text, per_char=70) \
        + [(400, lambda: dock().config_view_container._on_search_enter())]


def stacked_header(key):
    """The header of a section when the headers are stacked."""
    def _r():
        sections = dock()._fm_sections
        if key in sections._headers:
            return rect_of(sections._headers[key])
        return toolbox_button(key)()
    return _r


def header_click(key):
    def run():
        d = dock()
        page = getattr(d, key.upper())
        d.toolBox_tabTools.setCurrentWidget(page)
    return act(stacked_header(key), run)


HEADERS = ('APP', 'DOCKWIDGET', 'SECTION_HEADERS')
BAR = ('APP', 'DOCKWIDGET', 'ACTION_BAR_POSITION')


def open_configuration():
    dock().toolBox_tabTools.setCurrentWidget(dock().CONFIGURATION)


def trim_stacks():
    """The lower stack of the dock gives EXPLORING the band its open section leaves under its rows, or takes back
    what its rows lack. Read on the section itself (its viewport against what its rows ask), so it holds with the
    headers stacked and the buttons under each section, where rows_need() counts a rail."""
    d = dock()
    page = d.toolBox_tabTools.currentWidget()
    if page is None or page is d.CONFIGURATION or page.parentWidget() is None:
        return
    band = page.parentWidget().height() - max(page.sizeHint().height(), page.minimumSizeHint().height())
    sizes = d.splitter_main.sizes()
    if len(sizes) == 2 and band and sizes[1] - band > 0 and sizes[0] + band > 0:
        d.splitter_main.setSizes([sizes[0] + band, sizes[1] - band])
        sections = getattr(d, '_fm_sections', None)
        if sections is not None and hasattr(sections, '_share'):
            sections._share = (sizes[0] + band) / sum(sizes)
    log(f'stacks trimmed by {band}: {d.splitter_main.sizes()}')


def staged_in_configuration(scale):
    """staged(), with CONFIGURATION opened just before the recording starts."""
    steps = staged(scale)
    return steps[:-2] + [(300, open_configuration), (900, wait_idle())] + steps[-2:]


# layout: CONFIGURATION, two settings typed in its search and chosen in the tree, applied at once: the headers stacked
# instead of the rails, the buttons under each section instead of one bar; then FILTERING and EXPORTING opened.
# The window is not fitted: the dock with its headers stacked needs the 120 px a fitted window takes away, and the
# take starts in CONFIGURATION, whose tree takes that height (with FILTERING open it was an empty band).
LAYOUT = boot(PANELS_LAYERS, 'commune', '"nom_officiel" = \'Muret\'', 1.15, fit=None) + staged_in_configuration(1.15) + [
    title('The dock, laid out your way'), caption('1 · CONFIGURATION: every setting, found by its name'),
    hold(1200), (0, cam('dock', dur=1.4, pad=12)), hold(1200),
    (0, cam(lambda: dock().config_view_container, dur=1.2, pad=16)), hold(500),
] + [caption('2 · Section headers: stacked instead of the rail')] + config_find('SECTION_HEADERS') + [hold(700)] + config_choose(HEADERS, 'stacked') + [
    hold(900), (0, cam('dock', dur=1.2, pad=12)), hold(2200),
    (0, cam(lambda: dock().config_view_container, dur=1.2, pad=16)), hold(400),
] + [caption('3 · Action buttons: under each section')] + config_find('ACTION_BAR_POSITION') + [hold(700)] + config_choose(BAR, 'sections') + [
    hold(900), (0, cam(lambda: [dock().toolBox_tabTools, dock().pushButton_action_filter], dur=1.2, pad=16)), hold(400)] \
    + [caption('4 · Applied at once: each section has its own buttons')] \
    + header_click('filtering') + [(350, trim_stacks), hold(2200)] \
    + header_click('exporting') + [(350, trim_stacks), hold(2200)] \
    + header_click('filtering') + [(350, trim_stacks), hold(800), (0, cam('full', dur=1.4)), hold(2400),
                                   (0, stop_recording), (500, quit_when_idle)]


def agent_open_visible():
    return chip_click('agent')


def wizard_card():
    return agent_chat()._wizard._card


def card_option(label):
    def _r():
        card = wizard_card()
        for buttons, _other, _field in card._groups:
            for button, text in buttons:
                if text == label:
                    return rect_of(button)
        return rect_of(card)
    return _r


def card_button(label):
    card = wizard_card()
    for buttons, _other, _field in (card._groups if card is not None else ()):
        for button, text in buttons:
            if text == label:
                return button
    return None


def card_in_view():
    card = wizard_card()
    if card is not None:
        agent_panel().thread.ensureWidgetVisible(card, 10, 10)
        log('card: ' + ' | '.join(f'{c.text()}: ' + ', '.join(f'{t}{"*" if b.isChecked() else ""}' for b, t in g[0])
                                  for c, g in zip(card._chips, card._groups)))


def card_answer():
    """Answer the card in view (its choices as they are, or ticked just before); nothing when the cards are over."""
    def aim():
        card = wizard_card()
        if card is not None:
            r = rect_of(card.answer_button)
            REC.event('point', x=r.center().x(), y=r.center().y())

    def answer():
        card = wizard_card()
        if card is not None:
            r = rect_of(card.answer_button)
            REC.event('click', x=r.center().x(), y=r.center().y())
            card.answer_button.click()
    return [(0, card_in_view), hold(300), (400, aim), (550, answer), hold(600)]


def card_untick(label):
    """Untick ``label`` on the card in view, when it is one of its choices and it is ticked."""
    def aim():
        b = card_button(label)
        if b is not None and b.isChecked():
            r = rect_of(b)
            REC.event('point', x=r.x() + 10, y=r.center().y())

    def untick():
        b = card_button(label)
        log(f'untick {label}: {b is not None and b.isChecked()}')
        if b is not None and b.isChecked():
            r = rect_of(b)
            REC.event('click', x=r.x() + 10, y=r.center().y())
            b.setChecked(False)
    return [(700, aim), (900, untick), hold(900)]


def setup_card(untick=()):
    """One card of the setup, answered as it comes (its choices are ticked as the settings are: the sections all in
    the FilterMate panel, the default); ``untick``: choices unticked first."""
    steps = [(0, card_in_view)]
    for label in untick:
        steps += card_untick(label)
    return steps + card_answer()


SETUP_CARDS = (
    # (a choice only that card has, the caption shown with it, the choices unticked on it)
    ('EXPORTING', '2 · Sections and data: no EXPORTING, vector layers only',
     ('EXPORTING', 'Rasters (images, DEMs)', 'Point clouds (LiDAR)')),
    ('Light', '3 · Look and layout: as they are, in one panel', ()),
    ('Zone', '4 · The tools of EXPLORING: two buttons less', ('Zone', 'Link the single and multiple selections')),
)


def setup_cards():
    """Every card of the setup that is waiting, answered one after the other, however many steps the setup has (it
    gained one in November 2026, and will again): a step that finds a card puts the steps that answer it, and itself
    once more, right after it in the clip; it ends when the cards are over. A card of SETUP_CARDS gets its caption
    and its choices unticked; the others are answered as they are."""
    def step():
        card = wizard_card()
        if card is None:
            return None
        items, untick = [], ()
        for marker, text, labels in SETUP_CARDS:
            if card_button(marker) is not None:
                items, untick = [caption(text)], labels
                break
        items += setup_card(untick=untick) + [(0, setup_cards())]
        at = RUN['at'] + 1
        STEPS[at:at] = items
        return None
    return step


def settings_card():
    return agent_chat()._settings_cards[-1]


def apply_card():
    """Apply on the card that sums the changes up (logged)."""
    def run():
        card = settings_card()
        log('changes: ' + ' | '.join(row.text() for row in card.rows))
        card.apply_button.click()
    return [(0, lambda: agent_panel().thread.ensureWidgetVisible(settings_card(), 10, 10)), hold(400)] \
        + act(lambda: settings_card().apply_button, run)


def shown_sections():
    """Log what the setup left in the dock: its sections, and the buttons of the rail of EXPLORING."""
    sections = dock()._fm_sections
    log('FILTERING / EXPORTING shown: ' + ', '.join(key for key in ('filtering', 'exporting')
                                                    if sections.section_shown(key)))
    try:
        from filter_mate.ui.controllers.exploring_tool_choice import BUTTONS
        shown = []
        for name, button in BUTTONS['vector'].items():  # some are attributes of the dock, others only its children
            widget = getattr(dock(), button, None) or dock().findChild(QWidget, button)
            if widget is not None and not widget.isHidden():
                shown.append(name)
        log('rail of EXPLORING: ' + ', '.join(shown))
    except Exception:
        log(traceback.format_exc())


# setup: "Set up FilterMate, no model needed" in AGENT: cards of choices. The first one asks which sections and data
# are used: EXPORTING, rasters and point clouds are unticked. The card of the tools of EXPLORING loses two buttons.
# The others are answered as they are (the sections all in the FilterMate panel), Apply: the dock, still in one
# piece, keeps what is used; EXPORTING and its Export button are gone, the rail of EXPLORING is shorter.
SETUP = boot(PANELS_LAYERS, 'commune', '"nom_officiel" = \'Muret\'', 1.15) + [
    (0, lambda: agent_chat().new_conversation())] + staged(1.15) + [
    title('Only the tools you use'), caption('1 · Open AGENT, then Set up FilterMate: no AI model needed'),
    hold(1000), (0, cam('dock', dur=1.4, pad=12)), hold(500),
] + agent_open_visible() + [hold(900), (0, cam(agent_panel, dur=1.3, pad=12)), hold(500)] \
    + act(lambda: agent_panel().setup_button, lambda: agent_panel().setup_button.click()) + [hold(1000)] \
    + [(0, setup_cards())] + [
    hold(400), caption('5 · Apply: the panel keeps what you use'),
    (0, cam(agent_panel, dur=1.0, pad=12)),
] + apply_card() + [hold(1400), (0, shown_sections)] + chip_click('filtering') + [
    hold(900), (0, cam('dock', dur=1.3, pad=12)), hold(2800), (0, cam('full', dur=1.5)), hold(2600),
    (0, stop_recording), (500, quit_when_idle)]


# ------------------------------------------------------------------ second cut of the stories
# What the plain takes leave out: the side buttons of EXPLORING (identify, selecting, tracking), the browser of the
# picker to walk through a result, Undo and Redo, and the English text of the edit: the question of the take (title),
# one line per step (caption), the count it ends on (result), drawn by site_video_render.py. The dock stays in one
# piece, as a new install shows it. (A first version set a section apart in its own panel beside the map: the panel
# and the dock were both half empty, 19 November 2026.)
def single_group():
    """Single selection opened by the check box of its group, as a click there does."""
    d = dock()
    d.mGroupBox_exploring_single_selection.setChecked(True)
    name = iface.activeLayer().name()
    if DISPLAY.get(name):
        d.mFieldExpressionWidget_exploring_single_selection.setExpression(DISPLAY[name])


def picker_next():
    """The 'next' button of the browser of the single selection picker."""
    from qgis.PyQt.QtWidgets import QToolButton
    buttons = [b for b in dock().mFeaturePickerWidget_exploring_single_selection.findChildren(QToolButton)
               if b.isVisible()]
    return buttons[-1] if buttons else dock().mFeaturePickerWidget_exploring_single_selection


def walk(times, each=1500):
    """Next, next, next: with tracking on, the map goes to each feature of the result."""
    steps = []
    for i in range(times):
        steps += act(picker_next, lambda: picker_next().click(), lead=500, after=200 if i else 700) + [hold(each)]
    return steps


def identify():
    return act('pushButton_exploring_identify', lambda: dock().pushButton_exploring_identify.click(),
               lead=700, after=300)


def back_to_scene():
    """The framing of the scene again, tracking off: the closing shot shows the whole result."""
    dock().pushButton_checkable_exploring_tracking.setChecked(False)
    refocus()


MULTI_ZONE = ['mGroupBox_exploring_single_selection', 'mGroupBox_exploring_multiple_selection']

# noise, second cut (story 2): the main roads of Muret picked by an expression and flashed (identify), the buffer by
# road class, Filter.
NOISE2 = boot(S2_LAYERS, 'commune', f'"nom_officiel" = \'{PLACE_NOISE}\'', 1.2) + scope('commune') \
    + recorded_scene(1.2) + [
    still('s2-00'), title('Which buildings are near the main roads?'), hold(500),
    caption('1 · Pick the main roads'),
] + pick_layer('troncon_de_route') + [(900, cam(EXPLORE_ZONE, dur=1.2, pad=30))] \
    + typed_custom('"importance" IN (\'1\', \'2\')', per_char=24) \
    + settle() + [(0, cam('full', dur=1.1)), hold(200)] + identify() + [
    note_expr('major roads', 'troncon_de_route', '"importance" IN (\'1\', \'2\')'),
    hold(1200), still('s2-01'),
    caption('2 · Target the buildings'), (0, cam(FILTER_ZONE, dur=1.2, pad=40)),
] + targets(['batiment', 'erp'], per_item=220, close_after=500) + predicates(['intersect'], per_item=260, close_after=500) + [
    caption('3 · Buffer by road class: 300, 250 or 100 m'),
] + act('pushButton_checkable_filtering_buffer_value', buffer_value(0), lead=600, after=500) \
    + act('mPropertyOverrideButton_filtering_buffer_value_property',
          buffer_expr_dialog(NOISE_EXPR, keep_menu=1200, keep_dialog=2400), lead=600, after=500) \
    + combo_choose('comboBox_filtering_buffer_type', 'Flat', keep=800) + [
    hold(300), still('s2-03'), caption('4 · Filter'), (200, cam('full', dur=1.1)),
] + run_filter() + [
    result('{batiment:,} buildings · {erp:,} public buildings', ['batiment', 'erp']),
    hold(1800), still('s2-04'), (0, zoom_focus(0.5)),
] + settle() + show_map(2600, 1.05) + [still('s2-05')] + ending(['batiment', 'erp', 'troncon_de_route'])

# bridges, second cut (story 4): the permanent watercourses of Toulouse Métropole flashed, the roads and structures
# that cross them kept; then the structures walked one by one, tracking on: the map follows.
BRIDGES2 = boot(S4_LAYERS, 'epci', '"nom_officiel" = \'Toulouse Métropole\'', 1.1, dense_scale=400000) \
    + scope('epci') + recorded_scene(1.1) + [
    still('s4-00'), title('Which crossings to inspect?'), hold(500),
    caption('1 · Pick the permanent watercourses'),
] + pick_layer('troncon_hydrographique') + [(900, cam(EXPLORE_ZONE, dur=1.2, pad=30))] \
    + typed_custom('"persistance" = \'Permanent\'', per_char=24) + settle() + [
    note('scope', ['troncon_de_route', 'troncon_hydrographique', 'construction_lineaire', 'commune']),
    note_expr('permanent', 'troncon_hydrographique', '"persistance" = \'Permanent\''),
    still('s4-01'), (0, cam('full', dur=1.1)), hold(200),
] + identify() + [
    hold(1200), still('s4-02'),
    caption('2 · Target roads and structures that cross them'), (0, cam(FILTER_ZONE, dur=1.2, pad=40)),
] + targets(['troncon_de_route', 'construction_lineaire'], per_item=220, close_after=500) \
    + predicates(['cross'], per_item=260, close_after=500) + [
    hold(300), still('s4-03'), caption('3 · Filter'), (200, cam('full', dur=1.1)),
] + run_filter() + [
    result('{troncon_de_route:,} road sections · {construction_lineaire:,} structures',
           ['troncon_de_route', 'construction_lineaire']),
    hold(1800), still('s4-04'),
    caption('4 · Walk through them, the map follows'),
] + pick_layer('construction_lineaire') + [(900, cam(EXPLORE_ZONE, dur=1.2, pad=30))] \
    + act(gb_check('mGroupBox_exploring_single_selection'), single_group, lead=600, after=400) \
    + act('pushButton_checkable_exploring_tracking', enable('pushButton_checkable_exploring_tracking'),
          lead=600, after=400) + [
    (300, cam('full', dur=1.1)),
] + walk(3, each=1300) + [still('s4-05'), (0, back_to_scene)] + settle() + [
    result('{troncon_de_route:,} road sections · {construction_lineaire:,} structures',
           ['troncon_de_route', 'construction_lineaire']), hold(2200),
] + ending(['troncon_de_route', 'construction_lineaire'])


def clean_export_dir():
    """What an earlier take left in the export folder would go into the ZIP of this one."""
    if os.path.isdir(EXPORT_DIR):
        for name in os.listdir(EXPORT_DIR):
            path = os.path.join(EXPORT_DIR, name)
            if os.path.isfile(path):
                os.remove(path)


def zip_written():
    """Re-armed until the ZIP of the export is on the disk."""
    return not any(name.endswith('.zip') for name in (os.listdir(EXPORT_DIR) if os.path.isdir(EXPORT_DIR) else []))


def exported():
    """Log what the export wrote (the result line of the take says it)."""
    names = sorted(os.listdir(EXPORT_DIR)) if os.path.isdir(EXPORT_DIR) else []
    log(f'exported {[(n, os.path.getsize(os.path.join(EXPORT_DIR, n))) for n in names]}')


def open_exporting():
    dock().toolBox_tabTools.setCurrentWidget(dock().EXPORTING)


# export, second cut (story 1): EXPORTING opened by its chip in the dock; its six buttons, one after the other, then
# Export. The window is fitted to EXPORTING too, which has one row more than FILTERING.
EXPORT2 = boot(S1_LAYERS, 'commune', f'"nom_officiel" = \'{PLACE_EXPORT}\'', 1.3, fit=('FILTERING', 'EXPORTING')) \
    + scope('commune') + [(0, clean_export_dir)] + recorded_scene(1.3) + [
    note('scope', S1_TARGETS),
    title('One commune, one file to hand over'), hold(500),
    caption('1 · Open EXPORTING, choose the layers'), (0, cam('dock', dur=1.2, pad=10)),
] + act(toolbox_button('export'), open_exporting, lead=700, after=500) + [
    (300, cam(EXPORT_ZONE, dur=1.2, pad=40)),
] + act('pushButton_checkable_exporting_layers', enable('pushButton_checkable_exporting_layers'), lead=600, after=400) \
    + combo_check('checkableComboBoxLayer_exporting_layers', S1_TARGETS, per_item=150, close_after=500) + [
    (200, export_layers_changed), caption('2 · Projection, styles, format'),
] + act('pushButton_checkable_exporting_projection', enable('pushButton_checkable_exporting_projection'),
        lead=600, after=400) \
    + act('pushButton_checkable_exporting_styles', enable('pushButton_checkable_exporting_styles'),
          lead=600, after=400) \
    + act('pushButton_checkable_exporting_datatype', enable('pushButton_checkable_exporting_datatype'),
          lead=600, after=400) + [
    (300, export_datatype), caption('3 · Folder and ZIP'),
] + act('pushButton_checkable_exporting_output_folder', enable('pushButton_checkable_exporting_output_folder'),
        lead=600, after=400) \
    + act(folder_edit, lambda: folder_edit().clear(), lead=500, after=300) \
    + type_into(folder_edit, EXPORT_DIR, per_char=20, clear=False) \
    + act('pushButton_checkable_exporting_zip', enable('pushButton_checkable_exporting_zip'), lead=600, after=400) + [
    (300, export_zip), hold(500), still('s1-04'), caption('4 · Export'), (0, cam('full', dur=1.1)),
] + act('pushButton_action_export', export_with_recap, lead=700, after=500) + [(2400, mark('still:s1-05'))] \
    + settle(3.0) + [
    (300, speed(4.0)), (300, zip_written), (300, speed(1.0)),
    (0, exported), result(f'{len(S1_TARGETS)} layers · one GeoPackage, styles kept · zipped'), hold(3200),
] + ending()


def click_redo():
    dock().pushButton_action_redo_filter.click()


S3_RESULT = '{batiment:,} buildings · {erp:,} public buildings · {troncon_de_route:,} road sections'

# buffer, second cut (story 3): the water of Grenade, 300 m then 100 m around it, then Undo and Redo walk the two
# steps.
BUFFER2 = boot(S3_LAYERS, 'commune', f'"nom_officiel" = \'{PLACE_RIVER}\'', 1.2) + scope('commune') \
    + recorded_scene(1.2) + [
    still('s3-00'), title('What stands near the river?'), hold(300),
    caption('1 · Pick all the water surfaces'),
] + pick_layer('surface_hydrographique') + [(700, cam(MULTI_ZONE, dur=1.0, pad=30))] \
    + act(gb_check('mGroupBox_exploring_multiple_selection'), multi_mode, lead=500, after=300) + [hold(500)] \
    + select_all_multi_menu(keep=1000) + settle() + [
    hold(300), still('s3-01'),
    caption('2 · Target buildings and roads, 300 m around'), (0, cam(FILTER_ZONE, dur=1.2, pad=40)),
] + targets(S3_FLOOD_TARGETS, per_item=170, close_after=400, lead=500, after=350) \
    + predicates(['intersect'], per_item=220, close_after=400, lead=500, after=350) \
    + act('pushButton_checkable_filtering_buffer_value', buffer_value(0), lead=500, after=300) + typed_buffer(300) + [
    hold(300), still('s3-02'), caption('3 · Filter'), (200, cam('full', dur=1.1)),
] + run_filter(fast=10.0) + [
    note('300 m', S3_FLOOD_TARGETS), result('300 m: ' + S3_RESULT, S3_FLOOD_TARGETS), hold(1500), still('s3-03'),
    caption('4 · Try 100 m'), (0, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + typed_buffer(100) + run_filter(fast=10.0) + [
    (0, cam('full', dur=1.1)),
    note('100 m', S3_FLOOD_TARGETS), result('100 m: ' + S3_RESULT, S3_FLOOD_TARGETS), hold(1500), still('s3-04'),
    caption('5 · Undo, Redo: back and forth between the two'), (0, quiet_message_bar),
    (0, cam(ACTION_ZONE, dur=1.2, pad=40)),
] + act('pushButton_action_undo_filter', click_undo, lead=700, after=400) + settle(4.0) + [(0, refocus)] + settle() + [
    (0, cam('full', dur=1.1)), note('undo', S3_FLOOD_TARGETS), result('300 m again', ()), hold(1500), still('s3-05'),
    (0, cam(ACTION_ZONE, dur=1.1, pad=40)),
] + act('pushButton_action_redo_filter', click_redo, lead=700, after=400) + settle(4.0) + [(0, refocus)] + settle() + [
    (0, quiet_message_bar),
    note('redo', S3_FLOOD_TARGETS), result('100 m: ' + S3_RESULT, S3_FLOOD_TARGETS), hold(1400),
] + ending(S3_FLOOD_TARGETS)


def settled_counts(names, quiet=6):
    """Re-armed until the counts of ``names`` have stayed the same for ``quiet`` polls (a favorite replayed filters
    its layers one after the other, with no task to wait for)."""
    seen = {'last': None, 'same': 0}

    def _s():
        now = tuple(counts(names).values())
        seen['same'] = seen['same'] + 1 if now == seen['last'] else 0
        seen['last'] = now
        return seen['same'] < quiet
    _s.max_tries = 120
    return _s


def texted(steps, question, inserts):
    """The steps of a take with its text. ``question`` (the title) comes right after the recording starts, then each
    (anchor, step or list of steps) of ``inserts``, where the anchor is 'start' (the recording starts), the name of a
    step image ('s6-02': right after it; ('s6-04', 2): two steps before it), 'filtered' or 'filtered1' (the first,
    the second filter of the scene is over)."""
    out = list(steps)

    def place(anchor):
        name, before = anchor if isinstance(anchor, tuple) else (anchor, 0)
        if name == 'start':
            hits = [i for i, (_d, fn) in enumerate(out) if fn is rec_start]
        elif name.startswith('filtered'):
            hits = [i for i, (_d, fn) in enumerate(out) if fn is filtered][int(name[8:] or 0):]
        else:
            hits = [i for i, (_d, fn) in enumerate(out) if getattr(fn, 'mark', None) == 'still:' + name]
        if not hits:
            raise KeyError(f'no {anchor} in the scene')
        return hits[0] - before if before else hits[0] + 1

    for anchor, new in [('start', title(question))] + list(inserts):
        i = place(anchor)
        if anchor == 'start':   # after what the title, or an earlier line, put there
            while i < len(out) and getattr(out[i][1], 'text', False):
                i += 1
        new = new if isinstance(new, list) else [new]
        out[i:i] = new
    return out


HERO = texted(HERO, 'One commune out of a whole department', [
    ('start', caption('1 · Pick the commune')),
    ('s1-01', caption('2 · Target the 12 other layers')),
    ('s1-02', caption('3 · Filter')),
    ('filtered', result('12 layers · {batiment:,} buildings', ['batiment'])),
])
BRUSH = texted(BRUSH, 'Where to clear brush around homes?', [
    ('start', caption('1 · Pick the homes')),
    ('s5-01', caption('2 · Target vegetation and hedges, 50 m around')),
    ('filtered', result('{zone_de_vegetation:,} vegetation areas · {haie:,} hedges', ['zone_de_vegetation', 'haie'])),
    ('s5-02', caption('3 · Keep the woods only')),
    ('s5-03', caption('4 · Filter again')),
    ('filtered1', result('{zone_de_vegetation:,} woods · {haie:,} hedges within 50 m of a home',
                         ['zone_de_vegetation', 'haie'])),
])
HAMLETS = texted(HAMLETS, 'Which hamlets are far from a paved road?', [
    ('start', caption('1 · Pick the paved roads')),
    ('s6-02', caption('2 · Target the places: none within 200 m')),
    ('s6-03', caption('3 · Filter')),
    ('filtered', result('{zone_d_habitation:,} places more than 200 m from a paved road', ['zone_d_habitation'])),
])
FAVORITES = texted(FAVORITES, 'A filter saved, replayed in one click', [
    ('start', caption('1 · Save the filter as a favorite')),
    ('s7-01', caption('2 · Clear everything')),
    ('s7-02', caption('3 · Replay it from the favorites')),
    (('s7-04', 2), [(300, speed(3.0)), (300, settled_counts(S3_FLOOD_TARGETS)), (0, speed(1.0)),
                    result(S3_RESULT, S3_FLOOD_TARGETS)]),
])
PROCESSING = texted(PROCESSING, 'What changed since a date?', [
    ('start', caption('1 · FilterMate in the Processing toolbox')),
    ('s8-01', caption('2 · Batch filter: four layers, one expression')),
    ('s8-02', caption('3 · Run')),
    (('s8-03', 2), result('Modified since 15 March 2025: {batiment:,} buildings · {troncon_de_route:,} roads',
                          ['batiment', 'troncon_de_route'])),
])
SLOPE = texted(SLOPE, 'Which parcels lie on steep slopes?', [
    ('start', caption('1 · Compute the slope of the terrain model')),
    ('s9-01', caption(f'2 · Keep {FM5_SLOPE_MIN:g} % and steeper')),
    ('s9-02', caption('3 · Target the parcels at least half on it')),
    ('s9-03', caption('4 · Filter')),
    ('filtered', result('{parcelle:,} parcels on steep slopes', ['parcelle'])),
])
FM5_HEIGHT_MIN = int(os.environ.get('FM5_HEIGHT', '7'))
HEIGHTS = texted(HEIGHTS, f'Which buildings rise above {FM5_HEIGHT_MIN} m?', [
    ('start', caption('1 · Pick the building points of the LiDAR cloud')),
    ('s10-01', caption(f'2 · Keep the points {FM5_HEIGHT_MIN} m above the ground')),
    ('s10-02', caption('3 · Target the buildings half covered by them')),
    ('s10-03', caption('4 · Filter')),
    ('filtered', result('{batiment:,} buildings rise to ' + str(FM5_HEIGHT_MIN) + ' m or more', ['batiment'])),
])
PRUNING = texted(PRUNING, 'Which roads need pruning?', [
    ('start', caption('1 · Pick the high vegetation of the LiDAR cloud')),
    ('s11-01', caption('2 · Keep what stands 8 m above the ground')),
    ('s11-02', caption('3 · Target the roads within 3 m')),
    ('s11-03', caption('4 · Filter')),
    ('filtered', result('{troncon_de_route:,} road sections to prune', ['troncon_de_route'])),
])
NDVI = texted(NDVI, 'Vegetation of an infrared image, on the RGB one', [
    ('start', caption('1 · Tell the bands: infrared, red, green')),
    ('s13-01', caption('2 · Keep the vegetation: NDVI > 0.3')),
    ('s13-02', caption('3 · Target the RGB orthophoto')),
    ('s13-03', caption('4 · Filter')),
])
ROOFS = texted(ROOFS, 'The LiDAR points beneath two roofs', [
    ('start', caption('1 · The RGB orthophoto, on the roofs')),
    ('s14-01', caption('2 · Pipette: click a roof, Ctrl+click the next one')),
    ('s14-02', caption('3 · Target the LiDAR point cloud')),
    ('s14-03', caption('4 · Filter')),
])
GROUND = texted(GROUND, 'The terrain model where the ground was measured', [
    ('start', caption('1 · The classes of the LiDAR cloud')),
    ('s15-01', caption('2 · Keep the ground (class 2)')),
    ('s15-02', caption('3 · Target the terrain model')),
    ('s15-03', caption('4 · Filter')),
])
WIRES = texted(WIRES, 'High vegetation near the power lines', [
    ('start', caption('1 · The survey loaded twice: network and vegetation')),
    ('s16-01', caption('2 · Vegetation copy: class 5 only, filtered alone')),
    ('s16-02', caption('3 · Network copy: the wire conductors (class 14)')),
    ('s16-03', caption('4 · Target the vegetation, 10 m around the wires')),
])
SURVEY = texted(SURVEY, 'A survey package around one building', [
    ('start', caption('1 · Pick the tallest building')),
    ('s12-01', caption('2 · Target the terrain model and the point cloud, 50 m around')),
    ('s12-02', caption('3 · Filter')),
    ('s12-03', caption('4 · Export both into one ZIP')),
])


CLIPS = {'hero': HERO, 'panels': PANELS, 'exploring-panel': EXPLORING_PANEL, 'layout': LAYOUT, 'setup': SETUP,
         'metropole': METROPOLE, 'compare': COMPARE, 'sam': SAM, 'agent': AGENT, 'postgis': POSTGIS,
         'explore': EXPLORE, 'buffer': BUFFER2, 'noise': NOISE2, 'bridges': BRIDGES2, 'brush': BRUSH,
         'hamlets': HAMLETS, 'favorites': FAVORITES, 'export': EXPORT2, 'processing': PROCESSING,
         'slope': SLOPE, 'heights': HEIGHTS, 'pruning': PRUNING, 'survey': SURVEY,
         'ndvi': NDVI, 'roofs': ROOFS, 'ground': GROUND, 'wires': WIRES,
         # the first cut of the four stories told again with the buttons of EXPLORING, Undo / Redo and the walk
         # through a result (the teaser was edited from them)
         'noise_plain': NOISE, 'buffer_plain': BUFFER, 'bridges_plain': BRIDGES, 'export_plain': EXPORT}
STEPS = CLIPS[CLIP]
RUN = {'at': 0}  # the index of the step that runs: a step may put steps after itself (setup_cards)


def run_steps(i=0, tries=0):
    if i >= len(STEPS):
        return
    delay, fn = STEPS[i]

    # A step returning True is a wait: it is re-armed every 250 ms (100 s at most).
    def go():
        if tries == 0:
            log(f'--- step {i} {getattr(fn, "__name__", fn)}')
        again = False
        RUN['at'] = i
        try:
            again = fn() is True
        except Exception:
            log(traceback.format_exc())
        if again and tries < getattr(fn, 'max_tries', 400):
            run_steps(i, tries + 1)
        else:
            run_steps(i + 1)
    QTimer.singleShot(delay if tries == 0 else 250, go)


log(f'clip {CLIP}, {len(STEPS)} steps')
QTimer.singleShot(15000, run_steps)
