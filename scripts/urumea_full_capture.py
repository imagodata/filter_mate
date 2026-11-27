"""Urumea from an empty project: real agent acquisition, filtering and deliverables.

Executed by QGIS --code in an isolated desktop/profile with an unmodified dist.
The camera records the desktop, including real native dialogs and composers.
No data are preloaded and no successful result is substituted for a failed step.
"""
from pathlib import Path
exec(compile(Path('/w/scripts/urumea_linkedin_capture.py').read_text(),
             '/w/scripts/urumea_linkedin_capture.py', 'exec'), globals())
from qgis.PyQt.QtWidgets import QFileDialog, QDialog, QDialogButtonBox, QPlainTextEdit, QMessageBox
from qgis.PyQt.QtCore import QSize
from qgis.core import QgsSettings

WINDOW = (1920, 990)
PHASE = os.environ.get('FM_ZERO_PHASE', 'acquire')
SESSION = Path(os.environ.get('FM_ZERO_PROJECT', '/w/exports/urumea/urumea.qgz'))
MNT_URL = json.loads(Path('/w/sources/mnt-source.json').read_text())['url']
URA_URL = json.loads(Path('/w/sources/ura-source.json').read_text())['url']
BASE_CONFIGURE = configure_agent
BASE_CHECKPOINT = checkpoint


def type_into(get_edit, text, per_char=8, clear=True):
    # QTest.keyClicks asserts on a newline in Qt 6. Multiline D3 prompts are
    # entered through the real edit widget, including Unicode and newlines.
    steps = []
    if clear:
        steps.append((0, lambda: get_edit().clear()))
    for char in text:
        steps.append((per_char, lambda char=char: get_edit().insertPlainText(char)))
    return steps


class DesktopRecorder(Recorder):
    def start(self):
        super().start()
        self.size = (1920, 1080)

    def _tick(self):
        try:
            pm = QApplication.primaryScreen().grabWindow(0)
            self.times.append(round(self.now(), 4))
            self.queue.put((len(self.times) - 1, pm.toImage()))
        except Exception:
            log(traceback.format_exc())


REC = DesktopRecorder(OUT, FPS)


def setup_visible():
    canvas = prepare_window()
    project = QgsProject.instance()
    project.clear()
    metric = QgsCoordinateReferenceSystem('EPSG:25830')
    project.setCrs(metric)
    canvas.setDestinationCrs(metric)
    bounds = QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), metric, project).transformBoundingBox(QgsRectangle(*AREA))
    STATE.update(scene_rect=bounds, boot_extent=bounds)
    if PHASE != 'acquire':
        if not project.read(str(SESSION)):
            raise RuntimeError('Cannot resume the previously acquired project')
    elif project.mapLayers():
        raise RuntimeError('The opening project must be empty')
    canvas.setExtent(bounds)
    canvas.setRenderFlag(True)
    canvas.refresh()
    SESSION.parent.mkdir(parents=True, exist_ok=True)


def configure_agent():
    BASE_CONFIGURE()
    from filter_mate.adapters.agent.settings import load_settings, save_settings
    # File acquisition is explicitly allowed through the data platforms. URLs
    # supplied in the prompt are the verified official sources, not invented search results.
    old = load_settings()
    save_settings(replace(old, enabled_sources=('overpass_fr', 'photon', 'earth_search'),
                          expert_python=True,
                          tool_rules=json.dumps({'add_osm_features': 'allow', 'add_layer': 'allow',
                                                 'run_algorithm': 'allow', 'export_layers': 'allow'})))
    agent_chat()._refresh_ready()
    restore_view()


def restore_view():
    # QGIS can reset the canvas CRS during delayed empty-project initialization.
    metric = QgsCoordinateReferenceSystem('EPSG:25830')
    QgsProject.instance().setCrs(metric)
    canvas = iface.mapCanvas()
    canvas.setDestinationCrs(metric)
    canvas.setRenderFlag(True)
    canvas.setExtent(STATE['scene_rect'])
    canvas.refresh()


