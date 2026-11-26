# -*- coding: utf-8 -*-
"""Edit the Sarlat film (ln, three chapters) into a captioned 1920x1200 MP4.

Usage (the Python of QGIS has Pillow; ffmpeg must be on PATH or in FM_FFMPEG)::

    set FM_LANG=en            (en or fr)
    set FM_VOICE_ENGINE=edge-tts   (the folder voice/<engine>/<lang> made by scripts/fm5_clip_voice.py)
    python fm5_clip_render.py ln

Reads ``<FM_VIDEO_OUT>/<clip>/meta.json`` and ``frames/*.jpg`` and writes, in ``<FM_VIDEO_OUT>/site/``:

* ``<clip>-<lang>.mp4``: H.264 + AAC, 1920x1200, with burned-in captions of the voice-over lines, the
  title chip, the result badge and an end card, behind a cover (the hook over the best result) that is
  the very first frame, so it is also the thumbnail of the post;
* ``<clip>-<lang>-cover.jpg`` (1920x1200) and ``-cover-link.jpg`` (1200x627, the centre of it, for a link
  preview): the same cover as a still;
* ``<clip>-<lang>-result<N>.jpg``: the result of chapter N (map and dock, with the badge);
* ``<clip>-result<N>-fullscreen.jpg``: the same moment, the whole recorded screen, untouched;
* ``<clip>-<lang>-sheet.jpg``: a contact sheet to review the edit without a player.

The camera, the cursor and the fast-forwards are those of ``site_video_render.py``. The voice lines are
placed at their ``say`` events; when a line would run into the next one, the picture holds for the
difference (the recording waits for the longest voice, so this only happens after a frozen QGIS).
If ``<FM_VIDEO_OUT>/music/bed.mp3`` exists it is mixed under the voice at low volume.
``FM_VOICE_ENGINE=none`` makes a silent rough cut (``-silent.mp4``), with estimated subtitle durations.
"""
import bisect
import json
import os
import subprocess
import sys

os.environ.setdefault('FM_SIZE', '1920x1200')  # the whole primary screen (16:10), no crop

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

import site_video_render as base  # noqa: E402

ROOT, FFMPEG, FPS = base.ROOT, base.FFMPEG, base.FPS
OUT_W, OUT_H = base.OUT_W, base.OUT_H
LANG = os.environ.get('FM_LANG', 'en')
ENGINE = os.environ.get('FM_VOICE_ENGINE', 'edge-tts')
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.environ.get('FM_FONTS', r'C:\Windows\Fonts')
CARD = 3.6          # seconds of end card after the last frame
TITLE = 3.8         # seconds the title chip stays
FREEZE = 0.001      # speed factor that holds the picture
COVER = float(os.environ.get('FM_COVER', '1.6'))  # seconds of cover before the film (0: none)


def font(size, bold=False):
    for name in (('segoeuib.ttf', 'arialbd.ttf') if bold else ('segoeui.ttf', 'arial.ttf')):
        try:
            return ImageFont.truetype(os.path.join(FONTS, name), size)
        except OSError:
            continue
    try:
        return ImageFont.truetype(base.FONT_BOLD if bold else base.FONT, size)
    except OSError:
        pass
    return ImageFont.load_default()


