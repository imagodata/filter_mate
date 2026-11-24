r"""The favorites manager of FilterMate as a user sees it, grabbed to PNG in a real QGIS without a screen.

Starts the plugin, loads three layers, saves four favorites (one with remote layers, a spatial configuration and tags;
a plain one; one with 400 ids and a long name; a global one), shows the dialog non-modally and grabs the dock, each
tab of the first favorite, the long-name favorite, the global favorite and the message of a refused rename to ``FM_GRAB_DIR`` (default ``/out``).
``FM_THEME=dark`` (or ``light``) sets ``APP.DOCKWIDGET.COLORS.ACTIVE_THEME`` before the plugin starts. The language
is the one of QGIS (``--lang fr``); ``FM_LOCALE=fr`` sets the locale of the dates, as the machine of a user does
(the container has the C locale): this checks the localized date of the usage line on Qt5 and Qt6.

    docker run --rm -v "$PWD:/src:ro" -v /tmp/shots:/out -e FM_THEME=dark -e FM_LOCALE=fr qgis/qgis:ltr bash -c \
      "timeout 260 dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' qgis --nologo --noversioncheck \
       --lang fr --profiles-path /tmp/p --code /src/tests/qgis_headless/capture_favorites_manager.py"

Prints ``dialog dark: <bool>``, then ``done`` and the PNG names; exits 2 after 240 s. Read the PNGs: nothing here compares pixels.
"""
import json
import os
import shutil
import sys
import tempfile
import traceback
from qgis.core import QgsFeature, QgsGeometry, QgsProject, QgsRectangle, QgsSettings, QgsVectorFileWriter, QgsVectorLayer
from qgis.PyQt.QtCore import QLocale, Qt, QTimer
from qgis.PyQt.QtWidgets import QApplication, QTabWidget, QListWidget
from qgis.utils import iface
import qgis.utils
OUT = os.environ.get("FM_GRAB_DIR") or "/out"
os.makedirs(OUT, exist_ok=True)
# QGIS < 3.28 runs --code with exec() and no __file__: FM_REPO (default /src, the mount) then.
REPO = os.environ.get("FM_REPO") or (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                     if "__file__" in globals() else "/src")
PKG = "filter_mate"
EXCL = ('.git', '.github', '.claude', '.serena', '_bmad', '_bmad-output', 'dist', 'build', 'scripts', 'knowledge',
        'website', 'tests', 'docs', 'logs', '__pycache__', '*.pyc', 'test_*.py')
QTimer.singleShot(240000, lambda: os._exit(2))
qgis.utils.showException = lambda *a, **k: print("EXC", a[1] if len(a) > 1 else a, flush=True)

def close_modal():
    m = QApplication.activeModalWidget()
    if m is not None and not getattr(m, "_keep", False):
        print("modal closed:", m.windowTitle(), flush=True); m.reject() if hasattr(m, "reject") else m.close()
T = QTimer(); T.timeout.connect(close_modal); T.start(1000)

def layer(name, n):
    mem = QgsVectorLayer("Polygon?crs=EPSG:2154&field=nom:string&field=type:string&field=surface:double", "m", "memory")
    fs = []
    for i in range(n):
        f = QgsFeature(mem.fields()); f.setGeometry(QgsGeometry.fromRect(QgsRectangle(i*20, 0, i*20+10, 10)))
        f.setAttributes([f"{name}_{i}", "A" if i % 2 else "B", i * 1.5]); fs.append(f)
    mem.dataProvider().addFeatures(fs)
    o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName, o.layerName = "GPKG", name
    p = f"/tmp/{name}.gpkg"; QgsVectorFileWriter.writeAsVectorFormatV3(mem, p, QgsProject.instance().transformContext(), o)
    l = QgsVectorLayer(f"{p}|layername={name}", name, "ogr"); QgsProject.instance().addMapLayer(l); return l

def start():
    if os.environ.get("FM_LOCALE"):  # the dates of the dialog follow the locale of the machine, C in the container
        QLocale.setDefault(QLocale(os.environ["FM_LOCALE"]))
    s = QgsSettings(); s.setValue('FilterMate/whats_new_seen', 99); s.setValue('FilterMate/discord_welcome_dismissed', True)
    s.setValue('qgis/digitizing/validate_geometries', 0)
    iface.mainWindow().resize(1600, 1000); iface.mainWindow().show()
    plugins = os.path.join(tempfile.mkdtemp(), 'plugins'); shutil.copytree(REPO, os.path.join(plugins, PKG), ignore=shutil.ignore_patterns(*EXCL))
    if os.environ.get("FM_THEME"):  # the dock opens with this theme, as saved before
        for name in ("config.default.json", "config.json"):
            path = os.path.join(plugins, PKG, "config", name)
            with open(path, encoding="utf-8") as stream:
                config = json.load(stream)
            config["APP"]["DOCKWIDGET"]["COLORS"]["ACTIVE_THEME"]["value"] = os.environ["FM_THEME"]
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(config, stream, indent=2)
    sys.path.insert(0, plugins); qgis.utils.plugin_paths.insert(0, plugins); qgis.utils.updateAvailablePlugins()
    print("started", qgis.utils.loadPlugin(PKG) and qgis.utils.startPlugin(PKG), flush=True)
    qgis.utils.plugins[PKG].run()

