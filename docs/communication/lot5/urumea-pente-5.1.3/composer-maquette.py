"""Create a vector design mockup without inventing geographical or statistical results."""
import base64
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
spec = json.loads((ROOT / 'composer-plan.json').read_text())
ET.register_namespace('', 'http://www.w3.org/2000/svg')
NS = '{http://www.w3.org/2000/svg}'
svg = ET.Element(NS + 'svg', {'width': '1260', 'height': '891', 'viewBox': '0 0 1260 891'})
palette = spec['palette']


def element(kind, attrs):
    return ET.SubElement(svg, NS + kind, {key: str(value) for key, value in attrs.items()})


def text(x, y, value, size=16, color=None, bold=False, anchor='start'):
    node = element('text', {'x': x, 'y': y, 'font-family': 'DejaVu Sans, sans-serif', 'font-size': size,
                           'fill': color or palette['ink'], 'font-weight': '700' if bold else '400', 'text-anchor': anchor})
    node.text = value


def rect(x, y, width, height, fill, stroke='none', dash=None):
    attrs = {'x': x, 'y': y, 'width': width, 'height': height, 'rx': 8, 'fill': fill, 'stroke': stroke}
    if dash: attrs['stroke-dasharray'] = dash
    element('rect', attrs)


rect(0, 0, 1260, 891, palette['paper'])
logo = ROOT.parents[3] / 'website/logo.png'
if logo.is_file():
    element('image', {'x': 36, 'y': 32, 'width': 62, 'height': 62,
                     'href': 'data:image/png;base64,' + base64.b64encode(logo.read_bytes()).decode()})
text(116, 59, 'Urumea — Saint-Sébastien', 29, bold=True)
text(116, 87, 'Synthèse cartographique · FilterMate', 16)
text(1224, 48, 'MAQUETTE PRÉPARATOIRE', 13, color=palette['river'], bold=True, anchor='end')
text(1224, 74, 'Aucune valeur de résultat représentée', 12, anchor='end')

for name in ('map', 'kpi', 'progression', 'slope_histogram'):
    x, y, width, height = [value * 3 for value in spec['boxes_mm'][name]]
    rect(x, y, width, height, palette['panel'], '#dbe4e8')

text(405, 378, 'CARTE ISSUE DE QGIS', 28, color=palette['selected'], bold=True, anchor='middle')
text(405, 414, 'MNT · couloir de 500 m · zonage URA', 18, anchor='middle')
text(405, 447, 'Bâtiments retenus, routes et objets ponts', 17, anchor='middle')
text(405, 491, 'Emplacement réservé à la carte réelle', 14, color='#687f8b', anchor='middle')
text(64, 716, 'Légende · échelle · nord', 15)
text(1210, 155, 'BÂTIMENTS RETENUS', 13, bold=True, anchor='end')
text(834, 203, 'N final', 37, color=palette['selected'], bold=True)
text(1050, 200, '/ N secteur', 17)

text(834, 286, 'Effet des filtres', 19, bold=True)
for i, label in enumerate(['Acquis dans l’emprise', 'Couloir de 500 m', 'Avec le zonage URA']):
    y = 323 + i * 54
    text(834, y, label, 13)
    rect(834, y + 10, 336, 16, '#ffffff', '#a4bac5', '5 4')
    text(1188, y + 23, 'N', 14, color=palette['selected'], bold=True)
text(834, 480, 'Comptes uniques observés après chaque filtre', 12, color='#687f8b')

text(834, 561, 'Pentes du terrain (%)', 19, bold=True)
text(834, 589, 'Sous les bâtiments retenus · à calculer sur MNT', 12)
element('path', {'d': 'M854 615 V714 H1198', 'fill': 'none', 'stroke': '#a4bac5', 'stroke-width': 2})
for i in range(8): rect(869 + i * 39, 648, 26, 66, '#ffffff', '#a4bac5', '4 4')
text(1028, 742, 'Valeurs renseignées et manquantes à préciser', 12, color='#687f8b', anchor='middle')

text(36, 806, 'Sources, millésimes, projection et date à renseigner sur la composition réelle.', 14)
text(36, 836, 'Deux graphiques D3.js intégrés en SVG · PDF de synthèse · projet QGIS avec ses données', 14)
text(1224, 856, 'Conception de page · aucun zonage ou résultat fictif présenté comme observé', 12,
     color='#687f8b', anchor='end')
ET.ElementTree(svg).write(ROOT / 'composer-maquette.svg', encoding='utf-8', xml_declaration=True)
print('composer-maquette.svg written: layout mockup only')
