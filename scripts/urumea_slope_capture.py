"""Real QGIS take: slope in percent, 500 m river corridor, replay and export.

Wraps the proven 5.1.3 capture driver. Source data and the Copernicus raster are
prepared before recording; all analysis/filter/favorite/export actions go
through the real agent. Layout assistance only restores framing and map style.
"""
from pathlib import Path
exec(compile(Path('/w/scripts/urumea_linkedin_capture.py').read_text(),
             '/w/scripts/urumea_linkedin_capture.py', 'exec'), globals())

BASE_SETUP = setup_visible
BASE_CHECKPOINT = checkpoint
BASE_CONFIGURE = configure_agent

REQUESTS = [
    ('pente', 'Le modèle de surface « Copernicus 30 m » est déjà chargé. Calcule sa pente en POURCENTAGE avec gdal:slope : AS_PERCENT=true, COMPUTE_EDGES=true, SCALE=1, ZEVENBERGEN=false. Nomme le raster « Pente (%) », donne-lui une légende de couleurs lisible et affiche-le sous les vecteurs. Ne change pas le cadrage.'),
    ('moyenne', 'Calcule uniquement la moyenne du raster « Pente (%) » par emprise de « Bâtiments », avec native:zonalstatisticsfb, préfixe pente_ et statistique moyenne. Nomme la sortie « Bâtiments pente », colore-la par pente_mean et masque la couche originale « Bâtiments ». Aucun filtre pour le moment.'),
    ('seuil', 'Dans « Bâtiments pente », garde uniquement pente_mean < 10. La valeur est un pourcentage, pas des degrés. Ne fais aucun filtre spatial pour le moment, ne change pas le cadrage.'),
    ('filtre', 'Ajoute un second critère aux bâtiments déjà retenus : intersection avec un tampon de 500 mètres autour de « Urumea », avec un ET pour conserver pente_mean < 10. Crée aussi un tampon dissous de 500 m nommé « Couloir Urumea 500 m » pour le visualiser, en bleu clair transparent sous les bâtiments. Les distances sont métriques en EPSG:32630. Ne filtre pas encore les routes ni les ponts et ne change pas le cadrage.'),
    ('reseau', 'Garde « Routes », « Ponts lignes » et « Ponts polygones » à moins de 300 mètres des bâtiments actuellement retenus dans « Bâtiments pente ». Conserve tous les filtres actifs et le cadrage. Les objets ponts OSM ne sont pas un décompte de ponts physiques distincts.'),
    ('favori', 'Enregistre tous les filtres actifs du projet comme favori « Urumea — pente et rivière ». Réponds seulement « Favori enregistré » une fois le succès confirmé.'),
    ('reset', 'Efface les filtres des couches du projet sans supprimer les couches ni le favori. Nous comparons la carte complète avant le rejeu. Ne change pas le cadrage.'),
    ('rejeu', 'Réapplique seulement le favori « Urumea — pente et rivière ». Ne lance aucune autre opération de filtrage. Réponds seulement « Favori rejoué » après confirmation du succès.'),
    ('export', 'Exporte « Bâtiments pente », « Routes », « Ponts lignes », « Ponts polygones », « Urumea » et « Couloir Urumea 500 m », avec les filtres actifs, dans un seul GeoPackage « urumea_pente_resultats ». Exporte aussi les rasters « Pente (%) » et « Copernicus 30 m » dans des GeoTIFF séparés, avec les styles disponibles. Liste seulement les fichiers réellement écrits ; aucun projet embarqué n’est annoncé.'),
]


def setup_visible():
    BASE_SETUP()
    raster = QgsRasterLayer('/w/data/copernicus_30m.tif', 'Copernicus 30 m', 'gdal')
    if not raster.isValid():
        raise RuntimeError('Prepared Copernicus raster is invalid')
    raster.loadNamedStyle('/w/data/copernicus_30m.qml')
    project = QgsProject.instance()
    project.addMapLayer(raster, False)
    project.layerTreeRoot().addLayer(raster)
    restore_view()


def configure_agent():
    BASE_CONFIGURE()
    from qgis.PyQt.QtWidgets import QFileDialog
    target = Path(OUT) / 'session' / 'urumea-pente.qgz'
    target.parent.mkdir(parents=True, exist_ok=True)
    # Choose the recording project's dedicated destination through the normal
    # save controller. Subsequent Data cards reuse this same local destination.
    QFileDialog.getSaveFileName = staticmethod(lambda *args, **kwargs: (str(target), 'QGIS project (*.qgz)'))
    if not agent_chat()._data.save():
        raise RuntimeError('Project storage could not be chosen before GDAL Processing')
    log('Prepared recording project storage: ' + str(target))