def presentation(stage):
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    styles = {
        'Bâtiments': ('#c5b295', '#8c806e', '0.08'),
        'Bâtiments pente': ('#e75d35', '#9b3b24', '0.08'),
        'Couloir Urumea 500 m': ('33,133,189,32', '33,133,189,170', '0.35'),
        'URA T100': ('54,160,203,62', '#2694b4', '0.25'),
    }
    for vector in project.mapLayers().values():
        if isinstance(vector, QgsVectorLayer):
            if vector.name() in styles and vector.geometryType() == 2:
                color, outline, width = styles[vector.name()]
                vector.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(
                    {'color': color, 'outline_color': outline, 'outline_width': width})))
            elif vector.geometryType() == 1:
                color = '#1687bc' if vector.name() == 'Urumea' else '#cc8d40' if 'Ponts' in vector.name() else '#7e878c'
                width = '1.2' if vector.name() == 'Urumea' else '0.65' if 'Ponts' in vector.name() else '0.22'
                vector.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple(
                    {'line_color': color, 'line_width': width})))
            root.findLayer(vector.id()).setExpanded(False)
            vector.triggerRepaint()
    # Presentation only: source IDs, features, filters and chart numbers stay untouched.
    order = ['Ponts lignes', 'Ponts polygones', 'Bâtiments pente', 'Bâtiments', 'Urumea',
             'Routes', 'URA T100', 'Couloir Urumea 500 m', 'Pente (%)', 'MNT GeoEuskadi 5 m']
    root.setHasCustomLayerOrder(True)
    root.setCustomLayerOrder(sorted(project.mapLayers().values(),
                                   key=lambda item: order.index(item.name()) if item.name() in order else 99))
    for name in ('URA officiel',):
        for item in project.mapLayersByName(name):
            root.findLayer(item.id()).setItemVisibilityChecked(False)
    if project.mapLayersByName('Bâtiments pente'):
        for item in project.mapLayers().values():
            if item.name() == 'Bâtiments' or item.name().endswith('source WGS84'):
                root.findLayer(item.id()).setItemVisibilityChecked(False)
        for item in project.mapLayersByName('Pente (%)'):
            root.findLayer(item.id()).setItemVisibilityChecked(stage == 'terrain')
    restore_view()


def checkpoint(stage):
    def check():
        presentation(stage)
        BASE_CHECKPOINT(stage)()
        project = QgsProject.instance()
        if stage == 'sources':
            required = {'Bâtiments', 'Routes', 'Ponts lignes', 'Ponts polygones', 'Urumea',
                        'MNT GeoEuskadi 5 m', 'URA officiel'}
            absent = required - {item.name() for item in project.mapLayers().values()}
            if absent:
                raise RuntimeError('Missing acquired layers: ' + ', '.join(sorted(absent)))
            raster = project.mapLayersByName('MNT GeoEuskadi 5 m')[0]
            if not raster.isValid() or abs(raster.rasterUnitsPerPixelX() - 5) > .01:
                raise RuntimeError('The acquired terrain raster is not the verified 5 m MNT')
        if stage == 'terrain':
            if not project.mapLayersByName('Bâtiments pente') or not project.mapLayersByName('Pente (%)'):
                raise RuntimeError('The actual slope computation is missing')
        if stage in ('corridor', 't100', 'reseau'):
            filtered = current_filters()
            buildings = project.mapLayersByName('Bâtiments pente')
            if not buildings or not buildings[0].subsetString() or exact_count(buildings[0]) <= 0:
                raise RuntimeError('The river/building selection must be real and non-empty')
        if stage == 'composer':
            layout = project.layoutManager().layoutByName('Urumea — analyse')
            if layout is None:
                raise RuntimeError('No actual composer was created')
        project.setDirty(True)
    return check


def ask(stage, text):
    return [(0, lambda: STATE.update(demo_request=stage)),
            (0, lambda: REC.event('mark', name='ask:' + stage)), (400, agent_open)] + \
        act(lambda: agent_panel().input, lambda: agent_panel().input.setFocus(), lead=200, after=150) + \
        type_into(lambda: agent_panel().input, text, per_char=8) + \
        act(lambda: agent_panel().send_button, lambda: agent_panel().send_button.click(), lead=300, after=400) + \
        [(1000, wait_agent(stage)), (500, wait_idle()), (0, checkpoint(stage)),
         hold(4000), still('result-' + stage), hold(2000)]


