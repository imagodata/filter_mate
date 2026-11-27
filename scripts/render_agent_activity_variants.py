#!/usr/bin/env python3
"""Generate the native SVG state family and its review boards from the runtime artwork."""
import argparse
import importlib.util
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fm_activity_design', ROOT / 'ui/styles/mockup_design.py')
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)

LABELS = {
    'idle': 'Prêt pour un message', 'complete': 'Terminé', 'drafting': 'Saisie du message', 'queued': 'File d’attente',
    'thinking': 'Réflexion', 'searching': 'Recherche de données', 'reading': 'Lecture des données',
    'fetching': 'Récupération distante', 'processing': 'Calcul et traitement', 'editing': 'Édition de couche',
    'designing': 'Style et mise en page', 'exporting': 'Export des fichiers', 'navigating': 'Navigation QGIS',
    'working': 'Autre action', 'responding': 'Rédaction de la réponse', 'confirming': 'Confirmation utilisateur',
    'waiting': 'Attente d’une interface', 'listening': 'Enregistrement vocal', 'transcribing': 'Transcription audio',
    'retry': 'Nouvelle tentative', 'stopping': 'Arrêt demandé', 'error': 'Intervention nécessaire',
}


def documents():
    result = {}
    for dark in (False, True):
        theme = 'dark' if dark else 'light'
        color = design.tokens(dark)['fm_icon']
        for phase in LABELS:
            result[f'states/{phase}-{theme}.svg'] = design.agent_activity_svg(color, True, phase) + '\n'
    for animated in (False, True):
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="860" viewBox="0 0 1200 860">',
               '<title>Les 22 états du réseau de l’agent FilterMate</title>',
               '<rect width="1200" height="860" fill="#e5e8ec"/>']
        for side, dark in enumerate((False, True)):
            x0 = side * 600
            background, foreground, muted = ('#202124', '#eeeeee', '#bfc5cd') if dark else ('#ffffff', '#25282c', '#60666f')
            svg += [f'<rect x="{x0 + 12}" y="12" width="576" height="836" rx="16" fill="{background}"/>',
                    f'<g font-family="sans-serif" fill="{foreground}">',
                    f'<text x="{x0 + 32}" y="47" font-size="21" font-weight="bold">Réseau pulsé · {"sombre" if dark else "clair"}</text>',
                    f'<text x="{x0 + 32}" y="72" font-size="12" fill="{muted}">Statique au repos · animation pendant l’activité</text>']
            for index, (phase, label) in enumerate(LABELS.items()):
                x, y = x0 + 32 + index % 2 * 275, 100 + index // 2 * 66
                icon = design.agent_activity_svg(design.tokens(dark)['fm_icon'], animated, phase)
                body = icon.partition('>')[2].rsplit('</svg>', 1)[0]
                icon = (f'<g transform="translate({x} {y})"><g transform="scale({44 / 24})" '
                        f'fill="none" stroke="{design.tokens(dark)["fm_icon"]}" stroke-width="1.6" '
                        f'stroke-linecap="round" stroke-linejoin="round">{body}</g></g>')
                orbit, pulse, _count, _radius = design.AGENT_ACTIVITY_STYLES[phase]
                movement = 'Statique' if phase in design.STATIC_AGENT_PHASES else (
                    f'Orbite {orbit:g} s' if orbit else f'Pulsation {pulse:g} s')
                svg += [icon, f'<text x="{x + 54}" y="{y + 18}" font-size="12" font-weight="bold">{escape(label)}</text>',
                        f'<text x="{x + 54}" y="{y + 36}" font-size="11" fill="{muted}">{movement}</text>']
            svg.append('</g>')
        svg.append('</svg>\n')
        result['agent-states-' + ('animated' if animated else 'static') + '.svg'] = '\n'.join(svg)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    destination = ROOT / 'docs/design/agent-identity'
    changed = []
    for name, document in documents().items():
        path = destination / name
        if not path.exists() or path.read_text() != document:
            changed.append(name)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(document)
    if args.check and changed:
        raise SystemExit('Outdated agent artwork: ' + ', '.join(changed))
    print(f'{len(documents())} SVG documents checked' if args.check else f'{len(changed)} SVG documents written')


if __name__ == '__main__':
    main()
