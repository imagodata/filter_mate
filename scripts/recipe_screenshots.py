# -*- coding: utf-8 -*-
"""Per-step screenshots of the website "stories" (business use cases), one QGIS run each.

Usage (Windows QGIS driven from WSL or a Windows shell)::

    set FM_RECIPE=s1
    set FM_OUT=C:\\Users\\Simon\\AppData\\Local\\Temp\\fm_shots\\recipes
    set FM_GPKG=C:\\Users\\Simon\\Documents\\bdtopo31\\BDT_3-5_GPKG_LAMB93_D031-ED2026-03-15.gpkg
    qgis-bin.exe --nologo --lang en --code scripts/recipe_screenshots.py

Data: the full BD TOPO 3.5 GeoPackage of a French department (Haute-Garonne,
2.9 GB, 1.17 M buildings, 383 k road segments, 416 k hedges, EPSG:2154), as
downloaded from the IGN Géoplateforme. Every story starts by scoping the whole
department to one commune or EPCI with FilterMate itself, then answers a
business question with a second, chained filter.

Each story is a list of ``(delay_ms, callable)`` steps run on a QTimer chain
after QGIS and the plugins have loaded. A callable returning True is re-armed
after the same delay (used to wait for the filter task). Every capture is the
whole QGIS window scaled to 1600 px wide; some steps also save the panel alone.
After every Filter the feature counts are logged and compared with ``EXPECT``
when a value is known, so the documentation cannot show a wrong result.

Stories (see website/stories.fr.html):
  s1  the commune dossier: scope 12 layers to Saint-Gaudens, export a GPKG project
  s2  buildings exposed to major-road noise in Muret (buffer by expression, Flat)
  s3  flood setback along the Garonne in Grenade (300 m then 100 m, AND, Undo)
  s4  bridges of Toulouse Métropole (EPCI scope, Cross)
  s5  brush clearing around homes in Bagnères-de-Luchon (expression, chained AND)
  s6  hamlets far from any paved road in Aspet (Processing scope, Disjoint + buffer, AND)
  s7  favorites: save story s3, replay it, manage it
  s8  Processing: what changed since the last edition, department-wide

Layer names, fields and values are those of BD TOPO 3.5; adapt them for
another dataset.
"""
import os
import traceback

from qgis.PyQt.QtCore import QTimer, Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QApplication, QDockWidget, QLineEdit
from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRectangle, QgsProperty,
    QgsFeatureRequest, QgsExpression, QgsSymbol, QgsSingleSymbolRenderer,
)
from qgis.utils import iface, plugins

RECIPE = os.environ.get('FM_RECIPE', 's1').lower()
OUT = os.environ.get('FM_OUT', r'C:\Users\Simon\AppData\Local\Temp\fm_shots\recipes')
GPKG = os.environ.get('FM_GPKG', r'C:\Users\Simon\Documents\bdtopo31\BDT_3-5_GPKG_LAMB93_D031-ED2026-03-15.gpkg')
EXPORT_DIR = os.path.join(OUT, 'export')
LOG = os.path.join(OUT, f'{RECIPE}.log')
STATE = {}

# Expected feature counts after a filter, when verified independently (see
# scripts/recipe_counts.py). Missing keys are only logged.
EXPECT = {}

STYLE = {  # layer name: (color, line/stroke width or point size, fill opacity)
    'commune': ('#6b7280', 0.8, 0.0),
    'epci': ('#6b7280', 1.2, 0.0),
    'zone_d_habitation': ('#f0a040', 0.6, 0.18),
    'zone_de_vegetation': ('#4c9a3c', None, 0.45),
    'foret_publique': ('#2f6f3e', None, 0.35),
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


def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(str(m) + '\n')


# ------------------------------------------------------------------ helpers
def dock():
    return plugins['filter_mate'].app.dockwidget


def layer(name):
    return QgsProject.instance().mapLayersByName(name)[0]


def save_window(name):
    pm = iface.mainWindow().grab().scaledToWidth(1600, Qt.TransformationMode.SmoothTransformation)
    ok = pm.save(os.path.join(OUT, f'{RECIPE}-{name}.png'), 'PNG')
    log(f'saved {RECIPE}-{name} {pm.width()}x{pm.height()} ok={ok}')


def save_widget(widget, name, max_width=None):
    pm = widget.grab()
    if max_width and pm.width() > max_width:
        pm = pm.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)
    ok = pm.save(os.path.join(OUT, f'{RECIPE}-{name}.png'), 'PNG')
    log(f'saved widget {RECIPE}-{name} {pm.width()}x{pm.height()} ok={ok}')


