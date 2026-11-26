"""Render the slower real Urumea take; Tony introduces, Benjamin narrates.

Only the title frame is composed graphically. Every map image comes from the
recorded QGIS window. Run --intro-only to produce the standalone logo opening.
"""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageOps, ImageChops, ImageStat
from urumea_linkedin_render import font, pill, subtitle, credits, srt_time, BG, INK

W, H, FPS = 1920, 1080, 25
TITLES = {'place': 'Saint-Sébastien · Urumea', 'pente': '1 · Du relief à la pente',
          'moyenne': '2 · Une moyenne par bâtiment', 'seuil': '3 · Pente moyenne < 10 %',
          'filtre': '4 · À moins de 500 m de la rivière', 'reseau': '5 · Routes et ponts à 300 m',
          'favori': '6 · Enregistrer le favori', 'reset': '7 · Revenir à la carte complète',
          'rejeu': '8 · Rejouer le même filtre', 'export': '9 · Exporter les résultats'}


def logo_frame(root):
    frame = Image.new('RGBA', (W, H), (*BG, 255))
    draw = ImageDraw.Draw(frame)
    def centered(text, y, size, bold=False, color=INK):
        face = font(size, bold)
        x = (W - draw.textlength(text, font=face)) / 2
        draw.text((x, y), text, font=face, fill=(*color, 255))
    centered('imagodata présente', 130, 37)
    logo = Image.open(root / 'assets/filtermate-logo.png').convert('RGBA')
    logo.thumbnail((350, 350), Image.Resampling.LANCZOS)
    frame.alpha_composite(logo, ((W - logo.width) // 2, 270))
    centered('FilterMate', 674, 100, True)
    centered('Le meilleur compagnon pour QGIS', 825, 35, color=(111, 201, 218))
    centered('Un exemple d’analyse de l’Urumea — Saint-Sébastien', 920, 29, color=(176, 197, 208))
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/w'))
    parser.add_argument('--take', type=Path)
    parser.add_argument('--intro-only', action='store_true')
    parser.add_argument('--analysis-only', action='store_true')
    args = parser.parse_args()
    root = args.root
    out = root / 'final'
    out.mkdir(exist_ok=True)
    intro_manifest = json.loads((root / 'voice/intro/voice-manifest.json').read_text())
    body_manifest = json.loads((root / 'voice/body/voice-manifest.json').read_text())
    tracks = {line['id']: {**line, 'path': root / 'voice/body' / line['file']} for line in body_manifest['lines']}
    tracks.update({line['id']: {**line, 'path': root / 'voice/intro' / line['file']} for line in intro_manifest['lines']})
    opening = logo_frame(root)
    opening.convert('RGB').save(out / 'urumea-intro-logo.png')
    intro_duration = math.ceil(max(5.5, tracks['00-intro-imagodata']['duration_s'] + 1.5) * FPS) / FPS
    if args.intro_only:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-i', str(out / 'urumea-intro-logo.png'),
                        '-i', str(tracks['00-intro-imagodata']['path']), '-vf', 'fps=25', '-af', 'apad',
                        '-t', str(intro_duration), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-movflags', '+faststart',
                        str(out / 'urumea-intro-tony.mp4')], check=True)
        print('intro ready', intro_duration, flush=True)
        return
    if args.take is None:
        parser.error('--take is required unless --intro-only is selected')
    take = args.take
    meta = json.loads((take / 'meta.json').read_text())
    verification = json.loads((take / 'verified-observations.json').read_text())
    assert meta['status'] == 'complete' and verification['verified']
    marks = {e['name']: e['t'] for e in meta['events'] if e['kind'] == 'mark'}
    stages = ['moyenne', 'seuil', 'filtre', 'reseau'] + ([] if args.analysis_only else ['reset', 'rejeu'])
    observed = {stage: json.loads((take / (stage + '-observed.json')).read_text()) for stage in stages}
    event = next(e for e in meta['events'] if e['kind'] == 'camera' and e['t'] > marks['done:pente'] and e['rect'][2] < W * .85)
    x, y, width, height = event['rect']
    box = (x, y, x + width, y + height)
    cached = {}
    def raw(t):
        index = max(0, min(len(meta['frames']) - 1, bisect.bisect_right(meta['frames'], t) - 1))
        if index not in cached:
            cached.clear()
            cached[index] = Image.open(take / 'frames' / f'{index:06d}.jpg').convert('RGB')
        return cached[index]
    before = raw(marks['still:result-' + ('moyenne' if args.analysis_only else 'reset')]).crop(box).copy()
    after = raw(marks['still:result-' + ('reseau' if args.analysis_only else 'rejeu')]).crop(box).copy()
    assert sum(ImageStat.Stat(ImageChops.difference(before, after)).mean) > 4
    plan = [('intro', '00-intro-imagodata', intro_duration), ('place', '01-intro', 8),
            ('pente', '02-pente', 15), ('moyenne', '03-moyenne', 15), ('seuil', '04-seuil', 12),
            ('filtre', '05-riviere', 15), ('reseau', '06-reseau', 12), ('favoris', '07-favori', 18),
            ('export', '08-fin', 12)]
    if args.analysis_only:
        plan = [(stage, voice, {'pente': 17, 'moyenne': 16, 'filtre': 17}.get(stage, minimum))
                for stage, voice, minimum in plan if stage != 'favoris']
    parts, clock = [], 0
    for stage, voice, minimum in plan:
        offset = 1.5 if stage == 'favoris' else (0 if stage == 'intro' else .7)
        duration = max(minimum, tracks[voice]['duration_s'] + offset + (1.5 if stage == 'intro' else 4))
        duration = math.ceil(duration * FPS) / FPS
        parts.append({'stage': stage, 'voice': voice, 'start_s': clock, 'duration_s': duration, 'voice_offset_s': offset})
        clock += duration
    def view(stage, local, duration):
        action = min({'pente': 6, 'moyenne': 6, 'seuil': 3, 'filtre': 6, 'reseau': 4,
                      'favori': 1.5, 'reset': 1.5, 'rejeu': 1.2, 'export': 3}[stage], duration * .6)
        if local < action:
            clicks = [e['t'] for e in meta['events'] if e['kind'] == 'click' and marks['ask:' + stage] < e['t'] < marks['done:' + stage]]
            start = clicks[1] - .35 if len(clicks) > 1 else marks['ask:' + stage]
            stamp = start + (marks['done:' + stage] + .25 - start) * local / action
            return raw(stamp).resize((W, H)).convert('RGBA'), False
        return map_view(marks['still:result-' + stage]), True
    def map_view(stamp):
        frame = Image.new('RGBA', (W, H), (*BG, 255))
        picture = ImageOps.contain(raw(stamp).crop(box), (1400, 1080), Image.Resampling.LANCZOS)
        frame.alpha_composite(picture.convert('RGBA'), ((1400 - picture.width) // 2, (H - picture.height) // 2))
        return frame
    def compose(part, local):
        stage = part['stage']
        if stage == 'intro':
            return opening.copy()
        if stage == 'place':
            frame, held = map_view(marks['still:baseline']), True
        elif stage == 'favoris':
            stage, offset, duration = ('favori', 0, 3) if local < 3 else (('reset', 3, 4) if local < 7 else ('rejeu', 7, part['duration_s'] - 7))
            frame, held = view(stage, local - offset, duration)
        else:
            frame, held = view(stage, local, part['duration_s'])
        pill(frame, TITLES[stage], (55, 28), size=29)
        if held:
            draw = ImageDraw.Draw(frame)
            context = ['FilterMate 5.1.3', 'Modèle de surface', 'Résolution · 30 m']
            if stage != 'place':
                context.append('Pente moyenne < 10 %' if stage in ('seuil', 'filtre', 'reseau', 'favori', 'rejeu', 'export') else 'Pente · en %')
            if stage in ('filtre', 'reseau', 'favori', 'rejeu', 'export'):
                context.append('Rivière · 500 m')
            if stage in ('reseau', 'favori', 'rejeu', 'export'):
                context.append('Réseau · 300 m')
            for j, text in enumerate(context):
                draw.text((1440, 190 + j * 61), text, font=font(29, j == 0), fill=(*INK, 255))
            data_stage = 'reseau' if stage in ('favori', 'export') else stage
            if data_stage in observed:
                buildings = next((layer for layer in observed[data_stage]['layers'] if layer['name'] == 'Bâtiments pente'), None)
                if buildings:
                    draw.text((1440, 560), f"{buildings['count']:,}".replace(',', ' '), font=font(67, True), fill=(111, 201, 218, 255))
                    draw.text((1440, 650), 'bâtiments', font=font(30), fill=(*INK, 255))
            if stage == 'export':
                draw.text((1440, 750), 'Seuils illustratifs', font=font(25), fill=(*INK, 255))
                draw.text((1440, 795), 'Aucune prévision', font=font(25), fill=(*INK, 255))
                draw.text((1440, 835), 'de crue', font=font(25), fill=(*INK, 255))
        else:
            pill(frame, 'Attente montée', (W - 300, H - 90), size=20)
        credits(frame)
        return frame
    cues, subtitles = [], []
    for part in parts:
        line = tracks[part['voice']]
        words, chunks, chunk = line['text'].split(), [], []
        for word in words:
            if chunk and (len(' '.join(chunk + [word])) > 100 or chunk[-1].endswith(('.', '…', ':'))):
                chunks.append(chunk); chunk = []
            chunk.append(word)
        if chunk: chunks.append(chunk)
        cursor = part['start_s'] + part['voice_offset_s']
        for chunk in chunks:
            end = cursor + line['duration_s'] * len(chunk) / len(words)
            text = ' '.join(chunk)
            cues.append((cursor, end, text))
            subtitles.append(f'{len(subtitles) + 1}\n{srt_time(cursor)} --> {srt_time(end)}\n{text}\n')
            cursor = end
    (out / 'urumea-pente.fr.srt').write_text('\n'.join(subtitles), encoding='utf-8')
    silent = out / 'urumea-pente.silent.mp4'
    encoder = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', '25', '-i', '-',
                                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', '-an', str(silent)], stdin=subprocess.PIPE)
    thumbnails = []
    for part in parts:
        for n in range(round(part['duration_s'] * FPS)):
            local, absolute = n / FPS, part['start_s'] + n / FPS
            frame = compose(part, local)
            cue = next((text for start, end, text in cues if start <= absolute < end), None)
            if cue and part['stage'] != 'intro': subtitle(frame, cue)
            rgb = frame.convert('RGB')
            encoder.stdin.write(rgb.tobytes())
            if n == round(part['duration_s'] * FPS) - 1:
                thumbnails.append(rgb.resize((480, 270)))
        print('rendered', part['stage'], flush=True)
    encoder.stdin.close()
    assert encoder.wait() == 0
    inputs, filters, labels = [], [], []
    for i, part in enumerate(parts):
        inputs += ['-i', str(tracks[part['voice']]['path'])]
        delay = round((part['start_s'] + part['voice_offset_s']) * 1000)
        filters.append(f'[{i + 1}:a]adelay={delay}:all=1[a{i}]'); labels.append(f'[a{i}]')
    filters.append(''.join(labels) + f'amix=inputs={len(parts)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[audio]')
    final = out / 'urumea-pente-5.1.3-fr.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(silent), *inputs, '-filter_complex', ';'.join(filters), '-map', '0:v', '-map', '[audio]',
                    '-c:v', 'copy', '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-b:a', '192k', '-t', str(clock), '-movflags', '+faststart', str(final)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(final), '-f', 'null', '-'], check=True)
    sheet = Image.new('RGB', (1440, 810), BG)
    for i, thumb in enumerate(thumbnails): sheet.paste(thumb, ((i % 3) * 480, (i // 3) * 270))
    sheet.save(out / 'urumea-pente-sheet.jpg', quality=93)
    receipt = {'video': final.name, 'duration_s': clock, 'sha256': hashlib.sha256(final.read_bytes()).hexdigest(),
               'full_decode_check': 'passed', 'intro_voice': intro_manifest['voice_name'], 'body_voice': body_manifest['voice_name'],
               'package': json.loads((root / 'package.json').read_text()), 'take': str(take), 'segments': parts,
               'verification': verification, 'publication': 'not_published'}
    (out / 'urumea-pente-validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'video': str(final), 'duration_s': clock, 'decode': 'passed'}), flush=True)


if __name__ == '__main__':
    main()
