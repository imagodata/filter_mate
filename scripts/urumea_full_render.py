"""Edit the verified from-zero take, preserving QGIS and FilterMate throughout.

Only the logo opening and the caption strip outside the app are graphic assets.
Magnifiers duplicate actual recorded pixels in an inset over the canvas.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
import subprocess
import textwrap
from PIL import Image, ImageDraw
from urumea_slope_render import logo_frame
from urumea_linkedin_render import font, srt_time

W, H, FPS = 1920, 1080, 25


class Take:
    def __init__(self, path):
        self.path = path
        self.meta = json.loads((path / 'meta.json').read_text())
        if self.meta['status'] != 'complete':
            raise ValueError('Refuse an incomplete/failed take: ' + str(path))
        self.marks = {e['name']: e['t'] for e in self.meta['events'] if e['kind'] == 'mark'}
        self.cache = {}

    def frame(self, timestamp):
        i = max(0, min(len(self.meta['frames']) - 1,
                       bisect.bisect_right(self.meta['frames'], timestamp) - 1))
        if i not in self.cache:
            self.cache.clear()
            self.cache[i] = Image.open(self.path / 'frames' / f'{i:06d}.jpg').convert('RGB')
        return self.cache[i].copy()

    def stage(self, name):
        return self.marks['ask:' + name], self.marks['done:' + name]

    def send_time(self, name):
        start, end = self.stage(name)
        clicks = [event['t'] for event in self.meta['events'] if event['kind']=='click'
                  and start < event['t'] < end and event.get('x',0)>1800]
        return clicks[-1] if clicks else start


def progress(take, name, elapsed, duration, result=None):
    start, done = take.stage(name)
    # The interaction gets 55 % of the scene; the result stays readable after it.
    action = min(11, duration * .55)
    send = take.send_time(name)
    hold_prompt = min(5, action*.5)
    if elapsed < hold_prompt:
        return take.frame(max(start,send-.12))
    if elapsed < action:
        return take.frame(send + (done-send) * (elapsed-hold_prompt)/(action-hold_prompt))
    target = take.marks.get('still:' + (result or 'result-' + name), done + 3)
    return take.frame(target)


def magnify(frame, source=(1465, 222, 433, 345)):
    x, y, width, height = source
    crop = frame.crop((x, y, x + width, y + height))
    crop.thumbnail((865, 685)) if crop.width > 865 else None
    scale = min(865 / crop.width, 685 / crop.height)
    crop = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
    px, py = 420, 205
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((px - 8, py - 34, px + crop.width + 8, py + crop.height + 8), radius=8, fill='#123747')
    draw.text((px + 4, py - 30), 'Loupe', font=font(20, True), fill='#b9e5ee')
    frame.paste(crop, (px, py))
    return frame


def caption(frame, title, text, elapsed, duration):
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, 990, W, H), fill='#102f3f')
    draw.text((35, 998), title, font=font(23, True), fill='#81cddf')
    chunks = textwrap.wrap(text, width=117, break_long_words=False, break_on_hyphens=False)
    index = min(len(chunks) - 1, int(elapsed / max(.001, duration) * len(chunks)))
    if chunks:
        draw.text((35, 1033), chunks[index], font=font(27), fill='white')
    return frame


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--acquire', type=Path, required=True)
    p.add_argument('--analysis', type=Path, required=True)
    p.add_argument('--composer', type=Path, required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--verified', type=Path, required=True)
    args = p.parse_args()
    proof = json.loads(args.verified.read_text())
    if not proof.get('verified'):
        raise ValueError('Independent verification is required before editing')
    root = args.root
    out = root / 'final'
    out.mkdir(exist_ok=True)
    acquired, analysis, composer, review = Take(args.acquire), Take(args.analysis), Take(args.composer), Take(args.review)
    voices = {}
    for folder in ('intro', 'body'):
        manifest = json.loads((root / 'voice' / folder / 'voice-manifest.json').read_text())
        for line in manifest['lines']:
            voices[line['id']] = dict(line, path=root / 'voice' / folder / line['file'])
    scenes = [
        ('intro', '00-intro-imagodata', 6, 'imagodata présente'),
        ('depart', '01-depart', 8, '01 · Un projet vide'),
        ('sources', '02-sources', 20, '02 · Acquérir les sources · attentes raccourcies'),
        ('sauvegarde', '03-sauvegarde', 12, '03 · Conserver le projet et ses données'),
        ('terrain', '04-terrain', 22, '04 · MNT 5 m → pente (%) → moyenne par emprise'),
        ('corridor', '05-couloir', 20, '05 · Moteur de filtre · couloir de 500 m'),
        ('t100', '06-ura', 20, '06 · Couloir ET zonage officiel URA T100'),
        ('reseau', '07-reseau', 12, '07 · Un filtre en cascade · voies et objets ponts à 300 m'),
        ('charts', '08-graphiques', 22, '08 · Deux graphiques D3.js sur les résultats observés'),
        ('composer', '09-composer', 20, '09 · Une mise en page QGIS A3'),
        ('export', '10-export', 16, '10 · Moteur d’export · GeoPackage et GeoTIFF'),
        ('pdf', '11-pdf', 10, '11 · Le PDF effectivement exporté'),
        ('projet', '12-projet', 14, '12 · Le projet, ses données et sa composition'),
    ]
    durations = [math.ceil(max(minimum, voices[voice]['duration_s'] + 1.4) * FPS) / FPS
                 for _, voice, minimum, _ in scenes]
    total = sum(durations)
    opening = logo_frame(root).convert('RGB')
    opening.save(out / 'urumea-intro-logo.png')
    video = out / 'urumea-from-zero-5.1.3-fr.mp4'
    command = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{W}x{H}', '-r', str(FPS), '-i', 'pipe:0']
    for _, voice, _, _ in scenes:
        command += ['-i', str(voices[voice]['path'])]
    filters, offset = [], 0
    for i, duration in enumerate(durations):
        filters.append(f'[{i+1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={round((offset+.3)*1000)}|{round((offset+.3)*1000)}[a{i}]')
        offset += duration
    filters.append(''.join(f'[a{i}]' for i in range(len(scenes))) + f'amix=inputs={len(scenes)}:normalize=0,loudnorm=I=-18:TP=-2:LRA=9,apad[a]')
    command += ['-filter_complex', ';'.join(filters), '-map', '0:v', '-map', '[a]', '-t', str(total),
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
                '-threads', '4', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
                '-metadata:s:a:0', 'language=fra', '-movflags', '+faststart', str(video)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    timeline, subtitles, clock = [], [], 0.0
    try:
        for (scene, voice, _, title), duration in zip(scenes, durations):
            text = voices[voice]['text']
            print(scene, duration, flush=True)
            timeline.append({'scene': scene, 'start': clock, 'duration': duration, 'voice': voice, 'title': title})
            chunks = textwrap.wrap(text, width=117, break_long_words=False, break_on_hyphens=False)
            for k, chunk in enumerate(chunks):
                subtitles.append((clock + k / len(chunks) * duration, clock + (k + 1) / len(chunks) * duration, chunk))
            for i in range(round(duration * FPS)):
                t = i / FPS
                if scene == 'intro':
                    frame = opening.copy()
                elif scene == 'depart':
                    frame = acquired.frame(min(3.9, t * .4))
                elif scene == 'sources':
                    frame = progress(acquired, 'sources', t, duration)
                elif scene == 'sauvegarde':
                    start = acquired.marks['native-save-card']
                    end = acquired.marks['still:saved']
                    frame = acquired.frame(start + (end-start) * min(1, t / (duration*.8)))
                elif scene in ('terrain', 'corridor', 't100', 'reseau'):
                    result = 'filtering-' + scene if scene != 'terrain' else None
                    frame = progress(analysis, scene, t, duration, result)
                    if scene != 'terrain' and t > duration*.8:
                        frame = analysis.frame(analysis.marks['still:result-' + scene])
                elif scene == 'charts':
                    first = t < duration / 2
                    frame = progress(composer, 'progression' if first else 'histogramme',
                                     t if first else t-duration/2, duration/2)
                elif scene == 'composer':
                    frame = review.frame(review.marks['still:composer-fit']) if t > duration*.4 else progress(composer,'composer',t,duration*.8)
                elif scene == 'export':
                    frame = progress(composer, 'export', t, duration, 'exporting-native')
                elif scene == 'pdf':
                    frame = review.frame(review.marks['still:pdf-fit'])
                else:
                    start = composer.marks['native-save-card']
                    end = composer.marks['still:saved']
                    frame = composer.frame(start+(end-start)*min(1,t/(duration*.7)))
                    if t > duration*.75:
                        frame = review.frame(review.marks['still:moved-project'])
                if scene != 'intro':
                    # Temporary inset only: the full underlying QGIS UI remains in frame.
                    if scene in ('sources','terrain','corridor','t100','reseau','export') and 2 < t < 4.5:
                        frame = magnify(frame, (1458, 700, 445, 145))
                    if scene == 'charts' and (duration*.36 < t < duration*.46 or duration*.86 < t < duration*.96):
                        frame = magnify(frame)
                    if scene == 'composer' and duration*.65 < t < duration*.82:
                        frame = magnify(frame, (780, 425, 225, 325))
                    frame = caption(frame, title, text, t, duration)
                assert frame.size == (W,H)
                proc.stdin.write(frame.tobytes())
            frame.save(out / ('poster-' + scene + '.jpg'))
            clock += duration
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError('Video encoder failed')
    (out / 'urumea-from-zero-5.1.3-fr.srt').write_text('\n\n'.join(
        f'{i+1}\n{srt_time(a)} --> {srt_time(b)}\n{text}' for i,(a,b,text) in enumerate(subtitles))+'\n')
    (out / 'edit.json').write_text(json.dumps({'duration_s': total, 'fps': FPS, 'size': [W,H],
        'takes': [str(path) for path in (args.acquire,args.analysis,args.composer,args.review)], 'scenes':timeline,
        'qgis_frame': [0,0,1920,990], 'captions_outside_qgis': True,
        'source': 'recorded QGIS desktop; magnifiers duplicate recorded pixels',
        'publication': 'not_published'}, ensure_ascii=False,indent=2)+'\n')
    print(video, total, flush=True)


if __name__ == '__main__':
    main()