def save_screen_rect(widget, name):
    p = widget.mapToGlobal(widget.rect().topLeft()) if widget.parent() else widget.pos()
    pm = QApplication.primaryScreen().grabWindow(0, p.x(), p.y(), widget.width(), widget.height())
    ok = pm.save(os.path.join(OUT, f'{RECIPE}-{name}.png'), 'PNG')
    log(f'saved screen {RECIPE}-{name} {pm.width()}x{pm.height()} ok={ok}')


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
    log(f'combo {combo.objectName()} items={[combo.itemText(k) for k in range(combo.count())]} -> {text} idx={i}')
    if i >= 0:
        combo.setCurrentIndex(i)


def fids_where(name, expr):
    return [f.id() for f in layer(name).getFeatures(QgsFeatureRequest(QgsExpression(expr)))]


def counts(names):
    # featureCount() is -1 on an OGR layer carrying a SQL subset: iterate instead.
    out = {}
    for n in names:
        req = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry).setNoAttributes()
        out[n] = sum(1 for _ in layer(n).getFeatures(req))
    log(f'counts {out}')
    recount_tree()
    return out


def recount_tree():
    """Force the Layers panel to recompute its [n] feature counts after a filter."""
    for node in QgsProject.instance().layerTreeRoot().findLayers():
        node.setCustomProperty('showFeatureCount', False)
        node.setCustomProperty('showFeatureCount', True)


def check(key, names):
    got = counts(names)
    for n, v in EXPECT.get(key, {}).items():
        log(f'{"OK" if got.get(n) == v else "MISMATCH"} {key} {n}: got {got.get(n)} expected {v}')
    for n in names:
        log(f'subset {n}: {layer(n).subsetString()[:300]!r}')


def set_extent(rect):
    STATE['extent'] = QgsRectangle(rect)
    iface.mapCanvas().setExtent(STATE['extent'])
    iface.mapCanvas().refresh()


def restore_extent():
    if 'extent' in STATE:
        iface.mapCanvas().setExtent(STATE['extent'])
        iface.mapCanvas().refresh()


def style_layer(vl, style):
    """Replace whatever renderer the GeoPackage carries by one flat symbol."""
    if not style:
        return
    color, width, opacity = style
    sym = QgsSymbol.defaultSymbol(vl.geometryType())
    sym.setColor(QColor(color))
    if vl.geometryType() == 0 and hasattr(sym, 'setSize') and width:  # point
        sym.setSize(width)
    elif width is not None and hasattr(sym, 'setWidth'):
        sym.setWidth(width)
    if vl.geometryType() == 2:  # polygon
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
    n = QgsApplication.taskManager().countActiveTasks()
    if n:
        log(f'waiting: {n} active task(s)')
    return n > 0


# ------------------------------------------------------------------ generic steps
def setup(layer_names, focus_layer, focus_expr, scale=1.25):
    """Load layers (bottom to top), zoom to the feature of focus_layer matching focus_expr."""
    def _s():
        mw = iface.mainWindow()
        mw.showNormal()
        mw.resize(1760, 1040)
        for d in mw.findChildren(QDockWidget):
            if d.objectName() in ('MessageLog', 'Browser', 'Browser2', 'ProcessingToolbox'):
                d.hide()
        canvas = iface.mapCanvas()
        canvas.setRenderFlag(False)
        canvas.setCanvasColor(QColor('#f7f7f4'))
        # translucent selection colour: the selected commune must not hide its content
        canvas.setSelectionColor(QColor(255, 225, 0, 70))
        root = QgsProject.instance().layerTreeRoot()
        for name in layer_names:
            vl = QgsVectorLayer(f'{GPKG}|layername={name}', name, 'ogr')
            log(f'{name} valid={vl.isValid()} count={vl.featureCount()}')
            QgsProject.instance().addMapLayer(vl)
            node = root.findLayer(vl.id())
            if node:
                node.setCustomProperty('showFeatureCount', True)
            # the IGN GeoPackage ships styles with scale-dependent visibility
            vl.setScaleBasedVisibility(False)
            try:
                style_layer(vl, STYLE.get(name))
            except Exception:
                log(traceback.format_exc())
        fids = fids_where(focus_layer, focus_expr)
        log(f'focus {focus_layer} {focus_expr} -> {fids}')
        STATE['focus_fid'] = fids[0]
        STATE['focus_layer'] = focus_layer
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
    return lambda: iface.setActiveLayer(layer(name))


