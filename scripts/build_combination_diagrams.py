"""Build the source/result diagrams of the French and English combination recipes.

Run from any directory with Python's standard library. These SVG illustrations
explain the filters; they are not QGIS captures or measured geographic data.
"""
from html import escape
from math import hypot, sin
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / 'website/img/combinations'
PAPER = '#f3f4ef'
INK = '#16232b'
GREEN = '#589632'
YELLOW = '#ffd83d'
RED = '#d64545'
ENGLISH = {
    'FILTERMATE 5  /  SCHÉMA DE PRINCIPE': 'FILTERMATE 5  /  SCHEMATIC',
    'SOURCE → GÉOMÉTRIE → CIBLE': 'SOURCE → GEOMETRY → TARGET',
    'La végétation sur l’orthophoto': 'Vegetation on an RGB orthophoto',
    'SOURCE · ORTHOPHOTO IRC': 'SOURCE · COLOUR INFRARED ORTHOPHOTO',
    'CIBLE · ORTHOPHOTO RVB': 'TARGET · RGB ORTHOPHOTO',
    'NDVI > 0,3  ·  Intersect  ·  sans tampon': 'NDVI > 0.3  ·  Intersect  ·  no buffer',
    'À droite : les couleurs RVB conservées ; le damier représente le NoData.':
        'Right: the retained RGB colours; the checkerboard represents NoData.',
    'Les points sous les toits sélectionnés': 'Points beneath the selected roofs',
    'SOURCE · ORTHOPHOTO RVB': 'SOURCE · RGB ORTHOPHOTO',
    'CIBLE · NUAGE LIDAR': 'TARGET · LIDAR POINT CLOUD',
    'Pipette « objet cliqué »  ·  Intersect  ·  sans tampon':
        'Pipette: clicked object  ·  Intersect  ·  no buffer',
    'Contour jaune : objets sélectionnés ; points colorés : retours LiDAR conservés en plan.':
        'Yellow outlines: selected objects; coloured dots: retained LiDAR returns in plan view.',
    'Le MNT au droit des points sol': 'The DTM beneath ground points',
    'SOURCE · LIDAR CLASSÉ': 'SOURCE · CLASSIFIED LIDAR',
    'CIBLE · MODÈLE DE TERRAIN': 'TARGET · TERRAIN MODEL',
    'Classe 2 « Ground »  ·  Intersect  ·  sans tampon': 'Class 2: Ground  ·  Intersect  ·  no buffer',
    'Les altitudes du MNT sont conservées sous l’empreinte du sol ; ailleurs : NoData.':
        'DTM elevations are retained within the ground footprint; elsewhere: NoData.',
    'La végétation près des lignes électriques': 'Vegetation near power lines',
    'SOURCE · POINTS DE CÂBLE': 'SOURCE · WIRE POINTS',
    'CIBLE · POINTS DE VÉGÉTATION': 'TARGET · VEGETATION POINTS',
    'Classes 13 / 14 → classe 5  ·  Intersect  ·  tampon 10 m':
        'Classes 13 / 14 → class 5  ·  Intersect  ·  10 m buffer',
    'Vue en plan : le corridor retient les arbres proches de l’empreinte des câbles.':
        'Plan view: the corridor retains vegetation near the footprint of the wires.',
}


def rect(x, y, w, h, color, extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" {extra}/>'


def dot(x, y, color, radius=3):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color}"/>'


def label(x, y, text, size=22, color=PAPER, extra=''):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'{extra}>{escape(text)}</text>')


