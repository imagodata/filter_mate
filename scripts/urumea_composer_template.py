"""Generate the reusable native QGIS page design, without geographical results.

The actual agent creates a layout from this QPT, fills its KPI, adds real D3
charts and exports PDF. The map and numbers are never painted into this template.
"""
import base64
from pathlib import Path
from qgis.core import (QgsApplication, QgsProject, QgsPrintLayout, QgsLayoutItemPage,
                       QgsLayoutItemLabel, QgsLayoutItemMap, QgsLayoutItemPicture,
                       QgsLayoutItemScaleBar, QgsLayoutPoint, QgsLayoutSize,
                       QgsCoordinateReferenceSystem, QgsReadWriteContext)
from qgis.PyQt.QtGui import QColor, QFont

app = QgsApplication([b'urumea-template'], True)
app.initQgis()
project = QgsProject.instance()
project.setCrs(QgsCoordinateReferenceSystem('EPSG:25830'))
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.pageCollection().page(0).setPageSize('A3', QgsLayoutItemPage.Orientation.Landscape)


def label(key, text, box, size=10, bold=False, color='#183747', background=None):
    item = QgsLayoutItemLabel(layout)
    item.setId(key)
    item.setText(text)
    item.setFont(QFont('DejaVu Sans', size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    item.setFontColor(QColor(color))
    if background:
        item.setBackgroundEnabled(True)
        item.setBackgroundColor(QColor(background))
    layout.addLayoutItem(item)
    item.attemptMove(QgsLayoutPoint(*box[:2]))
    item.attemptResize(QgsLayoutSize(*box[2:]))
    return item


label('title', 'Urumea — Saint-Sébastien', (37, 10, 280, 15), 23, True)
label('subtitle', 'Du projet vide à une synthèse partageable · FilterMate', (37, 26, 280, 9), 10)
label('brand', 'imagodata\nFilterMate · QGIS', (344, 12, 64, 19), 11, True, '#1485a9')
logo = QgsLayoutItemPicture(layout)
logo.setPicturePath('base64:' + base64.b64encode(Path('/w/release/filter_mate/icons/logo.png').read_bytes()).decode())
layout.addLayoutItem(logo)
logo.attemptMove(QgsLayoutPoint(12, 11))
logo.attemptResize(QgsLayoutSize(20, 20))

map_item = QgsLayoutItemMap(layout)
map_item.setId('study-map')
map_item.setCrs(project.crs())
map_item.setBackgroundColor(QColor('#f6f7f4'))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeColor(QColor('#d8e2e5'))
layout.addLayoutItem(map_item)
map_item.attemptMove(QgsLayoutPoint(12, 42))
map_item.attemptResize(QgsLayoutSize(246, 210))

label('kpi-heading', 'BÂTIMENTS RETENUS', (270, 42, 138, 10), 10, True, '#1485a9')
label('kpi-value', 'À renseigner après calcul', (270, 52, 138, 15), 20, True)
label('kpi-caption', 'Couloir 500 m ET zonage URA T100', (270, 69, 138, 9), 9)
label('progression-heading', 'Effet des filtres', (270, 85, 138, 10), 13, True)
label('progression-caption', 'Comptes uniques · populations emboîtées', (270, 95, 138, 8), 8)
label('slope-heading', 'Pentes du terrain (%)', (270, 176, 138, 10), 13, True)
label('slope-caption', 'Moyenne sous les emprises retenues', (270, 187, 138, 8), 8)
label('valid-values', 'Valeurs renseignées / manquantes : à vérifier', (270, 244, 138, 9), 8)

# A compact static legend names the actual styles used in the take. Its swatches
# are vector characters; the map content itself is resolved by create_layout.
label('legend-background', '', (16, 229, 235, 18), 8, background='#ffffff')
label('legend-buildings', '● Bâtiments retenus', (18, 230, 68, 7), 8, color='#e75d35')
label('legend-river', '━ Urumea', (87, 230, 38, 7), 8, color='#1687bc')
label('legend-roads', '━ Voies', (126, 230, 36, 7), 8, color='#7e878c')
label('legend-bridges', '━ Objets ponts', (166, 230, 72, 7), 8, color='#cc8d40')
label('legend-ura', '■ Zonage URA T100', (18, 238, 100, 7), 8, color='#2694b4')
label('legend-buffer', '□ Couloir d’étude 500 m', (119, 238, 122, 7), 8, color='#2185bd')
# Scale and north are added through edit_layout after the real map is framed.
# Initializing a scale bar against an empty template map creates invalid units.

label('sources', 'Sources : OpenStreetMap © contributeurs (ODbL) · MNT 5 m/2017 : Eusko Jaurlaritza / Gobierno Vasco, GeoEuskadi (CC BY 3.0)\n'
      'URA : zonage T100, fichier CT_0501GInundabilidad_2025 · ETRS89 / UTM 30N (EPSG:25830)',
      (12, 261, 396, 14), 8)
label('method', 'Analyse exploratoire : la pente décrit le terrain ; elle ne calcule pas la crue. '
      'L’intersection d’une emprise avec le zonage ne constitue pas un diagnostic du bâtiment.',
      (12, 278, 396, 12), 8)

destination = Path('/w/profiles/profiles/urumea-zero/composer_templates/Urumea A3.qpt')
destination.parent.mkdir(parents=True, exist_ok=True)
assert layout.saveAsTemplate(str(destination), QgsReadWriteContext())
print('Native template written without a map or result values:', destination)