def single_focus(tracking=False):
    """Single selection of the focus feature, display expression from DISPLAY."""
    def _s():
        d = dock()
        name = iface.activeLayer().name()
        d.mGroupBox_exploring_single_selection.setChecked(True)
        if DISPLAY.get(name):
            d.mFieldExpressionWidget_exploring_single_selection.setExpression(DISPLAY[name])
        if tracking:
            d.pushButton_checkable_exploring_tracking.setChecked(True)
        QTimer.singleShot(1500, lambda: d.mFeaturePickerWidget_exploring_single_selection.setFeature(STATE['focus_fid']))
    return _s


def select_all():
    def _s():
        d = dock()
        w = d.checkableComboBoxFeaturesListPickerWidget_exploring_multiple_selection
        d.mGroupBox_exploring_multiple_selection.setChecked(True)
        expr = DISPLAY.get(iface.activeLayer().name() if iface.activeLayer() else '')
        if expr:
            d.mFieldExpressionWidget_exploring_multiple_selection.setExpression(expr)
        QTimer.singleShot(3000, lambda: w.select_all('Select All'))
    return _s


def custom(expr):
    def _s():
        d = dock()
        d.mGroupBox_exploring_custom_selection.setChecked(True)
        d.mFieldExpressionWidget_exploring_custom_selection.setExpression(expr)
    return _s


def targets(names=None):
    """Check the target layers; names=None checks every layer (right-click > Select All)."""
    def _s():
        d = dock()
        d.toolBox_tabTools.setCurrentIndex(0)
        d.pushButton_checkable_filtering_layers_to_filter.setChecked(True)
        check_combo_items(d.checkableComboBoxLayer_filtering_layers_to_filter, names or [''], uncheck_others=True)
        d.checkableComboBoxLayer_filtering_layers_to_filter.checkedItemsChangedEvent()
    return _s


def predicates(names):
    def _s():
        d = dock()
        d.pushButton_checkable_filtering_geometric_predicates.setChecked(True)
        check_combo_items(d.comboBox_filtering_geometric_predicates, names, uncheck_others=True)
    return _s


def buffer(value=None, expr=None, btype=None):
    def _s():
        d = dock()
        if value is None and expr is None:
            d.pushButton_checkable_filtering_buffer_value.setChecked(False)
            return
        d.pushButton_checkable_filtering_buffer_value.setChecked(True)
        if value is not None:
            d.mQgsDoubleSpinBox_filtering_buffer_value.setValue(value)
        if expr is not None:
            w = d.mPropertyOverrideButton_filtering_buffer_value_property
            w.setToProperty(QgsProperty.fromExpression(expr))
            w.setActive(True)
            d.filtering_buffer_property_changed()
        if btype is not None:
            d.pushButton_checkable_filtering_buffer_type.setChecked(True)
            set_combo_text(d.comboBox_filtering_buffer_type, btype)
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


def click_redo():
    dock().pushButton_action_redo_filter.click()


def click_unfilter():
    dock().pushButton_action_unfilter.click()


def wait_tasks():
    return tasks_running  # re-armed while it returns True


def grab(name, panel=False):
    def _s():
        restore_extent()
        iface.mapCanvas().waitWhileRendering()
        QApplication.processEvents()
        save_window(name)
        if panel:
            save_widget(dock(), name + '-panel')
    return _s


def zoom_focus(scale):
    """Zoom on the focus feature (commune or EPCI) with the given bbox scale factor."""
    def _s():
        f = layer(STATE['focus_layer']).getFeature(STATE['focus_fid'])
        bb = f.geometry().boundingBox()
        bb.scale(scale)
        set_extent(bb)
    return _s