def write_diagram(name, title, source, target, left, right, rule, legend, language):
    english = language == 'en'
    if english:
        name += '-en'
        title, source, target, rule, legend = (ENGLISH[value] for value in (title, source, target, rule, legend))
    kicker = 'FILTERMATE 5  /  SCHÉMA DE PRINCIPE'
    footer = 'SOURCE → GÉOMÉTRIE → CIBLE'
    if english:
        kicker, footer = ENGLISH[kicker], ENGLISH[footer]
    definitions = [
        '<defs><pattern id="empty" width="16" height="16" patternUnits="userSpaceOnUse">',
        rect(0, 0, 16, 16, '#e7e9e1'), rect(0, 0, 8, 8, '#cfd3c8'),
        rect(8, 8, 8, 8, '#cfd3c8'), '</pattern>',
        '<clipPath id="map"><rect width="528" height="320"/></clipPath></defs>',
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" '
        'width="1280" height="720" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(source + ' → ' + target + '. ' + rule + '. ' + legend)}</desc>',
        *definitions,
        '<g font-family="Barlow, Segoe UI, sans-serif">',
        rect(0, 0, 1280, 720, INK),
        label(48, 48, kicker, 18, '#a9b6bd', 'letter-spacing="2"'),
        label(48, 100, title, 32, PAPER, 'font-weight="600"'),
        label(48, 153, source, 21), label(704, 153, target, 21),
        rect(48, 176, 528, 320, PAPER), rect(704, 176, 528, 320, 'url(#empty)'),
        '<g transform="translate(48 176)" clip-path="url(#map)">', *left, '</g>',
        '<g transform="translate(704 176)" clip-path="url(#map)">', *right, '</g>',
        '<path d="M605 336h68m-18-18 18 18-18 18" fill="none" '
        f'stroke="{YELLOW}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
        label(48, 548, rule, 24, YELLOW, 'font-weight="600"'),
        label(48, 588, legend, 20, '#a9b6bd'),
        label(48, 664, footer, 18, PAPER, 'letter-spacing="2"'),
        '</g></svg>\n',
    ]
    (OUT / f'{name}.svg').write_text('\n'.join(parts), encoding='utf-8')
    # Text-free cover: the HTML band supplies its title and credit. Leave room
    # below the maps so long headings remain readable on a narrow screen.
    cover = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 640" width="1280" height="640">',
        f'<title>{escape(title + (" — schematic" if english else " — schéma"))}</title>', *definitions,
        rect(0, 0, 1280, 640, INK),
        '<g transform="translate(48 80)" clip-path="url(#map)">', *left, '</g>',
        '<g transform="translate(704 80)" clip-path="url(#map)">', *right, '</g>',
        '<path d="M605 240h68m-18-18 18 18-18 18" fill="none" '
        f'stroke="{YELLOW}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
        '</svg>\n',
    ]
    (OUT / f'{name}-cover.svg').write_text('\n'.join(cover), encoding='utf-8')


def diagram(name, title, source, target, left, right, rule, legend):
    for language in ('fr', 'en'):
        write_diagram(name, title, source, target, left, right, rule, legend, language)


def vegetation(x, y):
    return ((x - 110) / 83) ** 2 + ((y - 110) / 75) ** 2 < 1 or (
        ((x - 392) / 110) ** 2 + ((y - 222) / 66) ** 2 < 1)


def ndvi():
    left, right = [], []
    for row in range(20):
        for col in range(33):
            x, y = col * 16, row * 16
            kept = vegetation(x + 8, y + 8)
            left.append(rect(x, y, 15, 15, '#b34d63' if kept else '#93a8a1'))
            if kept:
                right.append(rect(x, y, 15, 15, '#6a9946' if (row + col) % 3 else '#3f7a22'))
    diagram('ndvi', 'La végétation sur l’orthophoto', 'SOURCE · ORTHOPHOTO IRC',
            'CIBLE · ORTHOPHOTO RVB', left, right,
            'NDVI > 0,3  ·  Intersect  ·  sans tampon',
            'À droite : les couleurs RVB conservées ; le damier représente le NoData.')


ROOFS = [(65, 50, 115, 68), (286, 166, 144, 85)]


