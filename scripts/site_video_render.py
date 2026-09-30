# -*- coding: utf-8 -*-
"""Edit a scripts/site_videos.py recording into a website background video.

Usage (the Python of QGIS has Pillow; ffmpeg must be on PATH or in FM_FFMPEG)::

    python site_video_render.py hero [more clips...]

Reads ``<FM_VIDEO_OUT>/<clip>/meta.json`` and ``frames/*.jpg`` and writes, in
``<FM_VIDEO_OUT>/site/``:

* ``<clip>.mp4``: 1280x720 (FM_SIZE), 25 fps, H.264, no audio, loops seamlessly (the
  last second cross-fades into the first frame);
* ``<clip>.webp``: poster frame (``mark`` event named ``poster``, else the last
  shot before the closing wide shot);
* ``<clip>-sheet.jpg``: contact sheet to review the edit without a player.

The edit follows the events logged during the recording: the virtual camera
eases between the framed regions (log-space zoom, cubic easing) and drifts
slowly while holding; a drawn cursor travels to each widget and ripples on
each click; ``speed`` events fast-forward the waits.
"""
import bisect
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.environ.get('FM_VIDEO_OUT', r'C:\Users\Simon\AppData\Local\Temp\fm_video')
FFMPEG = os.environ.get('FM_FFMPEG', 'ffmpeg')
OUT_W, OUT_H = (int(v) for v in os.environ.get('FM_SIZE', '1280x720').split('x'))
FPS = 25
LOOP = 1.2          # seconds of cross-fade back into the first frame
MAX_ZOOM = 2.6      # smallest framed width = window width / MAX_ZOOM
MOVE = 0.8          # longest cursor travel, seconds
CRF = os.environ.get('FM_CRF', '30')


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


# ------------------------------------------------------------------ time
class Clock:
    """Maps recording time to output time through the speed events."""

    def __init__(self, events, end):
        self.knots = [(0.0, 1.0)]
        for e in events:
            if e['kind'] == 'speed':
                self.knots.append((e['t'], float(e['factor'])))
        self.knots.sort()
        self.end = end
        # cumulative output time at each knot
        self.cum = [0.0]
        for (t0, f0), (t1, _f1) in zip(self.knots, self.knots[1:]):
            self.cum.append(self.cum[-1] + (t1 - t0) / f0)

    def out(self, ts):
        i = bisect.bisect_right([k[0] for k in self.knots], ts) - 1
        t0, f0 = self.knots[i]
        return self.cum[i] + (ts - t0) / f0

    def src(self, to):
        i = bisect.bisect_right(self.cum, to) - 1
        t0, f0 = self.knots[i]
        return t0 + (to - self.cum[i]) * f0

    @property
    def duration(self):
        return self.out(self.end)


# ------------------------------------------------------------------ camera
class Camera:
    """Camera state (cx, cy, w) in logical window pixels, fixed 16:9 aspect."""

    def __init__(self, events, clock, size):
        self.W, self.H = size
        self.aspect = OUT_W / OUT_H
        self.shots = []
        for e in events:
            if e['kind'] == 'camera':
                self.shots.append((clock.out(e['t']), self.fit(e['rect']), float(e['dur']), float(e['drift'])))
        self.shots.sort(key=lambda s: s[0])
        full = self.fit([0, 0, self.W, self.H])
        self.starts = []
        state = full
        for i, shot in enumerate(self.shots):
            if i:
                state = self._during(i - 1, shot[0])
            self.starts.append(state)
        self.full = full

    def fit(self, rect):
        x, y, w, h = rect
        cx, cy = x + w / 2, y + h / 2
        w = max(w, h * self.aspect, self.W / MAX_ZOOM)
        w = min(w, self.W, self.H * self.aspect)
        return self.clamp((cx, cy, w))

    def clamp(self, c):
        cx, cy, w = c
        h = w / self.aspect
        cx = min(max(cx, w / 2), self.W - w / 2)
        cy = min(max(cy, h / 2), self.H - h / 2)
        return (cx, cy, w)

    def _during(self, i, to):
        t0, target, dur, drift = self.shots[i]
        start = self.starts[i]
        u = ease((to - t0) / dur) if dur > 0 else 1.0
        cx = start[0] + (target[0] - start[0]) * u
        cy = start[1] + (target[1] - start[1]) * u
        w = math.exp(math.log(start[2]) + (math.log(target[2]) - math.log(start[2])) * u)
        hold = to - t0 - dur
        if hold > 0 and drift != 1.0:
            w /= drift ** (hold / 10.0)
        return self.clamp((cx, cy, w))

    def at(self, to):
        i = bisect.bisect_right([s[0] for s in self.shots], to) - 1
        if i < 0:
            return self.full
        return self._during(i, to)