def expect(key, names):
    return lambda: check(key, names)


def quit_qgis():
    QgsProject.instance().setDirty(False)
    QgsApplication.instance().quit()


def scope(scope_layer, targets_names=None, tracking=True):
    """Steps that restrict every layer to the focus feature of scope_layer (commune or EPCI)."""
    return [
        (500, source(scope_layer)), (2500, single_focus(tracking=tracking)), (4000, grab('01')),
        (500, targets(targets_names)), (500, predicates(['intersect'])), (500, buffer(None)), (2500, grab('02', panel=True)),
        (500, click_filter), (3000, wait_tasks()), (2000, lambda: None),
    ]


# ------------------------------------------------------------------ stories
S1_LAYERS = ['commune', 'zone_de_vegetation', 'surface_hydrographique', 'zone_d_habitation', 'terrain_de_sport',
             'cimetiere', 'equipement_de_transport', 'batiment', 'haie', 'troncon_hydrographique',
             'troncon_de_route', 'construction_lineaire', 'erp']
S1_TARGETS = [n for n in S1_LAYERS if n != 'commune']


def export_tab(names, fmt='GPKG', zip_name=None):
    def _s():
        d = dock()
        d.toolBox_tabTools.setCurrentIndex(1)
        d.pushButton_checkable_exporting_layers.setChecked(True)
        check_combo_items(d.checkableComboBoxLayer_exporting_layers, names, uncheck_others=True)
        d.checkableComboBoxLayer_exporting_layers.checkedItemsChangedEvent()
        d.pushButton_checkable_exporting_projection.setChecked(True)
        d.pushButton_checkable_exporting_styles.setChecked(True)
        d.pushButton_checkable_exporting_datatype.setChecked(True)
        set_combo_text(d.comboBox_exporting_datatype, fmt)
        d.pushButton_checkable_exporting_output_folder.setChecked(True)
        os.makedirs(EXPORT_DIR, exist_ok=True)
        d.lineEdit_exporting_output_folder.setText(EXPORT_DIR)
        if zip_name:
            d.pushButton_checkable_exporting_zip.setChecked(True)
            d.lineEdit_exporting_zip.setText(os.path.join(EXPORT_DIR, zip_name))
    return _s


def export_click(shot):
    def _s():
        def grab_recap():
            w = getattr(dock(), '_export_recap_dialog', None) or QApplication.activeModalWidget()
            log(f'recap {w}')
            if w:
                save_widget(w, shot + '-recap')
                save_window(shot)
                w.accept()
        QTimer.singleShot(2500, grab_recap)
        dock().pushButton_action_export.click()
    return _s


def export_listing():
    try:
        log('export dir: ' + ', '.join(sorted(os.listdir(EXPORT_DIR))))
    except Exception:
        log(traceback.format_exc())


S1 = [
    (1000, setup(S1_LAYERS, 'commune', '"nom_officiel" = \'Saint-Gaudens\'', 1.3)), (3000, open_plugin), (8000, size_dock),
] + scope('commune', None) + [
    (500, expect('s1', S1_TARGETS)), (500, grab('03')),
    (500, zoom_focus(0.45)), (2500, grab('04')),
    (500, zoom_focus(1.3)), (500, export_tab(S1_TARGETS, 'GPKG', 'saint_gaudens.zip')), (2500, grab('05', panel=True)),
    (500, export_click('06')), (3000, wait_tasks()), (5000, export_listing), (500, grab('07')),
    (1500, quit_qgis),
]

S2_LAYERS = ['commune', 'zone_d_habitation', 'batiment', 'troncon_de_voie_ferree', 'troncon_de_route', 'erp']
S2_TARGETS = [n for n in S2_LAYERS if n != 'commune']
NOISE_EXPR = 'CASE WHEN "importance" = \'1\' THEN 300 WHEN "importance" = \'2\' THEN 250 ELSE 100 END'