def ffprobe_duration(path):
    folder, name = os.path.split(FFMPEG)
    probe = os.environ.get('FM_FFPROBE', os.path.join(folder, name.replace('ffmpeg', 'ffprobe')))
    out = subprocess.run([probe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def wrap(draw, text, face, width):
    lines, line = [], ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if draw.textlength(trial, font=face) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def pill(frame, box, fill, radius=18):
    over = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(over).rounded_rectangle(box, radius=radius, fill=fill)
    frame.alpha_composite(over)


def fade(to, start, length=0.35, end=None, out=0.35):
    """0..1 envelope: in at ``start``, out at ``end`` (None: stays)."""
    a = min(max((to - start) / length, 0.0), 1.0)
    if end is not None:
        a = min(a, min(max((end - to) / out, 0.0), 1.0))
    return a


def hold_for_voice(events, voice, clip):
    """Freeze events so that no voice line starts before the previous one is spoken."""
    says = sorted((e for e in events if e['kind'] == 'say'), key=lambda e: e['t'])
    added = []
    for prev, nxt in zip(says, says[1:]):
        clock = base.Clock(events + added, 1e9)
        gap = clock.out(nxt['t']) - clock.out(prev['t'])
        need = voice[prev['key']] + 0.35
        if gap < need:
            t = nxt['t'] - 0.01
            before = base.Clock(events + added, 1e9)
            i = bisect.bisect_right([k[0] for k in before.knots], t) - 1
            factor = before.knots[i][1]
            added.append({'kind': 'speed', 't': t, 'factor': FREEZE})
            added.append({'kind': 'speed', 't': t + (need - gap) * FREEZE, 'factor': factor})
            print(f'  holding the picture {need - gap:.1f} s before line {nxt["key"]}')
    return events + added


def render(clip):
    base_dir = os.path.join(ROOT, clip)
    with open(os.path.join(base_dir, 'meta.json'), encoding='utf-8') as f:
        meta = json.load(f)
    if meta.get('status') != 'complete':
        raise ValueError('capture integrity must pass before editing')
    with open(os.path.join(HERE, 'sarlat_narration.json'), encoding='utf-8') as f:
        narration = json.load(f)
    spec = narration['clips'][clip]
    voice_dir = os.path.join(ROOT, 'voice', ENGINE, LANG)
    times, events = base.close_gaps(meta['frames'], meta['events'])
    keys = {event['key'] for event in events if event['kind'] == 'say'}
    if ENGINE == 'none':
        voice = {key: max(2.0, len(spec['lines'][key][LANG].split()) / 2.5) for key in keys}
    else:
        voice = {key: ffprobe_duration(os.path.join(voice_dir, f'{clip}-{key}.mp3')) for key in keys}
    events = hold_for_voice(events, voice, clip)
    dpr, size = meta['dpr'], tuple(meta['size'])
    clock = base.Clock(events, times[-1])
    camera = base.Camera(events, clock, size)
    cursor = base.Cursor(events, clock)
    sprite, hotspot = base.cursor_sprite()
    duration = clock.duration
    voice_end = max((clock.out(e['t']) + voice[e['key']] + 0.35 for e in events
                     if e['kind'] == 'say'), default=0.0)
    duration = max(duration, voice_end)  # the last line must finish before the end card
    total = duration + CARD
    n_out = int(total * FPS)
    entry = (size[0] * 0.55, size[1] * 0.75)

    says = [(clock.out(e['t']), e['key']) for e in events if e['kind'] == 'say']
    chapters = sorted((clock.out(e['t']), e['n']) for e in events if e['kind'] == 'chapter')
    # a badge lives from its result to the next chapter
    badges = []
    for e in sorted((e for e in events if e['kind'] == 'badge'), key=lambda e: e['t']):
        start = clock.out(e['t'])
        end = next((t for t, _n in chapters if t > start), total)
        badges.append((start, end, spec['badges'][str(e['n'])][LANG].format_map(e['counts'])))
    results = {int(e['name'][len('still:result'):]): clock.out(e['t']) for e in events
               if e['kind'] == 'mark' and str(e.get('name', '')).startswith('still:result')}

    cache = {}
    # the frame size is the truth (a 1707 px window at 150 % is 2561 px wide, not round(2560.5))
    full_px = Image.open(os.path.join(base_dir, 'frames', '000000.jpg')).size
    sx, sy = full_px[0] / size[0], full_px[1] / size[1]

    def source(ts):
        i = max(bisect.bisect_right(times, ts) - 1, 0)
        if i not in cache:
            cache.clear()
            im = Image.open(os.path.join(base_dir, 'frames', f'{i:06d}.jpg')).convert('RGB')
            if im.size != full_px:
                fixed = Image.new('RGB', full_px, im.getpixel((im.width - 1, im.height - 1)))
                fixed.paste(im, (0, 0))
                im = fixed
            cache[i] = im
        return cache[i]

    def compose(to):
        cx, cy, w = camera.at(to)
        h = w / (OUT_W / OUT_H)
        box = ((cx - w / 2) * sx, (cy - h / 2) * sy, (cx + w / 2) * sx, (cy + h / 2) * sy)
        box = (max(box[0], 0.0), max(box[1], 0.0), min(box[2], float(full_px[0])), min(box[3], float(full_px[1])))
        frame = source(clock.src(to)).resize((OUT_W, OUT_H), Image.Resampling.BICUBIC, box=box).convert('RGBA')
        k = OUT_W / (box[2] - box[0])
        for tc, x, y in cursor.clicks:
            base.draw_ripple(frame, (x * sx - box[0]) * k, (y * sy - box[1]) * k, to - tc)
        c = cursor.at(to, entry)
        if c and c[2] > 0:
            px, py = (c[0] * sx - box[0]) * k, (c[1] * sy - box[1]) * k
            press = any(0 <= to - tc < 0.14 for tc, _x, _y in cursor.clicks)
            spr = sprite if not press else sprite.resize((int(sprite.width * 0.88), int(sprite.height * 0.88)))
            if c[2] < 1:
                spr = spr.copy()
                spr.putalpha(spr.getchannel('A').point(lambda v: int(v * c[2])))
            frame.alpha_composite(spr, (int(px - hotspot[0]), int(py - hotspot[1])))
        return frame

    def draw_badge(frame, to):
        found = next(((b0, b1, text) for b0, b1, text in badges if b0 + 0.3 <= to < b1), None)
        if found is None:
            return
        b0, b1, badge_text = found
        a = fade(to, b0 + 0.3, 0.35, b1 - 0.1, 0.3)
        face = font(38, True)
        d = ImageDraw.Draw(frame)
        width = d.textlength(badge_text, font=face)
        x1, y0 = OUT_W - 48, 48
        box = (x1 - width - 48, y0, x1, y0 + 76)
        pill(frame, box, (255, 214, 10, int(240 * a)), 24)
        ImageDraw.Draw(frame).text((box[0] + 24, y0 + 12), badge_text, font=face, fill=(18, 22, 26, int(255 * a)))

    def draw_title(frame, to):
        found = next(((t, n) for t, n in chapters if t <= to < t + TITLE), None)
        if found is None:
            return
        title_t, n = found
        a = fade(to, title_t, 0.5, title_t + TITLE)
        small, big = font(28, True), font(54, True)
        d = ImageDraw.Draw(frame)
        text = spec['chapters'][n - 1][LANG]
        width = max(d.textlength(text, font=big), d.textlength(f'FILTERMATE 5 · {n}/{len(spec["chapters"])}', font=small))
        box = (48, 48, 48 + width + 64, 48 + 130)
        pill(frame, box, (14, 20, 24, int(225 * a)), 22)
        d = ImageDraw.Draw(frame)
        d.text((80, 62), f'FILTERMATE 5 · {n}/{len(spec["chapters"])}', font=small, fill=(255, 214, 10, int(255 * a)))
        d.text((80, 100), text, font=big, fill=(255, 255, 255, int(255 * a)))

    def draw_caption(frame, to):
        for start, key in says:
            end = start + voice[key] + 0.3
            if start - 0.1 <= to < end:
                a = fade(to, start - 0.1, 0.25, end, 0.3)
                face = font(40)
                d = ImageDraw.Draw(frame)
                lines = wrap(d, spec['lines'][key][LANG], face, 1500)
                height = len(lines) * 54 + 36
                box = (160, OUT_H - 56 - height, OUT_W - 160, OUT_H - 56)
                pill(frame, box, (10, 14, 18, int(215 * a)), 22)
                d = ImageDraw.Draw(frame)
                for n, line in enumerate(lines):
                    w = d.textlength(line, font=face)
                    d.text(((OUT_W - w) / 2, box[1] + 18 + n * 54), line, font=face, fill=(255, 255, 255, int(255 * a)))
                return

    def draw_card(frame, to):
        a = fade(to, duration - 0.1, 0.6)
        if a <= 0:
            return
        over = Image.new('RGBA', frame.size, (12, 17, 21, int(232 * a)))
        frame.alpha_composite(over)
        d = ImageDraw.Draw(frame)
        for text, face, y, fill in (('FilterMate 5', font(120, True), 360, (255, 255, 255)),
                                    (narration['outro'][LANG], font(40), 540, (255, 214, 10)),
                                    (narration['credits'][LANG], font(28), OUT_H - 110, (170, 180, 186))):
            w = d.textlength(text, font=face)
            d.text(((OUT_W - w) / 2, y), text, font=face, fill=fill + (int(255 * a),))

    def make_cover():
        """The hook over the best result, centred so that any crop of the thumbnail keeps it readable."""
        text = spec['cover']
        counts = next((e['counts'] for e in sorted(events, key=lambda e: -e['t'])
                       if e['kind'] == 'badge' and e.get('counts')), {})
        shot = min(results) if results else None
        frame = compose(results[shot] if shot else duration / 2)
        frame = frame.filter(ImageFilter.GaussianBlur(3))
        frame.alpha_composite(Image.new('RGBA', frame.size, (8, 12, 16, 120)))
        d = ImageDraw.Draw(frame)
        kicker, big, sub_face = font(44, True), font(118, True), font(52)
        lines = wrap(d, text['headline'][LANG].format_map(counts), big, 1560)
        block = 60 + len(lines) * 138 + 30 + 66
        y = (OUT_H - block) / 2
        w = d.textlength(text['kicker'][LANG], font=kicker)
        pill(frame, ((OUT_W - w) / 2 - 36, y - 6, (OUT_W + w) / 2 + 36, y + 62), (255, 214, 10, 255), 22)
        d = ImageDraw.Draw(frame)
        d.text(((OUT_W - w) / 2, y + 2), text['kicker'][LANG], font=kicker, fill=(18, 22, 26, 255))
        y += 96
        for line in lines:
            w = d.textlength(line, font=big)
            for dx, dy in ((4, 5), (-2, 5), (4, -2)):  # a short shadow keeps it readable on any map
                d.text(((OUT_W - w) / 2 + dx, y + dy), line, font=big, fill=(0, 0, 0, 200))
            d.text(((OUT_W - w) / 2, y), line, font=big, fill=(255, 255, 255, 255))
            y += 138
        y += 30
        w = d.textlength(text['sub'][LANG], font=sub_face)
        d.text(((OUT_W - w) / 2, y), text['sub'][LANG], font=sub_face, fill=(255, 214, 10, 255))
        return frame.convert('RGB')

    def overlay(frame, to, captions=True):
        draw_badge(frame, to)
        if captions:
            draw_title(frame, to)
            draw_caption(frame, to)
            draw_card(frame, to)
        return frame

    site = os.path.join(ROOT, 'site')
    os.makedirs(site, exist_ok=True)
    silent = os.path.join(site, f'{clip}-{LANG}.silent.mp4')
    cmd = [FFMPEG, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OUT_W}x{OUT_H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', os.environ.get('FM_CRF', '18'),
           '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', silent]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    thumbs, every = [], max(total / 16, 0.5)
    cover = make_cover() if COVER > 0 else None
    n_cover = int(COVER * FPS) if cover else 0
    if cover:
        cover.save(os.path.join(site, f'{clip}-{LANG}-cover.jpg'), quality=94)
        cover.crop((0, (OUT_H - OUT_W * 627 // 1200) // 2, OUT_W, (OUT_H + OUT_W * 627 // 1200) // 2)).resize(
            (1200, 627), Image.Resampling.LANCZOS).save(os.path.join(site, f'{clip}-{LANG}-cover-link.jpg'), quality=94)
    for n in range(n_cover):  # frame 0 is the cover itself, untouched: that is what LinkedIn shows
        k = min(max((n_cover - n) / (0.25 * FPS), 0.0), 1.0)
        enc.stdin.write((cover if k >= 1 else Image.blend(Image.new('RGB', cover.size, (0, 0, 0)), cover, k)).tobytes())
    for n in range(n_out):
        to = n / FPS
        frame = overlay(compose(min(to, duration - 0.02)), to)
        black = max(fade(to, 0.0, 0.5), 0.0)
        out = frame.convert('RGB')
        if black < 1:
            out = Image.blend(Image.new('RGB', out.size, (0, 0, 0)), out, black)
        tail = min(max((total - to) / 0.5, 0.0), 1.0)
        if tail < 1:
            out = Image.blend(Image.new('RGB', out.size, (0, 0, 0)), out, tail)
        if len(thumbs) < 16 and to >= len(thumbs) * every:
            thumbs.append((to, out.resize((400, 225), Image.Resampling.BILINEAR)))
        enc.stdin.write(out.tobytes())
    enc.stdin.close()
    enc.wait()

    # the result of the scenario, with its badge, and the same moment on the whole recorded screen
    for n, rt in sorted(results.items()):
        overlay(compose(rt), rt, captions=False).convert('RGB').save(
            os.path.join(site, f'{clip}-{LANG}-result{n}.jpg'), quality=94)
        source(clock.src(rt)).save(os.path.join(site, f'{clip}-result{n}-fullscreen.jpg'), quality=94)

    # voice-over (and the music bed, when there is one) mixed on the picture
    inputs, filters, labels = [], [], []
    for start, key in ([] if ENGINE == 'none' else says):
        inputs += ['-i', os.path.join(voice_dir, f'{clip}-{key}.mp3')]
        ms = int((start + (n_cover / FPS)) * 1000)
        filters.append(f'[{len(labels) + 1}:a]adelay={ms}|{ms},volume=1.0[v{len(labels)}]')
        labels.append(f'[v{len(labels)}]')
    bed = os.path.join(ROOT, 'music', 'bed.mp3')
    if ENGINE != 'none' and os.path.exists(bed):
        inputs += ['-stream_loop', '-1', '-i', bed]
        filters.append(f'[{len(labels) + 1}:a]volume=0.14,afade=t=in:d=1.5,afade=t=out:st={total + n_cover / FPS - 2.5:.2f}:d=2.5[bed]')
        labels.append('[bed]')
    final = os.path.join(site, f'{clip}-{LANG}' + ('-silent' if ENGINE == 'none' else '') + '.mp4')
    if labels:
        filters.append(''.join(labels) + f'amix=inputs={len(labels)}:normalize=0:duration=longest,'
                       f'alimiter=limit=0.95,apad[a]')
        subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', silent] + inputs + [
            '-filter_complex', ';'.join(filters), '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            '-t', f'{total + n_cover / FPS:.2f}', '-movflags', '+faststart', final], check=True)
        os.remove(silent)
    else:
        os.replace(silent, final)

    sheet = Image.new('RGB', (4 * 400, 4 * 245), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for k, (to, im) in enumerate(thumbs):
        x, y = (k % 4) * 400, (k // 4) * 245
        sheet.paste(im, (x, y))
        d.text((x + 6, y + 228), f'{to:5.1f} s', fill=(230, 230, 230))
    sheet.save(os.path.join(site, f'{clip}-{LANG}-sheet.jpg'), quality=85)
    print(f'{clip} [{LANG}]: {total + n_cover / FPS:.1f} s, {os.path.getsize(final) / 1e6:.1f} MB, voice lines {len(says)}')


if __name__ == '__main__':
    for name in sys.argv[1:]:
        render(name)