NATIVE = {'seen': set(), 'file': set(), 'refs': []}


def service_dialogs():
    """Fill real dialogs; never replace QFileDialog or the save controller."""
    for widget in QApplication.topLevelWidgets():
        if not widget.isVisible():
            continue
        if widget is not iface.mainWindow() and widget.inherits('QgsLayoutDesignerDialog'):
            widget.setGeometry(315, 145, 1115, 800)
            for designer in iface.openLayoutDesigners():
                if designer.window() is widget:
                    designer.view().zoomFull()
        if isinstance(widget, QFileDialog) and id(widget) not in NATIVE['file']:
            NATIVE['file'].add(id(widget))
            NATIVE['refs'].append(widget)
            widget.setGeometry(420, 220, 900, 570)
            def choose(widget=widget):
                if sip.isdeleted(widget):
                    return
                widget.setDirectory(str(SESSION.parent))
                def fill():
                    widget.selectFile(SESSION.name)
                    edit = widget.findChild(QLineEdit, 'fileNameEdit')
                    if edit is not None:
                        edit.setText(SESSION.name)
                    log('native dialog destination entered')
                QTimer.singleShot(700, fill)
                REC.event('mark', name='native-save-dialog')
                QTimer.singleShot(3800, widget.accept)
            QTimer.singleShot(1000, choose)
        elif isinstance(widget, QDialog) and widget.findChild(QPlainTextEdit) is not None:
            widget.setGeometry(330, 165, 1090, 760)
            if id(widget) not in NATIVE['seen']:
                NATIVE['seen'].add(id(widget))
                NATIVE['refs'].append(widget)
                buttons = widget.findChild(QDialogButtonBox)
                if buttons and buttons.button(QDialogButtonBox.StandardButton.Yes):
                    QTimer.singleShot(5500, buttons.button(QDialogButtonBox.StandardButton.Yes).click)
        elif isinstance(widget, QMessageBox) and widget.button(QMessageBox.StandardButton.Yes):
            if id(widget) not in NATIVE['seen']:
                NATIVE['seen'].add(id(widget))
                NATIVE['refs'].append(widget)
                QTimer.singleShot(2000, widget.button(QMessageBox.StandardButton.Yes).click)
    # Expert code is displayed in the plugin's actual confirmation interface.
    # This recording is authorized to run its own acquisition/layout/chart code.


DIALOG_TIMER = QTimer()
DIALOG_TIMER.setInterval(250)
DIALOG_TIMER.timeout.connect(service_dialogs)
DIALOG_TIMER.start()


def native_save():
    from filter_mate.ui.widgets.agent_thread import ConfirmCard
    cards = [card for card in agent_panel().thread.findChildren(ConfirmCard)
             if card.isVisible() and not card.done and 'Data' in str(getattr(card, 'texts', ''))]
    if not cards:
        cards = [card for card in agent_panel().thread.findChildren(ConfirmCard)
                 if card.isVisible() and not card.done]
    REC.event('mark', name='native-save-card')
    if cards:
        QTimer.singleShot(2500, cards[-1].yes_button.click)
    else:
        # At a final save the initial card is already answered. Use the native
        # controller again to write new results, which opens the actual dialog.
        QTimer.singleShot(1000, agent_chat()._data.save)


def saved():
    if SESSION.exists() and not QApplication.activeModalWidget():
        return False
    return True
saved.max_tries = 600


def wait_agent(stage):
    seen = set()
    state = {'ticks': 0}
    def step():
        from filter_mate.ui.widgets.agent_thread import ConfirmCard
        state['ticks'] += 1
        busy = agent_chat().chat_busy() or agent_panel()._working
        # The save offer is answered separately after the request has ended.
        if busy:
            for card in agent_panel().thread.findChildren(ConfirmCard):
                if card.isVisible() and not card.done and id(card) not in seen:
                    seen.add(id(card))
                    QTimer.singleShot(3500, card.yes_button.click)
        if not busy and state['ticks'] >= 4:
            return False
        return True
    step.max_tries = 3200
    return step


def show_section(section):
    def show():
        dock().toolBox_tabTools.setCurrentWidget(getattr(dock(), section.upper()))
        REC.event('mark', name='panel:' + section)
    return show