S2 = [
    (1000, setup(S2_LAYERS, 'commune', '"nom_officiel" = \'Muret\'', 1.2)), (3000, open_plugin), (8000, size_dock),
] + scope('commune', None) + [
    (500, expect('s2a', S2_TARGETS)), (500, grab('03')),
    (500, source('troncon_de_route')), (3000, custom('"importance" IN (\'1\', \'2\')')), (3000, grab('04')),
    (500, targets(['batiment', 'erp'])), (500, predicates(['intersect'])),
    (500, buffer(expr=NOISE_EXPR, btype='Flat')), (500, combine(None, 'AND')), (2500, grab('05', panel=True)),
    (500, click_filter), (3000, wait_tasks()), (2000, expect('s2', ['batiment', 'erp', 'troncon_de_route'])), (500, grab('06')),
    (500, zoom_focus(0.5)), (2500, grab('07')),
    (1500, quit_qgis),
]

S3_LAYERS = ['commune', 'zone_d_habitation', 'surface_hydrographique', 'batiment', 'troncon_hydrographique',
             'troncon_de_route', 'erp']
S3_TARGETS = [n for n in S3_LAYERS if n != 'commune']
S3_FLOOD_TARGETS = ['batiment', 'erp', 'troncon_de_route']

S3 = [
    (1000, setup(S3_LAYERS, 'commune', '"nom_officiel" = \'Grenade\'', 1.2)), (3000, open_plugin), (8000, size_dock),
] + scope('commune', None) + [
    (500, expect('s3a', S3_TARGETS)), (500, grab('03')),
    (500, source('surface_hydrographique')), (3000, select_all()), (6000, grab('04')),
    (500, targets(S3_FLOOD_TARGETS)), (500, predicates(['intersect'])),
    (500, buffer(300)), (500, combine(None, 'AND')), (2500, grab('05', panel=True)),
    (500, click_filter), (3000, wait_tasks()), (2000, expect('s3b', S3_FLOOD_TARGETS)), (500, grab('06')),
    (500, buffer(100)), (500, click_filter), (3000, wait_tasks()), (2000, expect('s3c', S3_FLOOD_TARGETS)), (500, grab('07')),
    (500, click_undo), (3000, wait_tasks()), (2000, expect('s3b', S3_FLOOD_TARGETS)), (500, grab('08')),
    (1500, quit_qgis),
]

S4_LAYERS = ['epci', 'commune', 'surface_hydrographique', 'troncon_hydrographique', 'troncon_de_route', 'construction_lineaire']
S4_TARGETS = [n for n in S4_LAYERS if n != 'epci']

S4 = [
    (1000, setup(S4_LAYERS, 'epci', '"nom_officiel" = \'Toulouse Métropole\'', 1.1)), (3000, open_plugin), (8000, size_dock),
] + scope('epci', None) + [
    (500, expect('s4a', S4_TARGETS)), (500, grab('03')),
    (500, source('troncon_hydrographique')), (3000, custom('"persistance" = \'Permanent\'')), (3000, grab('04')),
    (500, targets(['troncon_de_route', 'construction_lineaire'])), (500, predicates(['cross'])),
    (500, buffer(None)), (500, combine(None, 'AND')), (2500, grab('05', panel=True)),
    (500, click_filter), (3000, wait_tasks()), (2000, expect('s4', ['troncon_de_route', 'construction_lineaire'])), (500, grab('06')),
    (500, zoom_focus(0.22)), (2500, grab('07')),
    (1500, quit_qgis),
]

S5_LAYERS = ['commune', 'foret_publique', 'zone_de_vegetation', 'zone_d_habitation', 'batiment', 'haie', 'troncon_de_route']
S5_TARGETS = [n for n in S5_LAYERS if n != 'commune']
WOOD_EXPR = '"nature" IN (\'Bois\', \'Forêt fermée de feuillus\', \'Forêt fermée de conifères\', \'Forêt fermée mixte\', \'Forêt ouverte\')'

