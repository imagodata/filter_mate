"""Read each take of the site before it is published: the layout at its end and the counts the pages quote.

    python3 scripts/site_takes_check.py <work folder> <clip> [<clip> ...]

``<work folder>`` is the FM_WORK of scripts/site_videos_headless.sh (default ~/dev/fm-video): the script reads
``out/<clip>/capture.log``, ``out/<clip>/meta.json`` and ``out/site/<clip>.mp4`` / ``.webp``. One line per take,
exit 1 when one fails. A take passes when:

* its dock is 380 px wide and in one piece (no section apart at its end);
* at most 16 px are left under the rows of the section its dock shows (14 px is the margin of the section);
* its theme is the one its name asks (``<clip>-dark``);
* its video and its poster are newer than its recording;
* the counts logged at its end are the ones the pages quote (EXPECT below: change them with the pages).

Takes that set sections apart on purpose (panels, exploring-panel) end with every section back in the dock.
"""
import json
import os
import re
import sys

work, clips = sys.argv[1], sys.argv[2:]
EXPECT = {  # counts the pages of the site quote (stories.html, index.html), by layer, at the end of the take
    'noise': {'batiment': 2196, 'erp': 75}, 'buffer': {'batiment': 606, 'erp': 3, 'troncon_de_route': 420},
    'bridges': {'troncon_de_route': 708, 'construction_lineaire': 343}, 'brush': {'zone_de_vegetation': 57, 'haie': 46},
    'hero': {'batiment': 12380}, 'hamlets': {'zone_d_habitation': 22},
    'favorites': {'batiment': 2913, 'erp': 27, 'troncon_de_route': 1020},
    'compare': {'batiment': 983, 'erp': 18, 'troncon_de_route': 728},
    'processing': {'batiment': 22954, 'troncon_de_route': 173616},
    'slope': {'parcelle': 34}, 'heights': {'batiment': 119}, 'pruning': {'troncon_de_route': 82},
}
bad = 0
for clip in clips:
    scene = clip[:-5] if clip.endswith('-dark') else clip
    log = os.path.join(work, 'out', clip, 'capture.log')
    meta = os.path.join(work, 'out', clip, 'meta.json')
    notes = []
    try:
        text = open(log, encoding='utf-8').read()
        m = json.load(open(meta, encoding='utf-8'))
    except OSError as exc:
        print(f'{clip:16} MISSING {exc}')
        bad += 1
        continue
    theme_ok = m['theme'] == ('dark' if clip.endswith('-dark') else 'light')
    end = re.findall(r'layout at the end: window (\d+)x(\d+), dock (\d+)x(\d+), empty band (-?\d+), sections apart \((.*?)\)', text)
    if not end:
        notes.append('no layout line')
    else:
        w, h, dw, dh, band, apart = end[-1]
        if int(dw) != 380:
            notes.append(f'dock {dw} px')
        if int(band) > 16:
            notes.append(f'empty band {band} px')
        if apart.strip():
            notes.append(f'sections apart {apart}')
    counts = [json.loads(c.replace("'", '"')) for c in re.findall(r'counts (\{.*?\})', text)]
    want = EXPECT.get(scene)
    if want:
        last = {}
        for c in counts:
            last.update(c)
        diff = {k: (last.get(k), v) for k, v in want.items() if last.get(k) != v}
        if diff:
            notes.append(f'counts differ (got, expected): {diff}')
    if 'Traceback' in text:
        notes.append('Traceback in the log')
    if not theme_ok:
        notes.append(f"theme {m['theme']}")
    site = os.path.join(work, 'out', 'site')
    for ext in ('.mp4', '.webp'):
        f = os.path.join(site, clip + ext)
        if not os.path.exists(f) or os.path.getmtime(f) < os.path.getmtime(meta) - 1:
            notes.append(f'{ext} older than the take')
    dur = m['frames'][-1] if m['frames'] else 0
    size = end[-1][0] + 'x' + end[-1][1] if end else '?'
    print(f"{clip:16} {'OK  ' if not notes else 'FAIL'} window {size}, {dur:5.1f} s, {len(m['frames'])} frames" + ('' if not notes else '  <- ' + '; '.join(notes)))
    bad += bool(notes)
sys.exit(1 if bad else 0)