ACQUIRE = (
    "Partons de ce projet vide à Saint-Sébastien. Acquiers les données sur le rectangle WGS84 "
    "[-1.985,43.295,-1.948,43.324]. Avec Overpass, ajoute les bâtiments (polygones) « Bâtiments », "
    "les routes highway (lignes) « Routes », les ponts bridge (lignes et polygones séparés) « Ponts lignes » "
    "et « Ponts polygones ». Pour la couche « Urumea », utilise UNE requête Overpass avec UNIQUEMENT "
    "le tag waterway=river, geometry=lines. Ne fais PAS une requête name=Urumea : les segments urbains portent un nom différent. "
    "Nous filtrerons les noms contenant Urumea ensuite. "
    "Voici deux liens officiels déjà identifiés : ajoute le GeoTIFF numérique de terrain « MNT GeoEuskadi 5 m » "
    "depuis " + MNT_URL + " ; et le ZIP shapefile « URA officiel » depuis " + URA_URL + ". "
    "Le projet est en EPSG:25830. Mets les vecteurs au-dessus du raster, zoome sur le rectangle demandé. "
    "Ne filtre pas, ne calcule pas encore. Réponds brièvement sur les données effectivement ajoutées."
)

ANALYSIS = [
    ('preparer', 'Prépare les données acquises : reprojette les CINQ couches OSM en EPSG:25830 avec native:reprojectlayer (Bâtiments, Routes, Ponts lignes, Ponts polygones, Urumea). Renomme les originales en ajoutant « source WGS84 », masque-les et donne aux copies métriques les noms initiaux exacts. Les données restent complètes. Inspecte les valeurs name de « Urumea » puis filtre avec lower(coalesce("name", \'\')) LIKE \'%urumea%\' : les segments urbains ne portent pas forcément le nom exact Urumea. Contrôle que l’étendue de la rivière recouvre le secteur [582334,4794075,585295,4797333]. Ne filtre pas encore les bâtiments. Conserve le cadrage.'),
    ('terrain', 'À partir du MNT numérique GeoEuskadi 5 m (terrain nu, 2017), calcule une pente en POURCENTAGE avec gdal:slope, AS_PERCENT=true, COMPUTE_EDGES=true, SCALE=1. Nomme le raster « Pente (%) ». Calcule ensuite sa moyenne par emprise de « Bâtiments » avec native:zonalstatisticsfb, préfixe pente_, statistique moyenne seulement, sortie « Bâtiments pente ». Masque les bâtiments originaux. La pente décrit le terrain : aucun seuil de pente ne définit une inondabilité. Conserve toutes les géométries de bâtiments et le cadrage.'),
    ('corridor', 'Commence par filtrer la couche « Urumea » sur son champ name pour ne garder que le fleuve Urumea : les autres waterway=river acquis ne sont pas tous ce fleuve. Inspecte les valeurs avant de choisir. Moteur de filtre FilterMate : garde dans « Bâtiments pente » les bâtiments à moins de 500 MÈTRES de « Urumea », sans supprimer de géométries. Utilise filter avec buffer_distance=500, buffer_type=round, target_layers bâtiments, source rivière, CRS métrique de travail EPSG:25830 si nécessaire : reprojette des COPIES des sources OSM avant le filtre. Crée aussi un tampon dissous visible de 500 m « Couloir Urumea 500 m » sous les bâtiments. Note le nombre de bâtiments avant et après ce premier filtre.'),
    ('t100', 'Dans « URA officiel », sélectionne les zones RIO = Urumea et CODIGO = Q0100 (T100). Fais-en une couche « URA T100 » en EPSG:25830. Avec le moteur de filtre FilterMate, ajoute aux « Bâtiments pente » déjà dans le couloir 500 m un critère ET : intersection avec « URA T100 ». Garde le critère 500 m. Donne le nombre réellement retenu, sans dire que chaque bâtiment sera inondé. La source est le zonage officiel de période de retour 100 ans, pas un calcul de crue par la pente.'),
    ('reseau', 'Avec FilterMate, garde les routes et les objets ponts OSM à moins de 300 mètres des bâtiments actuellement retenus. Utilise « Bâtiments pente » comme source et « Routes », « Ponts lignes », « Ponts polygones » comme cibles. Conserve les filtres actifs des bâtiments et le cadrage. Les objets ponts OSM ne sont pas des ponts physiques distincts.'),
]