S5 = [
    (1000, setup(S5_LAYERS, 'commune', '"nom_officiel" = \'Bagnères-de-Luchon\'', 1.15)), (3000, open_plugin), (8000, size_dock),
] + scope('commune', None) + [
    (500, expect('s5a', S5_TARGETS)), (500, grab('03')),
    (500, source('batiment')), (3000, custom('"usage_1" = \'Résidentiel\'')), (3000, grab('04')),
    (500, targets(['zone_de_vegetation', 'haie'])), (500, predicates(['intersect'])),
    (500, buffer(50)), (500, combine(None, 'AND')), (2500, grab('05', panel=True)),
    (500, click_filter), (3000, wait_tasks()), (2000, expect('s5b', ['zone_de_vegetation', 'haie'])), (500, grab('06')),
    (500, source('zone_de_vegetation')), (3000, custom(WOOD_EXPR)), (500, combine('AND', None)), (2500, grab('07', panel=True)),
    (500, click_filter), (3000, wait_tasks()), (2000, expect('s5', ['zone_de_vegetation', 'haie'])), (500, grab('08')),
    (500, zoom_focus(0.35)), (2500, grab('09')),
    (1500, quit_qgis),
]

S6_LAYERS = ['commune', 'zone_de_vegetation', 'zone_d_activite_ou_d_interet', 'zone_d_habitation', 'batiment', 'troncon_de_route']
S6_SCOPE_TARGETS = ['zone_de_vegetation', 'batiment', 'troncon_de_route']
S6_TARGETS = ['zone_d_habitation', 'zone_d_activite_ou_d_interet']
PAVED_EXPR = '"nature" NOT IN (\'Chemin\', \'Sentier\', \'Escalier\', \'Piste cyclable\', \'Route empierrée\')'
ASPET_EXPR = '"insee_commune" = \'31020\''


def s6_processing_scope():
    """Attribute scope of the two target layers with the Processing batch filter."""
    import processing
    res = processing.run('filtermate:batch_filter', {'INPUT_LAYERS': [layer(n) for n in S6_TARGETS], 'EXPRESSION': ASPET_EXPR})
    log(f'processing result {res}')


S6 = [
    (1000, setup(S6_LAYERS, 'commune', '"nom_officiel" = \'Aspet\'', 1.15)), (3000, open_plugin), (8000, size_dock),
] + scope('commune', S6_SCOPE_TARGETS) + [
    (500, expect('s6a', S6_SCOPE_TARGETS)), (500, s6_processing_scope), (3000, wait_tasks()), (2000, expect('s6b', S6_TARGETS)), (500, grab('03')),
    (500, source('troncon_de_route')), (3000, custom(PAVED_EXPR)), (3000, grab('04')),
    (500, targets(S6_TARGETS)), (500, predicates(['disjoint'])),
    (500, buffer(200)), (500, combine(None, 'AND')), (2500, grab('05', panel=True)),
    (500, click_filter), (3000, wait_tasks()), (2000, expect('s6', S6_TARGETS)), (500, grab('06')),
    (1500, quit_qgis),
]


FAV_NAME = 'PPRI Garonne 300 m'


def fav_add():
    ok = dock()._favorites_ctrl.add_current_to_favorites(FAV_NAME)
    log(f'favorite added {ok}')


def fav_menu(shot):
    def _s():
        def grab_popup():
            w = QApplication.activePopupWidget()
            log(f'popup {w}')
            if w:
                save_screen_rect(w, shot + '-menu')
                save_window(shot)
                w.close()
        QTimer.singleShot(1200, grab_popup)
        dock()._favorites_ctrl.handle_indicator_clicked()
    return _s


def fav_apply():
    ctrl = dock()._favorites_ctrl
    for f in ctrl.get_all_favorites():
        if getattr(f, 'name', '') == FAV_NAME:
            log(f'apply favorite {f.id}: {ctrl.apply_favorite(f.id)}')
            return
    log('favorite not found')


def fav_manager(shot):
    def _s():
        def grab_modal():
            w = QApplication.activeModalWidget()
            log(f'modal {w}')
            if w:
                w.resize(960, 640)
                QTimer.singleShot(600, lambda: (save_widget(w, shot + '-manager'), save_window(shot), w.reject()))
        QTimer.singleShot(1500, grab_modal)
        dock()._favorites_ctrl.show_manager_dialog()
    return _s


def fav_export():
    path = os.path.join(OUT, 'favoris_ppri.json')
    try:
        log(f'export favorites {path}: {dock()._favorites_ctrl.export_favorites(path)}')
    except Exception:
        log(traceback.format_exc())


def fav_cleanup():
    ctrl = dock()._favorites_ctrl
    for f in ctrl.get_all_favorites():
        if getattr(f, 'name', '') == FAV_NAME:
            log(f'remove favorite {f.id}: {ctrl.remove_favorite(f.id)}')


