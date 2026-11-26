# -*- coding: utf-8 -*-
"""Contrôle en lecture seule du poste Windows / QGIS 4.

Dans l'éditeur de la console Python QGIS, ouvrir puis exécuter ce fichier.
Le JSON imprimé ne contient ni clé, ni URI de connexion. Ne charge aucun plugin,
source réseau ou modèle. La présence d'un algorithme ne valide pas une prise.
"""
import json
import platform


def collect():
    from qgis.core import Qgis, QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer
    from qgis.PyQt.QtCore import QT_VERSION_STR
    from qgis.utils import plugins, pluginMetadata

    project = QgsProject.instance()
    loaded = 'filter_mate' in plugins
    report = {'schema': 1, 'platform': platform.system(), 'python': platform.python_version(),
              'qgis': Qgis.QGIS_VERSION, 'qt': QT_VERSION_STR,
              'filtermate_loaded': loaded, 'filtermate_version': pluginMetadata('filter_mate', 'version') if loaded else None,
              'project_saved': bool(project.fileName()), 'project_crs': project.crs().authid(), 'layers': []}
    for layer in project.mapLayers().values():
        item = {'name': layer.name(), 'valid': layer.isValid(), 'provider': layer.providerType(),
                'crs': layer.crs().authid(), 'type': type(layer).__name__}
        if isinstance(layer, QgsVectorLayer):
            item.update(features=layer.featureCount(), geometry=int(layer.geometryType()),
                        subset=layer.subsetString(), fields=[f.name() for f in layer.fields()])
        elif isinstance(layer, QgsRasterLayer):
            item.update(width=layer.width(), height=layer.height(), bands=layer.bandCount(),
                        pixel_in_crs_units=[layer.rasterUnitsPerPixelX(), layer.rasterUnitsPerPixelY()])
        report['layers'].append(item)
    registry = QgsApplication.processingRegistry()
    report['algorithms'] = {key: registry.algorithmById(key) is not None for key in (
        'native:serviceareafromlayer', 'native:serviceareafrompoint',
        'native:zonalstatisticsfb', 'qgis:zonalstatisticsfb', 'gdal:slope')}
    report['qneat_algorithms'] = [a.id() for a in registry.algorithms() if 'qneat' in a.id().lower()]
    if loaded:
        from filter_mate.adapters.agent.settings import load_settings
        settings = load_settings()
        report['agent'] = {key: getattr(settings, key, None) for key in (
            'preset', 'model', 'consent', 'autonomy', 'enabled_sources', 'local_filtering_only', 'tool_families')}
    report['checks'] = {'windows': platform.system() == 'Windows', 'qgis4': Qgis.QGIS_VERSION_INT >= 40000,
                        'filtermate_loaded': loaded, 'has_layers': bool(report['layers']),
                        'all_current_layers_valid': all(x['valid'] for x in report['layers'])}
    report['environment_ready'] = all(report['checks'].values())
    report['scenario_validated'] = False
    return report


if __name__ in ('__main__', '__console__'):
    print(json.dumps(collect(), ensure_ascii=False, indent=2))
