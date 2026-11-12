"""Cost of the window planning of filtermate:segment_from_features (segmentation.assign_windows / plan_prompts).

Written 2026-11-12 for the audit of the segmentation: the greedy grouping compared every point with every window
opened before it. Runs without QGIS (qgis.* stubbed): argv = plugin root, then point counts (1000 4000 20000).

Sparse points: random points over a raster of 100 km a side, native cell 0.25 m, windows of 1024 pixels (256 m),
nearly one window per point, the worst case of the grouping. The planning is also compared with the quadratic one
of origin/main 9ba0c922 (copied below) on sparse points, clusters, an edge of the raster and a regular grid: same
windows, same members, same order.

Result, 2026-11-12 (WSL2, Python 3.12), before -> after the windows indexed on a grid of their side:

     1000 sparse points: assign_windows   0.84 s ->  0.03 s
     4000 sparse points: assign_windows   8.3 s  ->  0.15 s
    20000 sparse points: assign_windows 148 s    ->  0.79 s

and the same plan as the quadratic one in every case compared.
"""
import importlib.util
import random
import sys
import time
import types
from unittest.mock import MagicMock

root = sys.argv[1]
counts = [int(value) for value in sys.argv[2:]] or [1000, 4000, 20000]
for name in ('qgis', 'qgis.core', 'qgis.gui', 'qgis.PyQt', 'qgis.PyQt.QtCore', 'qgis.PyQt.QtGui'):
    sys.modules[name] = MagicMock()
package = types.ModuleType('fm_bench')
package.__path__ = [root]
sys.modules['fm_bench'] = package
spec = importlib.util.spec_from_file_location('fm_bench.segmentation', f'{root}/adapters/qgis/coverage_layers/segmentation.py')
segmentation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(segmentation)


def quadratic(points, raster, cell, size, margin_pixels=128):
    """assign_windows of origin/main 9ba0c922, the reference."""
    margin = margin_pixels * cell
    windows = []
    for index, (x, y) in enumerate(points):
        for window, members in windows:
            if (window.x_min + margin <= x <= window.x_min + window.side - margin
                    and window.y_max - window.side + margin <= y <= window.y_max - margin):
                members.append(index)
                break
        else:
            window = segmentation.window_at(x, y, raster, cell, size)
            same = [members for other, members in windows if (other.x_min, other.y_max) == (window.x_min, window.y_max)]
            if same:
                same[0].append(index)
            else:
                windows.append((window, [index]))
    return windows


def plan(windows):
    return [(window.x_min, window.y_max, window.cell, members) for window, members in windows]


raster = (0.0, 0.0, 100000.0, 100000.0)
random.seed(20261112)
for count in counts:
    points = [(random.uniform(0, 100000.0), random.uniform(0, 100000.0)) for _ in range(count)]
    begin = time.perf_counter()
    planned = segmentation.assign_windows(points, raster, 0.25, 1024)
    print(f'{count:>6} sparse points: assign_windows {time.perf_counter() - begin:7.2f} s, {len(planned)} windows', flush=True)
    if count <= 4000:
        print(f'        same plan as the quadratic one: {plan(planned) == plan(quadratic(points, raster, 0.25, 1024))}',
              flush=True)

clusters = []
for _ in range(60):
    cx, cy = random.uniform(0, 100000.0), random.uniform(0, 100000.0)
    clusters += [(cx + random.gauss(0, 150.0), cy + random.gauss(0, 150.0)) for _ in range(50)]
edge = [(99990.0 - random.uniform(0, 300.0), random.uniform(0, 100000.0)) for _ in range(500)]
grid = [(float(x * 64), float(y * 64)) for x in range(40) for y in range(40)]
for label, points, margin in (('clusters', clusters, 128), ('edge of the raster', edge, 128),
                              ('clusters, margin of 500 pixels', clusters, 500), ('grid of 64 m', grid, 128),
                              ('grid of 64 m, margin 0', grid, 0)):
    points = [(min(max(x, 0.0), 100000.0), min(max(y, 0.0), 100000.0)) for x, y in points]
    planned = segmentation.assign_windows(points, raster, 0.25, 1024, margin)
    same = plan(planned) == plan(quadratic(points, raster, 0.25, 1024, margin))
    print(f'{label}: {len(points)} points, {len(planned)} windows, same plan as the quadratic one: {same}', flush=True)