def composer_requests():
    analysis = Path(os.environ.get('FM_ANALYSIS_TAKE', '/w/out/analysis01/urumea'))
    acquired = json.loads((Path(os.environ.get('FM_ACQUIRE_TAKE', '/w/out/acquire04/urumea')) / 'sources-observed.json').read_text())
    def count(document, name):
        return next(item['count'] for item in document['layers'] if item['name'] == name)
    total = count(acquired, 'Bâtiments')
    corridor = count(json.loads((analysis / 'corridor-observed.json').read_text()), 'Bâtiments pente')
    final = count(json.loads((analysis / 't100-observed.json').read_text()), 'Bâtiments pente')
    rows = [{'label': label, 'value': value} for label, value in
            [('Données acquises', total), ('Couloir 500 m', corridor), ('Avec URA T100', final)]]
    bar_code = Path('/w/scripts/urumea_progression.d3.js').read_text()
    histogram_code = Path('/w/scripts/urumea_slope_histogram.d3.js').read_text()
    return [
        ('progression', 'Crée un graphique show_chart bar horizontal 700 × 310, sans titre dans le dessin, avec ces comptes réellement observés : '
         + json.dumps(rows, ensure_ascii=False) + '. Ces populations sont emboîtées, ne les additionne pas. '
         'Puis redessine ce graphique avec run_chart_code D3.js (mode expert) en utilisant exactement ce corps de fonction :\n' + bar_code),
        ('histogramme', 'Crée un histogramme show_chart de « Bâtiments pente » TELLE QUE FILTRÉE maintenant, champ pente_mean, 8 classes, dimensions 700 × 240, sans titre. '
         'Donne aussi le nombre de valeurs valides et manquantes, sans les remplacer par zéro. Puis utilise run_chart_code D3.js avec exactement ce corps :\n' + histogram_code),
        ('composer', 'Crée la mise en page « Urumea — analyse » depuis le modèle QGIS « Urumea A3 ». '
         'Carte avec les couches visibles, emprise métrique [582334,4794075,585295,4797333]. '
         'Remplace le texte kpi-value par « ' + str(final) + ' / ' + str(total) + ' » et valid-values par le compte valide/manquant réellement lu dans l’histogramme. '
         'Ajoute les DEUX graphiques redessinés avec D3 (pas leurs premières versions Python) : progression à x=270, y=105, width=138 mm ; histogramme à x=270, y=197, width=138 mm. '
         'La page est A3 paysage et contient les sources, la légende et le logo. Après cadrage de la carte, ajoute avec edit_layout une barre d’échelle liée à study-map à x=16,y=215,width=60,height=10 et une flèche nord à x=238,y=46,width=12,height=12. Ouvre le vrai composeur avec open_layout.'),
        ('export', 'Exporte réellement, avec le moteur FilterMate, les couches filtrées « Bâtiments pente », « Routes », « Ponts lignes », « Ponts polygones », ainsi que « Urumea », « Couloir Urumea 500 m », « URA T100 » dans un seul GeoPackage urumea_resultats. '
         'Exporte aussi les rasters « MNT GeoEuskadi 5 m » et « Pente (%) » dans des GeoTIFF. Exporte la mise en page « Urumea — analyse » en PDF, 200 dpi. '
         'Liste uniquement les fichiers effectivement écrits.'),
        ('portable', 'Prépare la dernière sauvegarde du projet avec ses données : retire seulement la couche brute « URA officiel » qui lit encore le ZIP distant, '
         'puisque la sélection locale « URA T100 » reste dans le projet. Conserve les couches OSM sources complètes, les copies métriques avec leurs filtres, '
         'les rasters et la mise en page avec ses SVG D3 intégrés. Ne supprime aucun fichier. Nous allons utiliser le bouton natif Enregistrer le projet et les couches. '
         'Ne prétends pas qu’un QGZ seul embarque des fichiers externes.'),
    ]


