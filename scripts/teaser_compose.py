# -*- coding: utf-8 -*-
"""Teaser of a release from the takes of scripts/site_videos.py, edited by scripts/site_video_render.py.

    python3 teaser_compose.py en|fr 16x9|4x5

Each segment is a cut of a take with a caption in English and French; the closing card is drawn with Pillow. The
4:5 version keeps the 16:9 picture whole, the caption under it. Needs ffmpeg and the DejaVu fonts (the image of
scripts/docker/site_videos.Dockerfile has both):

    docker run --rm --user "$(id -u):$(id -g)" -v "$FM_WORK:/w" -v "$PWD/scripts:/s:ro" fm-video \
        python3 /s/teaser_compose.py en 16x9

Environment: FM_VIDEO_OUT (default /w/out, the takes are in its site/ folder), FM_TEASER_OUT (default /w/teaser),
FM_COMPARE_CUT ("start,duration" of the Compare take). The cuts below are those of the teaser of 5.1.1, recorded
on Toulouse Métropole on 2026-11-14; another recording needs its own times (read the <clip>-sheet.jpg of each take).
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

LANG, FMT = sys.argv[1], sys.argv[2]
SITE = os.path.join(os.environ.get('FM_VIDEO_OUT', '/w/out'), 'site')
OUT = os.environ.get('FM_TEASER_OUT', '/w/teaser')
TMP = f'/tmp/teaser_{LANG}_{FMT}'
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)
W, H = (1920, 1080) if FMT == '16x9' else (1080, 1350)
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BG = (18, 24, 32)
INK = (245, 245, 240)
ACCENT = (240, 160, 64)
E = 0 if LANG == 'en' else 1

# (take, start s, duration s, (EN, FR)); take 'card:<name>' is drawn
# one take of the agent per language: scripts/site_videos.py clip agent, with FM_AGENT_REQUEST in French for agent-fr
AGENT_TAKE = 'agent' if LANG == 'en' else 'agent-fr'
AGENT_CUTS = ((4.4, 3.2), (14.6, 3.2), (19.0, 2.4)) if LANG == 'en' else ((4.6, 3.2), (17.8, 3.2), (21.8, 2.4))
SEGMENTS = [
    ('metropole', 0.0, 2.4, ('One spatial question.\nOne answer, inside QGIS.', 'Une question spatiale.\nUne réponse, dans QGIS.')),
    ('metropole', 84.0, 3.0, ('One click filters 12 layers:\n360,577 buildings of Toulouse Métropole', 'Un clic filtre 12 couches :\n360 577 bâtiments de Toulouse Métropole')),
    ('heights', 0.4, 2.6, ('Vector, raster, point cloud:\neach can be the source or the target', 'Vecteur, raster, nuage de points :\nchacun peut être source ou cible')),
    ('postgis', 5.6, 2.8, ('The filter runs in the SQL of each source:\nPostGIS, GeoPackage, SpatiaLite, files', 'Le filtre s\'écrit dans le SQL de chaque source :\nPostGIS, GeoPackage, SpatiaLite, fichiers')),
    ('bridges', 25.0, 2.6, ('Chain filters: AND, OR, AND NOT,\nseveral targets at once', 'Enchaînez : ET, OU, SAUF,\nplusieurs cibles à la fois')),
    ('explore', 18.0, 2.6, ('Pick one feature, several,\nor write an expression', 'Une entité, plusieurs,\nou une expression')),
    ('heights', 51.6, 2.6, ('LiDAR: buildings over 7 m,\nread from the point cloud', 'LiDAR : les bâtiments de plus de 7 m,\nlus dans le nuage de points')),
    ('survey', 37.0, 2.8, ('Clip the terrain model and the cloud\naround a selection', 'Découpez le MNT et le nuage\nautour d\'une sélection')),
    ('compare', None, None, ('History: Undo, Redo,\nCompare before and after', 'Historique : Annuler, Rétablir,\nComparer avant et après')),
    ('favorites', 3.2, 2.4, ('Save a filter as a favorite,\nshare it with the project', 'Enregistrez un filtre en favori,\npartagez-le avec le projet')),
    ('export', 25.4, 3.2, ('Export only the answer: one GeoPackage\nkeeps the project and its structure', 'Exportez seulement la réponse : un GeoPackage\ngarde le projet et sa structure')),
    ('processing', 5.2, 3.0, ('Automate: Processing,\nPython and REST API, MCP', 'Automatisez : Processing,\nAPI Python et REST, MCP')),
    ('sam', 126.2, 5.0, ('SAM (experimental): one click outlines\nan object on the orthophoto, on your CPU', 'SAM (expérimental) : un clic détoure\nun objet sur l\'orthophoto, sur votre processeur')),
    ('sam', 153.4, 2.6, ('The objects then filter your other layers', 'Les objets filtrent ensuite vos autres couches')),
    (AGENT_TAKE, AGENT_CUTS[0][0], AGENT_CUTS[0][1], ('AGENT (experimental):\nask in one sentence', 'AGENT (expérimental) :\ndemandez en une phrase')),
    (AGENT_TAKE, AGENT_CUTS[1][0], AGENT_CUTS[1][1], ('It filters, and says what it did.\nHere with a local model, nothing leaves your computer', 'Il filtre, et dit ce qu\'il a fait.\nIci avec un modèle local, rien ne quitte votre ordinateur')),
    (AGENT_TAKE, AGENT_CUTS[2][0], AGENT_CUTS[2][1], ('Check every step. Undo in one click.', 'Vérifiez chaque étape. Annulez d\'un clic.')),
    ('card:end', 0, 3.6, ('FilterMate 5.1.1\nFree and open source · QGIS 3.22 to 4.x\nimagodata.github.io/filter_mate', 'FilterMate 5.1.1\nGratuit et open source · QGIS 3.22 à 4.x\nimagodata.github.io/filter_mate')),
]
COMPARE_CUT = tuple(float(v) for v in os.environ.get('FM_COMPARE_CUT', '45.0,5.2').split(','))


def font(path, size):
    return ImageFont.truetype(path, size)


def text_block(draw, lines, fonts, cx, top, fills, gap=14):
    y = top
    for line, f, fill in zip(lines, fonts, fills):
        w = draw.textlength(line, font=f)
        draw.text((cx - w / 2, y), line, font=f, fill=fill)
        y += f.size + gap
    return y


def card(name, text):
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    lines = text.split('\n')
    big = 76 if FMT == '16x9' else 60
    small = 40 if FMT == '16x9' else 32
    fonts = [font(BOLD, big)] + [font(REG, small)] * (len(lines) - 1)
    if FMT != '16x9':
        wrapped = [lines[0]]
        for ln in lines[1:]:
            while d.textlength(ln, font=fonts[1]) > W - 120 and ' ' in ln:
                cut = ln.rfind(' ', 0, len(ln) * (W - 120) // int(d.textlength(ln, font=fonts[1])))
                wrapped.append(ln[:cut])
                ln = ln[cut + 1:]
            wrapped.append(ln)
        lines = wrapped
        fonts = [fonts[0]] + [font(REG, small)] * (len(lines) - 1)
    height = sum(f.size + 22 for f in fonts)
    text_block(d, lines, fonts, W // 2, (H - height) // 2, [ACCENT] + [INK] * (len(lines) - 1), gap=22)
    path = f'{TMP}/card_{name}.png'
    img.save(path)
    return path


def caption_png(text, i):
    """Transparent overlay holding the caption band."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = text.split('\n')
    size = 46 if FMT == '16x9' else 40
    f = font(BOLD, size)
    while max(d.textlength(ln, font=f) for ln in lines) > W - 90 and size > 24:
        size -= 2
        f = font(BOLD, size)
    if FMT == '16x9':
        bh = len(lines) * (size + 14) + 36
        top = H - bh - 46
        bw = max(d.textlength(ln, font=f) for ln in lines) + 80
        d.rounded_rectangle([(W - bw) / 2, top, (W + bw) / 2, top + bh], radius=18, fill=(18, 24, 32, 225))
        text_block(d, lines, [f] * len(lines), W // 2, top + 18, [INK] * len(lines))
    else:
        vid_h = int(W * 9 / 16)
        top = (H - vid_h) // 2 + vid_h + 50
        text_block(d, lines, [f] * len(lines), W // 2, top, [INK] * len(lines), gap=18)
        t = font(BOLD, 44)
        text_block(d, ['FilterMate 5.1.1'], [t], W // 2, (H - vid_h) // 2 - 120, [ACCENT])
    path = f'{TMP}/cap_{i}.png'
    img.save(path)
    return path


def run(args):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + args)
    if r.returncode:
        sys.exit(f'ffmpeg failed: {args}')


ENC = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-r', '25', '-an']
parts = []
for i, (take, start, dur, texts) in enumerate(SEGMENTS):
    out = f'{TMP}/seg_{i:02d}.mp4'
    if take == 'compare':
        start, dur = COMPARE_CUT
        if not dur or not os.path.exists(f'{SITE}/compare.mp4'):
            print('compare take missing: segment skipped')
            continue
    if take.startswith('card:'):
        png = card(take[5:], texts[E])
        fade = f'fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3}:d=0.3'
        run(['-loop', '1', '-t', str(dur), '-i', png, '-vf', fade] + ENC + [out])
    else:
        cap = caption_png(texts[E], i)
        if FMT == '16x9':
            vf = f'[0:v]scale={W}:{H}[v];[v][1:v]overlay=0:0[o]'
        else:
            vid_h = int(W * 9 / 16)
            vf = (f'[0:v]scale={W}:{vid_h}[v];color=c=0x121820:s={W}x{H}:d={dur}[bg];'
                  f'[bg][v]overlay=0:{(H - vid_h) // 2}[b];[b][1:v]overlay=0:0[o]')
        run(['-ss', str(start), '-t', str(dur), '-i', f'{SITE}/{take}.mp4', '-loop', '1', '-t', str(dur), '-i', cap,
             '-filter_complex', vf, '-map', '[o]', '-t', str(dur)] + ENC + [out])
    parts.append(out)

with open(f'{TMP}/list.txt', 'w') as fh:
    fh.write(''.join(f"file '{p}'\n" for p in parts))
final = f'{OUT}/filtermate-5.1.1-teaser-{LANG}-{FMT}.mp4'
run(['-f', 'concat', '-safe', '0', '-i', f'{TMP}/list.txt', '-c', 'copy', '-movflags', '+faststart', final])
probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size', '-of', 'csv=p=0', final],
                       capture_output=True, text=True).stdout.strip()
print(final, probe)