# ------------------------------------------------------------------ cursor
class Cursor:
    """Cursor path: each point/click is a target; travel time grows with the distance."""

    def __init__(self, events, clock):
        raw = sorted((clock.out(e['t']), e['kind'], e['x'], e['y'])
                     for e in events if e['kind'] in ('point', 'click'))
        self.clicks = [(t, x, y) for t, k, x, y in raw if k == 'click']
        self.moves = []    # (depart, arrive, x, y)
        last = None
        for t, k, x, y in raw:
            if last == (x, y):
                continue
            dist = math.hypot(x - last[0], y - last[1]) if last else 600
            travel = min(max(0.22 + dist / 1400, 0.3), MOVE)
            if k == 'point':
                self.moves.append((t, t + travel, x, y))
            else:  # a click nobody pointed at first: arrive right on time
                self.moves.append((max(t - travel, 0.0), t, x, y))
            last = (x, y)
        self.moves.sort()
        self.departs = [m[0] for m in self.moves]
        self.activity = sorted([m[1] for m in self.moves] + [c[0] for c in self.clicks])

    def at(self, to, entry):
        """(x, y, alpha) or None; entry is where the cursor comes from on its first move."""
        i = bisect.bisect_right(self.departs, to) - 1
        if i < 0:
            return None
        pos = entry
        for k in range(i + 1):
            d, a, x, y = self.moves[k]
            until = min(self.moves[k + 1][0], to) if k < i else to
            u = ease((until - d) / (a - d)) if a > d else 1.0
            pos = (pos[0] + (x - pos[0]) * u, pos[1] + (y - pos[1]) * u)
        # fade out after 2.5 s without activity, fade in 0.3 s before the next move
        j = bisect.bisect_right(self.activity, to) - 1
        idle = to - self.activity[j] if j >= 0 else 0
        alpha = 1.0 if idle < 2.5 else max(0.0, 1 - (idle - 2.5) / 0.5)
        if i + 1 < len(self.moves) and self.moves[i + 1][0] - to < 0.3:
            alpha = max(alpha, 1 - (self.moves[i + 1][0] - to) / 0.3)
        return (pos[0], pos[1], alpha)