def roofs():
    left, right = [], []
    left.append('<path d="M0 270 528 40" stroke="#cfd3c8" stroke-width="38"/>')
    for x, y, w, h in ROOFS:
        left.extend([rect(x, y, w, h, RED, f'stroke="{YELLOW}" stroke-width="4"'),
                     f'<path d="M{x} {y + h / 2}h{w}" stroke="#973b3b" stroke-width="3"/>'])
        for row in range(6):
            for col in range(12):
                right.append(dot(x + 5 + col * (w - 10) / 11,
                                 y + 5 + row * (h - 10) / 5, RED if row % 2 else '#e89455'))
        right.append(rect(x, y, w, h, 'none', f'stroke="{YELLOW}" stroke-width="2"'))
    left.extend([dot(446, 70, GREEN, 31), dot(227, 248, GREEN, 38),
                 rect(359, 40, 60, 38, '#a9b6bd')])
    diagram('roofs', 'Les points sous les toits sélectionnés', 'SOURCE · ORTHOPHOTO RVB',
            'CIBLE · NUAGE LIDAR', left, right,
            'Pipette « objet cliqué »  ·  Intersect  ·  sans tampon',
            'Contour jaune : objets sélectionnés ; points colorés : retours LiDAR conservés en plan.')


def ground():
    left, right = [], []
    for row in range(20):
        for col in range(33):
            x, y = col * 16 + 8, row * 16 + 8
            roof = 175 < x < 320 and 90 < y < 215
            canopy = ((x - 420) / 60) ** 2 + ((y - 82) / 58) ** 2 < 1
            left.append(dot(x, y, RED if roof else GREEN if canopy else '#697b63', 3.5))
            if not roof and not canopy:
                color = ['#b7c38a', '#c9c894', '#d9ceab'][min(2, col // 11)]
                right.append(rect(x - 8, y - 8, 15, 15, color))
    left.append(rect(175, 90, 145, 125, 'none', f'stroke="{RED}" stroke-width="2"'))
    diagram('ground', 'Le MNT au droit des points sol', 'SOURCE · LIDAR CLASSÉ',
            'CIBLE · MODÈLE DE TERRAIN', left, right,
            'Classe 2 « Ground »  ·  Intersect  ·  sans tampon',
            'Les altitudes du MNT sont conservées sous l’empreinte du sol ; ailleurs : NoData.')


def wires():
    left, right = [], []
    left.append('<path d="M35 250 493 70" stroke="#697b63" stroke-width="1"/>')
    right.append('<path d="M35 250 493 70" stroke="#ffd83d" stroke-opacity=".3" '
                 'stroke-width="84" stroke-linecap="round"/>')
    for i in range(82):
        x = 35 + i * 458 / 81
        y = 250 - i * 180 / 81 + 2 * sin(i)
        left.append(dot(x, y, '#cf9e17', 3.5))
    for cx, cy in [(75, 62), (112, 212), (230, 157), (365, 71), (432, 230)]:
        for j in range(48):
            x = cx + 27 * sin(j * 2.4) * (j % 7 + 1) / 7
            y = cy + 24 * sin(j * 1.7) * (j % 5 + 1) / 5
            left.append(dot(x, y, GREEN, 3))
            if abs(180 * (x - 35) + 458 * (y - 250)) / hypot(180, 458) <= 42:
                right.append(dot(x, y, GREEN, 3))
    right.append('<path d="M35 250 493 70" stroke="#cf9e17" stroke-width="2" '
                 'stroke-dasharray="7 6"/>')
    diagram('wires', 'La végétation près des lignes électriques', 'SOURCE · POINTS DE CÂBLE',
            'CIBLE · POINTS DE VÉGÉTATION', left, right,
            'Classes 13 / 14 → classe 5  ·  Intersect  ·  tampon 10 m',
            'Vue en plan : le corridor retient les arbres proches de l’empreinte des câbles.')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for build in (ndvi, roofs, ground, wires):
        build()
    print(f'Built combination diagrams and covers in French and English in {OUT}')