def finish():
    presentation('final')
    iface.actionSaveProject().trigger()
    QgsProject.instance().setDirty(False)
    REC.event('mark', name='phase-complete:' + PHASE)
    Path(OUT, 'phase.json').write_text(json.dumps({'phase': PHASE, 'project': str(SESSION),
                                                 'status': 'complete'}, indent=2))


def close_composer():
    for designer in iface.openLayoutDesigners():
        designer.window().close()


def open_pdf():
    from PyQt6.QtPdf import QPdfDocument
    from PyQt6.QtPdfWidgets import QPdfView
    from qgis.PyQt.QtWidgets import QVBoxLayout, QLabel
    root = Path(QgsApplication.qgisSettingsDirPath()) / 'FilterMate/exports'
    paths = sorted(root.rglob('*.pdf'), key=lambda path: path.stat().st_mtime)
    if not paths:
        raise RuntimeError('No actual PDF was exported')
    window = QDialog(iface.mainWindow())
    window.setWindowTitle('PDF exporté — ' + paths[-1].name)
    window.setGeometry(315, 145, 1115, 800)
    box = QVBoxLayout(window)
    box.addWidget(QLabel('PDF exporté : ' + paths[-1].name))
    document = QPdfDocument(window)
    document.load(str(paths[-1]))
    view = QPdfView(window)
    view.setDocument(document)
    view.setZoomMode(QPdfView.ZoomMode.FitInView)
    box.addWidget(view)
    window.show()
    NATIVE['refs'].extend((window, document, view))
    REC.event('mark', name='pdf-opened')


def close_pdf():
    for window in QApplication.topLevelWidgets():
        if window.windowTitle().startswith('PDF exporté —'):
            window.close()


STEPS = [(1000, setup_visible), (3000, open_plugin), (6000, size_dock), (1000, wait_idle()),
         (600, configure_agent), (400, agent_open), (600, align_dock), (800, wait_idle()),
         (500, rec_start), (0, cam('full', dur=0)), hold(4000), still('empty' if PHASE == 'acquire' else 'resume')]
if PHASE != 'acquire':
    # The file-only Processing destination is session state. On a new QGIS
    # process it must be chosen through the real native save controller again.
    STEPS += [(0, native_save), hold(3500), (500, saved), hold(1500)]
if PHASE == 'acquire':
    STEPS += ask('sources', ACQUIRE)
elif PHASE == 'analysis':
    for stage, request in ANALYSIS:
        STEPS += ask(stage, request)
        if stage in ('corridor', 't100', 'reseau'):
            STEPS += [(0, show_section('filtering')), hold(4500), still('filtering-' + stage),
                      (0, agent_open), hold(1000)]
elif PHASE == 'composer':
    for stage, request in composer_requests():
        STEPS += ask(stage, request)
        if stage == 'composer':
            STEPS += [hold(5000), still('composer-native'), (0, close_composer)]
        if stage == 'export':
            STEPS += [(0, show_section('exporting')), hold(4500), still('exporting-native'),
                      (0, agent_open), (0, open_pdf), hold(6500), still('pdf-native'), (0, close_pdf)]
elif PHASE == 'finish_layout':
    STEPS += ask('finition', 'Dans la mise en page « Urumea — analyse », supprime la barre d’échelle du modèle (ref scale), puis ajoute avec edit_layout une nouvelle barre d’échelle liée à study-map à x=16,y=215,width=60,height=10. Elle doit être calculée sur la carte maintenant cadrée, en mètres. Ajoute aussi une flèche nord liée à study-map à x=238,y=46,width=12,height=12. Ne change pas les couches, les filtres, les graphiques ni les autres textes. Ouvre le composeur.')
    STEPS += [hold(4000), still('composer-final'), (0, close_composer)]
    STEPS += ask('pdf-final', 'Exporte à nouveau la mise en page « Urumea — analyse » en PDF à 200 dpi après la correction de la barre d’échelle et l’ajout du nord. Donne le fichier réellement écrit.')
STEPS += [(0, native_save), hold(3500), (500, saved), hold(5000), still('saved'), (0, finish),
          (0, stop_recording), (500, quit_when_idle)]
log('Urumea zero phase ' + PHASE + ', ' + str(len(STEPS)) + ' steps')