def cursor_sprite(height=30):
    """Arrow pointer, white with a dark outline and a soft shadow, supersampled."""
    s = 8
    pts = [(0, 0), (0, 17), (4.2, 13.2), (7.0, 19.6), (9.6, 18.5), (6.9, 12.2), (12.2, 12.2)]
    scale = height * s / 20.0
    pad = 6 * s
    W, H = int(13 * scale + 2 * pad), int(21 * scale + 2 * pad)
    shadow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(shadow).polygon([(pad + x * scale + 2 * s, pad + y * scale + 3 * s) for x, y in pts], fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(3 * s))
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    img.putalpha(shadow)
    img = Image.composite(Image.new('RGBA', (W, H), (0, 0, 0, 255)), img, shadow)
    img.putalpha(shadow)
    d = ImageDraw.Draw(img)
    poly = [(pad + x * scale, pad + y * scale) for x, y in pts]
    d.polygon(poly, fill=(255, 255, 255, 255), outline=(20, 24, 28, 255), width=int(1.5 * s))
    small = img.resize((W // s, H // s), Image.Resampling.LANCZOS)
    return small, (pad // s, pad // s)


def draw_ripple(frame, x, y, age):
    """Expanding ring on a click, 0.55 s long."""
    if not 0 <= age < 0.55:
        return
    u = age / 0.55
    r = 7 + 26 * ease(u)
    a = int(255 * (1 - u))
    over = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 225, 77, a), width=4)
    d.ellipse([x - r - 2, y - r - 2, x + r + 2, y + r + 2], outline=(20, 24, 28, a // 2), width=1)
    frame.alpha_composite(over)


# ------------------------------------------------------------------ render
def close_gaps(times, events, longest=1.0, keep=0.4):
    """Shrink every hole of more than `longest` s between two frames to `keep` s.

    A hole means QGIS blocked its main thread (no frame could be grabbed): the
    picture did not change, so the edit just cuts the wait.
    """
    cuts = []  # (time where the hole ends, seconds removed)
    for a, b in zip(times, times[1:]):
        if b - a > longest:
            cuts.append((b, b - a - keep))

    def shift(t):
        return t - sum(removed for end, removed in cuts if end <= t + 1e-9)

    if cuts:
        print(f'  closing {len(cuts)} hole(s): ' + ', '.join(f'{r + keep:.1f} s' for _e, r in cuts))
    moved = []
    for e in events:
        e = dict(e)
        # an event logged inside a hole happened when the frames resumed
        for end, removed in cuts:
            if end - removed - keep < e['t'] < end:
                e['t'] = end
        e['t'] = shift(e['t'])
        moved.append(e)
    return [shift(t) for t in times], moved


def render(clip):
    base = os.path.join(ROOT, clip)
    with open(os.path.join(base, 'meta.json'), encoding='utf-8') as f:
        meta = json.load(f)
    times, events = close_gaps(meta['frames'], meta['events'])
    dpr = meta['dpr']
    size = tuple(meta['size'])
    clock = Clock(events, times[-1])
    camera = Camera(events, clock, size)
    cursor = Cursor(events, clock)
    sprite, hotspot = cursor_sprite()
    duration = clock.duration
    n_out = int(duration * FPS)
    entry = (size[0] * 0.55, size[1] * 0.75)
    # poster: a 'poster' mark, else the result on the map just before the closing wide shot
    cams = [clock.out(e['t']) for e in events if e['kind'] == 'camera']
    poster_t = next((clock.out(e['t']) for e in events if e['kind'] == 'mark' and e.get('name') == 'poster'),
                    cams[-1] - 0.3 if len(cams) > 1 else duration * 0.7)

    site = os.path.join(ROOT, 'site')
    os.makedirs(site, exist_ok=True)
    mp4 = os.path.join(site, f'{clip}.mp4')
    cmd = [FFMPEG, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{OUT_W}x{OUT_H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', CRF, '-tune', 'animation',
           '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', mp4]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    cache = {}

    def source(ts):
        i = max(bisect.bisect_right(times, ts) - 1, 0)
        if i not in cache:
            cache.clear()
            cache[i] = Image.open(os.path.join(base, 'frames', f'{i:06d}.jpg')).convert('RGB')
        return cache[i]

    def compose(to):
        cx, cy, w = camera.at(to)
        h = w / (OUT_W / OUT_H)
        box = ((cx - w / 2) * dpr, (cy - h / 2) * dpr, (cx + w / 2) * dpr, (cy + h / 2) * dpr)
        frame = source(clock.src(to)).resize((OUT_W, OUT_H), Image.Resampling.BICUBIC, box=box).convert('RGBA')
        k = OUT_W / (box[2] - box[0])
        for tc, x, y in cursor.clicks:
            draw_ripple(frame, (x * dpr - box[0]) * k, (y * dpr - box[1]) * k, to - tc)
        c = cursor.at(to, entry)
        if c and c[2] > 0:
            px, py = (c[0] * dpr - box[0]) * k, (c[1] * dpr - box[1]) * k
            press = any(0 <= to - tc < 0.14 for tc, _x, _y in cursor.clicks)
            spr = sprite if not press else sprite.resize((int(sprite.width * 0.88), int(sprite.height * 0.88)))
            if c[2] < 1:
                spr = spr.copy()
                spr.putalpha(spr.getchannel('A').point(lambda v: int(v * c[2])))
            frame.alpha_composite(spr, (int(px - hotspot[0]), int(py - hotspot[1])))
        return frame.convert('RGB')

    first = compose(0.0)
    poster = None
    sheet_every = max(duration / 16, 0.5)
    thumbs = []
    for n in range(n_out):
        to = n / FPS
        frame = first if n == 0 else compose(to)
        if to > duration - LOOP:
            frame = Image.blend(frame, first, ease((to - (duration - LOOP)) / LOOP))
        if poster is None and to >= poster_t:
            poster = frame.copy()
        if len(thumbs) < 16 and to >= len(thumbs) * sheet_every:
            thumbs.append((to, frame.resize((400, 225), Image.Resampling.BILINEAR)))
        enc.stdin.write(frame.tobytes())
    enc.stdin.close()
    enc.wait()

    # the Pillow of QGIS has no WebP encoder: let ffmpeg convert the poster
    png = os.path.join(site, f'{clip}-poster.png')
    (poster or first).save(png)
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', png, '-c:v', 'libwebp', '-quality', '70',
                    os.path.join(site, f'{clip}.webp')], check=True)
    os.remove(png)
    sheet = Image.new('RGB', (4 * 400, 4 * 245), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for k, (to, im) in enumerate(thumbs):
        x, y = (k % 4) * 400, (k // 4) * 245
        sheet.paste(im, (x, y))
        d.text((x + 6, y + 228), f'{to:5.1f} s', fill=(230, 230, 230))
    sheet.save(os.path.join(site, f'{clip}-sheet.jpg'), quality=85)
    mb = os.path.getsize(mp4) / 1e6
    print(f'{clip}: {duration:.1f} s, {n_out} frames, {mb:.2f} MB, {len(times)} source frames')


if __name__ == '__main__':
    for name in sys.argv[1:]:
        render(name)