def data():
    global parcelles, routes, bati
    parcelles, routes, bati = layer("parcelles", 30), layer("troncon_de_route", 40), layer("batiment", 50)
    QgsProject.instance().write("/tmp/demo.qgz")

def favs():
    svc = qgis.utils.plugins[PKG].app.favorites_manager
    svc.add_favorite("Parcelles A > 20 m²", '"type" = \'A\' AND "surface" > 20', layer_name="parcelles", layer_provider="ogr",
                     remote_layers={"ogr::troncon_de_route": {"expression": '"fid" IN (1,2,3,4,5,6,7,8,9,10,11,12)', "feature_count": 12,
                                    "layer_id": routes.id(), "display_name": "troncon_de_route", "provider": "ogr"},
                                    "ogr::batiment": {"expression": 'intersects($geometry, geom_from_wkt(\'POLYGON((0 0,100 0,100 10,0 10,0 0))\'))',
                                    "feature_count": 5, "layer_id": bati.id(), "display_name": "batiment", "provider": "ogr"}},
                     spatial_config={"geometric_predicates": ["Intersect", "Within"], "has_geometric_predicates": True, "buffer_value": 25.0,
                                     "exploring_groupbox": "custom_selection"},
                     tags=["urbanisme", "PLU"], description="Parcelles de type A de plus de 20 m² et les routes et bâtiments qui les touchent")
    svc.add_favorite("Routes", '"nom" LIKE \'troncon_de_route_1%\'', layer_name="troncon_de_route", layer_provider="ogr")
    svc.add_favorite("Un favori au nom vraiment très long pour voir comment la liste le coupe ou le déborde",
                     '"fid" IN (' + ",".join(str(i) for i in range(1, 400)) + ')', layer_name="batiment", layer_provider="ogr")
    fid = svc.add_favorite("Bâtiments B", '"type" = \'B\'', layer_name="batiment", layer_provider="ogr")
    svc.copy_to_global(fid)
    print("favs", svc.count, flush=True)

def shots():
    from filter_mate.ui.dialogs import FavoritesManagerDialog
    app = qgis.utils.plugins[PKG].app
    dw = app.dockwidget
    dw.grab().save(f"{OUT}/0_dock.png")
    global dlg
    dlg = FavoritesManagerDialog(app.favorites_manager, dw, extension_bridge=None); dlg._keep = True
    dlg.show(); dlg.raise_()
    print("dialog dark:", dlg._dark, flush=True)
    QTimer.singleShot(1500, shots2)

def select(prefix, is_global=False):
    """Select the favorite whose name starts with ``prefix`` (and is global, or not); rows are sorted, so not stable."""
    lst = dlg.findChild(QListWidget)
    for row in range(lst.count()):
        fav = dlg._find_favorite(lst.item(row).data(Qt.ItemDataRole.UserRole))
        if fav is not None and fav.name.startswith(prefix) and dlg._favorite_is_global(fav) == is_global:
            lst.setCurrentRow(row)
            return True
    print("no favorite starting with", prefix, flush=True)
    return False

def shots2():
    select("Parcelles")
    QTimer.singleShot(800, lambda: shots3(0))

def shots3(i):
    tabs = dlg.findChild(QTabWidget)
    if tabs is not None and i < tabs.count():
        tabs.setCurrentIndex(i); QApplication.processEvents()
        QTimer.singleShot(500, lambda: (dlg.grab().save(f"{OUT}/1_dialog_tab{i}.png"), shots3(i + 1)))
        return
    select("Un favori"); tabs.setCurrentIndex(0)
    QTimer.singleShot(600, longname)

def longname():
    dlg.grab().save(f"{OUT}/2_dialog_longname.png")
    select("Bâtiments B", is_global=True)
    QTimer.singleShot(600, done)

def done():
    dlg.grab().save(f"{OUT}/3_dialog_global.png")
    select("Routes"); dlg._tab_widget.setCurrentIndex(0); dlg._name_edit.setText("")
    dlg._on_save()  # refused: the message shows on the bar at the top of the dialog
    QTimer.singleShot(800, refused)

def refused():
    bar = dlg._message_bar
    print("message bar:", type(bar).__name__, "visible:", bar.isVisible(), flush=True)
    dlg.grab().save(f"{OUT}/4_dialog_refused.png")
    print("done", sorted(os.listdir(OUT)), flush=True); os._exit(0)

STEPS = [(start, 8), (data, 6), (favs, 2), (shots, 0)]
def run(i=0):
    if i == len(STEPS): return
    f, w = STEPS[i]
    try: f()
    except Exception: traceback.print_exc()
    QTimer.singleShot(int(w*1000), lambda: run(i+1))
QTimer.singleShot(2000, run)
