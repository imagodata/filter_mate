"""Build the small, attributed website demo with QGIS Python (no plugin needed).

Usage: python-qgis.bat scripts/build_site_demo.py INPUT.gpkg OUTPUT_DIRECTORY
The source is opened read-only. Existing outputs are never overwritten.
"""
import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from qgis.core import (
    QgsApplication, QgsCoordinateReferenceSystem, QgsFeature, QgsFeatureRequest,
    Qgis, QgsProject, QgsRectangle, QgsReferencedRectangle, QgsSingleSymbolRenderer, QgsSymbol,
    QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes,
)


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'filtermate-toutens.zip'
    if archive.exists():
        raise FileExistsError(archive)
    project = QgsProject()
    project.setCrs(QgsCoordinateReferenceSystem('EPSG:2154'))
    project.setFilePathStorage(Qgis.FilePathType.Relative)
    commune = QgsVectorLayer(f'{source}|layername=commune', 'commune', 'ogr')
    if not commune.isValid() or not commune.setSubsetString('"nom_officiel" = \'Toutens\''):
        raise RuntimeError('Cannot read Toutens from the source GeoPackage')
    areas = list(commune.getFeatures())
    if len(areas) != 1:
        raise ValueError(f'Expected one Toutens boundary, found {len(areas)}')
    area = areas[0].geometry()
    extent = QgsRectangle(area.boundingBox())
    extent.grow(300)
    counts = {}
    features = {}
    palette = {'commune': '#6b7280', 'troncon_de_route': '#424b55', 'batiment': '#d64545', 'erp': '#e0ad00'}
    with tempfile.TemporaryDirectory(prefix='filtermate-demo-') as temp:
        root = Path(temp)
        gpkg = root / 'toutens.gpkg'
        for name in palette:
            raw = commune if name == 'commune' else QgsVectorLayer(f'{source}|layername={name}', name, 'ogr')
            if not raw.isValid():
                raise ValueError(f'Invalid input layer: {name}')
            if raw.crs().authid() != 'EPSG:2154':
                raise ValueError(f'Unexpected CRS for {name}: {raw.crs().authid()}')
            picked = list(raw.getFeatures(QgsFeatureRequest().setFilterRect(extent)))
            # Keep complete geometries touching the commune and a 300 m margin.
            # This is a teaching extract, not the complete departmental dataset.
            fields = [field for field in raw.fields() if field.name() != 'fid']
            memory = QgsVectorLayer(f'{QgsWkbTypes.displayString(raw.wkbType())}?crs=EPSG:2154', name, 'memory')
            memory.dataProvider().addAttributes(fields)
            memory.updateFields()
            converted = []
            for feature in picked:
                item = QgsFeature(memory.fields())
                item.setGeometry(feature.geometry())
                item.setAttributes([feature[field.name()] for field in fields])
                converted.append(item)
            if not memory.dataProvider().addFeatures(converted)[0]:
                raise RuntimeError(f'Cannot populate {name}')
            memory.updateExtents()
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GPKG'
            options.layerName = name
            options.actionOnExistingFile = (QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
                                            if gpkg.exists() else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile)
            result = QgsVectorFileWriter.writeAsVectorFormatV3(memory, str(gpkg), project.transformContext(), options)
            if result[0] != QgsVectorFileWriter.WriterError.NoError:
                raise RuntimeError(str(result))
            layer = QgsVectorLayer(f'{gpkg}|layername={name}', name, 'ogr')
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            from qgis.PyQt.QtGui import QColor
            symbol.setColor(QColor(palette[name]))
            if name == 'commune':
                symbol.setOpacity(0.15)
            layer.setRenderer(QgsSingleSymbolRenderer(symbol))
            layer.setDisplayExpression('"nom_officiel"' if name == 'commune' else '"cleabs"')
            project.addMapLayer(layer)
            features[name] = list(layer.getFeatures())
            counts[name] = len(features[name])
        project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent, project.crs()))
        project.setFileName(str(root / 'filtermate-toutens.qgs'))
        if not project.write():
            raise RuntimeError('Could not write the demo project')
        scoped = {name: [f for f in items if f.geometry().intersects(area)] for name, items in features.items()}
        residential = [f for f in features['batiment'] if f['usage_1'] == 'Résidentiel']
        manifest = {
            'dataset': 'BD TOPO 3.5, Haute-Garonne, edition 2026-03-15',
            'source_file': source.name,
            'attribution': 'BD TOPO® © IGN, Licence Ouverte 2.0',
            'license': 'https://www.etalab.gouv.fr/licence-ouverte-open-licence/',
            'extent': 'Toutens bounding rectangle + 300 m; complete intersecting feature geometries',
            'crs': 'EPSG:2154',
            'layers': counts,
            'expected_after_commune_intersect': {name: len(items) for name, items in scoped.items()},
            'expected_residential_without_spatial_filter': len(residential),
            'verification': 'QGIS geometry.intersects and attribute evaluation, independently of FilterMate',
        }
        (root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        favorite = {
            'schema': 'filter_mate.favorites', 'schema_version': 3, 'version': '3.0',
            'min_compat_plugin_version': '4.7.0',
            'collection': {'name': 'FilterMate — Toutens', 'license': 'CC0-1.0'},
            'favorites': [{
                'name': 'Toutens — Résidentiel / Residential',
                'description': 'Attributaire uniquement / Attribute only. Select batiment, clear existing filters, then apply.',
                'expression': '\"usage_1\" = \'Résidentiel\'',
                'layer_name': 'batiment', 'layer_provider': 'ogr', 'layer_id': None,
                'tags': ['demo', 'toutens'],
                'spatial_config': {'source_layer_signature': 'ogr::batiment'},
            }],
        }
        (root / 'toutens.fmfav-pack.json').write_text(json.dumps(favorite, ensure_ascii=False, indent=2), encoding='utf-8')
        instructions = f'''FILTERMATE — TOUTENS / START HERE

FR — Décompressez toute l’archive dans un dossier, puis ouvrez filtermate-toutens.qgs dans QGIS.
Installez FilterMate via le gestionnaire d’extensions. Le projet utilise des chemins relatifs.

1. Premier filtre spatial : source commune, Single selection = Toutens ; cibles batiment,
   troncon_de_route et erp ; Intersect, sans tampon, puis Filter.
   Résultats attendus : {json.dumps(manifest['expected_after_commune_intersect'], ensure_ascii=False)}.
2. Favori attributaire : effacez les filtres (Unfilter), choisissez batiment comme source,
   puis importez toutens.fmfav-pack.json depuis le menu Favoris. Appliquez le favori
   Résidentiel. Résultat attendu : {len(residential)} bâtiments dans cet extrait.

EN — Extract the whole archive to one folder and open filtermate-toutens.qgs in QGIS.
Install FilterMate from the plugin manager. Project paths are relative.

1. Spatial filter: commune source, Single selection = Toutens; targets batiment,
   troncon_de_route and erp; Intersect, no buffer, then Filter.
   Expected results are listed in manifest.json (expected_after_commune_intersect).
2. Attribute favorite: clear filters (Unfilter), select batiment as source, import
   toutens.fmfav-pack.json from Favorites, and apply Residential. Expect {len(residential)} buildings.

EXTRAIT PÉDAGOGIQUE / TEACHING EXTRACT
Rectangle englobant Toutens + 300 m, géométries entières. Les effectifs diffèrent des
vidéos départementales. / Whole geometries from Toutens extent + 300 m. Counts differ
from the department-wide videos. No plugin settings or macros are embedded.

DONNÉES / DATA: BD TOPO® 3.5 © IGN, Haute-Garonne, édition 2026-03-15.
Licence Ouverte 2.0 : https://www.etalab.gouv.fr/licence-ouverte-open-licence/
Source : https://geoservices.ign.fr/bdtopo
Instructions, style et favori / Instructions, styling and favorite: CC0-1.0.
'''
        (root / 'START-HERE.txt').write_text(instructions, encoding='utf-8')
        project.clear()
        # Close provider handles before packaging, particularly on Windows.
        layer = raw = memory = commune = None
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
            for file in sorted(root.iterdir()):
                if file.suffix not in ('.gpkg', '.qgs', '.json', '.txt'):
                    continue
                bundle.write(file, arcname=f'filtermate-toutens/{file.name}')
        print(json.dumps(manifest, ensure_ascii=False))
        print(f'Archive: {archive.stat().st_size} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    app = QgsApplication([], False)
    app.initQgis()
    build(args.source, args.output)
    app.exitQgis()