def presentation(stage):
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    # Keep both raster layers in order without removing a layer's last tree node.
    # The project/tree bridge removes a layer if its only node is removed first.
    for name in ('Pente (%)', 'Copernicus 30 m'):
        for layer in project.mapLayersByName(name):
            node = root.findLayer(layer.id())
            root.addChildNode(node.clone())
            node.parent().removeChildNode(node)
            if name == 'Pente (%)':
                layer.renderer().setOpacity(0.6)
                root.findLayer(layer.id()).setItemVisibilityChecked(stage == 'pente')
    # A quiet relief background makes the selected buildings readable after
    # the slope raster itself has been shown. This only changes presentation.
    from qgis.core import QgsGradientColorRamp
    from qgis.PyQt.QtGui import QColor
    for layer in project.mapLayersByName('Bâtiments pente'):
        renderer = layer.renderer()
        if hasattr(renderer, 'updateColorRamp'):
            renderer.updateColorRamp(QgsGradientColorRamp(QColor('#303b81'), QColor('#e85535')))
            layer.triggerRepaint()
    for layer in project.mapLayers().values():
        if layer.name() == 'Couloir Urumea 500 m':
            layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({
                'color': '33,133,189,36', 'outline_color': '33,133,189,150',
                'outline_width': '0.4'})))
            node = root.findLayer(layer.id())
            clone = node.clone()
            # Keep the corridor below the vectors and above the background rasters.
            index = next((i for i, child in enumerate(root.children())
                          if hasattr(child, 'layer') and isinstance(child.layer(), QgsRasterLayer)), len(root.children()))
            root.insertChildNode(index, clone)
            node.parent().removeChildNode(node)
            layer.triggerRepaint()


def checkpoint(stage):
    def check():
        presentation(stage)
        BASE_CHECKPOINT(stage)()
        project = QgsProject.instance()
        buildings = next((layer for layer in project.mapLayers().values()
                          if layer.name() == 'Bâtiments pente'), None)
        if stage in ('moyenne', 'seuil', 'filtre', 'reseau') and buildings is None:
            raise RuntimeError('Missing zonal slope layer')
        if stage == 'pente' and not any(isinstance(layer, QgsRasterLayer) and layer.name() == 'Pente (%)'
                                        for layer in project.mapLayers().values()):
            raise RuntimeError('Missing slope raster')
        if stage == 'moyenne' and (exact_count(buildings) != 3073 or 'pente_mean' not in buildings.fields().names()):
            raise RuntimeError('Invalid zonal mean result')
        if stage == 'seuil' and exact_count(buildings) != 1463:
            raise RuntimeError('Slope threshold differs from independently prepared data')
        if stage == 'filtre':
            if not 410 < exact_count(buildings) < 1463:
                raise RuntimeError('Unexpected 500 m corridor result')
            if not any(layer.name() == 'Couloir Urumea 500 m' for layer in project.mapLayers().values()):
                raise RuntimeError('Missing visible corridor geometry')
        if stage == 'reseau':
            filters = current_filters()
            if set(filters) != {'Bâtiments pente', 'Routes', 'Ponts lignes', 'Ponts polygones'}:
                raise RuntimeError('Four filtered layers expected')
            REFERENCE_FILTERS.clear()
            REFERENCE_FILTERS.update(filters)
    return check


def focus_filtered_buildings():
    for layer in QgsProject.instance().mapLayers().values():
        if layer.name() == 'Bâtiments pente':
            iface.setActiveLayer(layer)
            return


if os.environ.get('FM_ANALYSIS_ONLY') == '1':
    REQUESTS = [(stage, text) for stage, text in REQUESTS if stage not in ('favori', 'reset', 'rejeu')]

STEPS = [(1000, setup_visible), (3000, open_plugin), (8000, size_dock), (1500, wait_idle()),
         (600, configure_agent), (400, agent_open), (800, align_dock), (800, wait_idle()),
         (500, rec_start), title('FilterMate 5.1.3 · Urumea et pente'),
         (0, cam('full', dur=0)), hold(4500), still('baseline')]
for stage, request in REQUESTS:
    STEPS += ask(stage, request)
STEPS += [(0, collect_deliverables), hold(1500), (0, stop_recording), (500, quit_when_idle)]
