# -*- coding: utf-8 -*-
"""Convert the story screenshots to the website formats.

Usage::

    python scripts/recipe_images.py <captures_dir> website/img/stories

Whole-window captures (1600 px wide) become WebP at quality 82, which keeps
the panel text readable at roughly a tenth of the PNG size; dialog and panel
captures (recap, manager, Processing dialog) stay PNG because their flat
colours compress well losslessly and their text must stay crisp.
Requires Pillow with WebP support.
"""
import os
import sys

from PIL import Image

KEEP_PNG = ('-recap', '-manager', '-dialog', '-menu', '-panel')


def convert(src_dir, dst_dir, quality=82):
    os.makedirs(dst_dir, exist_ok=True)
    total_in = total_out = 0
    for name in sorted(os.listdir(src_dir)):
        if not name.endswith('.png'):
            continue
        src = os.path.join(src_dir, name)
        total_in += os.path.getsize(src)
        stem = name[:-4]
        img = Image.open(src)
        if any(k in stem for k in KEEP_PNG):
            dst = os.path.join(dst_dir, name)
            img.convert('RGB').save(dst, 'PNG', optimize=True)
        else:
            dst = os.path.join(dst_dir, stem + '.webp')
            img.convert('RGB').save(dst, 'WEBP', quality=quality, method=6)
        total_out += os.path.getsize(dst)
        print(f'{name} -> {os.path.basename(dst)} {os.path.getsize(dst) // 1024} KB')
    print(f'total {total_in / 1e6:.1f} MB -> {total_out / 1e6:.1f} MB')


if __name__ == '__main__':
    convert(sys.argv[1], sys.argv[2])