# s7 rebuilds the 300 m result of s3 (no captures), then works with favorites.
S7 = [
    (1000, setup(S3_LAYERS, 'commune', '"nom_officiel" = \'Grenade\'', 1.2)), (3000, open_plugin), (8000, size_dock),
    (500, source('commune')), (2500, single_focus(tracking=True)), (4000, lambda: None),
    (500, targets(None)), (500, predicates(['intersect'])), (500, buffer(None)),
    (500, click_filter), (3000, wait_tasks()), (2000, lambda: counts(S3_TARGETS)),
    (500, source('surface_hydrographique')), (3000, select_all()), (6000, lambda: None),
    (500, targets(S3_FLOOD_TARGETS)), (500, predicates(['intersect'])),
    (500, buffer(300)), (500, combine(None, 'AND')),
    (500, click_filter), (3000, wait_tasks()), (2000, expect('s3b', S3_FLOOD_TARGETS)),
    (500, fav_add), (2500, fav_menu('01')), (3000, lambda: None),
    (500, click_unfilter), (3000, wait_tasks()), (2000, lambda: counts(S3_FLOOD_TARGETS)), (500, grab('02')),
    (500, fav_apply), (3000, wait_tasks()), (2000, expect('s3b', S3_FLOOD_TARGETS)), (500, grab('03')),
    (500, fav_manager('04')), (4000, lambda: None),
    (500, fav_export), (500, fav_cleanup), (1500, quit_qgis),
]


CHANGED_EXPR = '"date_modification" >= \'2025-03-15\''
S8_LAYERS = ['commune', 'batiment', 'troncon_hydrographique', 'troncon_de_route', 'erp']
S8_TARGETS = ['batiment', 'troncon_de_route', 'troncon_hydrographique', 'erp']


def s8_toolbox():
    mw = iface.mainWindow()
    for d in mw.findChildren(QDockWidget):
        if d.objectName() == 'ProcessingToolbox':
            d.show()
            d.raise_()
            mw.resizeDocks([d], [360], Qt.Orientation.Horizontal)
            for le in d.findChildren(QLineEdit):
                le.setText('filtermate')
                break


def s8_dialog():
    import processing
    dlg = processing.createAlgorithmDialog('filtermate:batch_filter', {
        'INPUT_LAYERS': [layer(n) for n in S8_TARGETS],
        'EXPRESSION': CHANGED_EXPR,
    })
    dlg.resize(860, 640)
    dlg.show()
    STATE['proc'] = dlg


def s8_grab_dialog():
    dlg = STATE.get('proc')
    if dlg:
        save_widget(dlg, '02-dialog')
        save_window('02')
        dlg.close()


def s8_run():
    import processing
    res = processing.run('filtermate:batch_filter', {'INPUT_LAYERS': [layer(n) for n in S8_TARGETS], 'EXPRESSION': CHANGED_EXPR})
    log(f'processing result {res}')


S8 = [
    (1000, setup(S8_LAYERS, 'commune', '"nom_officiel" = \'Toulouse\'', 1.6)), (3000, open_plugin), (8000, size_dock),
    (500, s8_toolbox), (2500, grab('01')),
    (500, s8_dialog), (3500, s8_grab_dialog),
    (500, s8_run), (3000, wait_tasks()), (2000, expect('s8', S8_TARGETS)), (500, grab('03')),
    (1500, quit_qgis),
]

RECIPES = {'s1': S1, 's2': S2, 's3': S3, 's4': S4, 's5': S5, 's6': S6, 's7': S7, 's8': S8}
STEPS = RECIPES[RECIPE]


def run_steps(i=0, tries=0):
    if i >= len(STEPS):
        return
    delay, fn = STEPS[i]

    def go():
        if tries == 0:
            log(f'--- step {i} {getattr(fn, "__name__", fn)}')
        again = False
        try:
            again = fn() is True
        except Exception:
            log(traceback.format_exc())
        if again and tries < 200:
            run_steps(i, tries + 1)
        else:
            run_steps(i + 1)
    QTimer.singleShot(delay, go)


log(f'story {RECIPE}, {len(STEPS)} steps')
QTimer.singleShot(15000, run_steps)
