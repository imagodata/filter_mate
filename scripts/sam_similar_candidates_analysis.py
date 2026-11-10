"""Decide by the rules fixed before the run (see sam_similar_candidates.py): feature candidates, and keep / reject re-ranking.

Replays SimilarObjectsTask for each variant on the objects SAM drew, with shapely (no QGIS):

    uvx --with shapely --with numpy python scripts/sam_similar_candidates_analysis.py candidates.json
"""
import json
import math
import statistics
import sys

import numpy as np
from shapely import wkt as shapely_wkt
from shapely.geometry import Point

RATIO = (0.5, 2.0)
SAME_OBJECT_IOU = 0.5
MATCH_IOU = 0.5
BASELINE_APPEARANCE = 0.68
COLOUR_LIMIT = 120
GRID_SIMILARITY = [round(0.30 + 0.05 * i, 2) for i in range(13)]  # 0.30 .. 0.90
GRID_COUNT = [10, 20, 40, 60, 80, 120, 200]
GRID_APPEARANCE = [None, 0.60, 0.64, 0.68, 0.72, 0.76, 0.80]
RERANK_FIRST = 3


def iou(first, second):
    try:
        union = first.union(second).area
        return first.intersection(second).area / union if union > 0 else 0.0
    except Exception:  # an invalid polygon: not the same object
        return 0.0


def compactness(geometry):
    area, perimeter = geometry.area, geometry.length
    return min(1.0, 4 * math.pi * area / (perimeter * perimeter)) if area > 0 and perimeter > 0 else 0.0


def load(path):
    rows = json.load(open(path, encoding='utf-8'))
    for row in rows:
        row['_buildings'] = [shapely_wkt.loads(text) for text in row['buildings']]
        row['_reference'] = shapely_wkt.loads(row['reference'])
        row['_clicked'] = shapely_wkt.loads(row['clicked']) if row.get('clicked') else None
        for candidate in row['candidates']:
            candidate['_geometry'] = shapely_wkt.loads(candidate['wkt']) if candidate['wkt'] else None
            if candidate['_geometry'] is not None and not candidate['_geometry'].is_valid:
                candidate['_geometry'] = candidate['_geometry'].buffer(0)
            candidate['_match'] = None
    return rows


def matches(row, geometry):
    """Indexes of the buildings (reference = -1) an object matches at IoU >= 0.5."""
    found = [index for index, building in enumerate(row['_buildings']) if iou(geometry, building) >= MATCH_IOU]
    return found + ([-1] if iou(geometry, row['_reference']) >= MATCH_IOU else [])


def similar(row, geometry):
    clicked = row['_clicked']
    area, shape = clicked.area, compactness(clicked)
    low, high = min(RATIO), max(RATIO)
    return area * low <= geometry.area <= area * high and shape * low <= compactness(geometry) <= min(1.0, shape * high)


def replay(row, prompts, appearance_min):
    """SimilarObjectsTask on these candidates, in this order: (proposals, prompts drawn)."""
    if row['_clicked'] is None:
        return [], 0
    kept, proposals, drawn = [row['_clicked']], [], 0
    for candidate in prompts:
        where = Point(candidate['x'], candidate['y'])
        if any(geometry.contains(where) for geometry in kept):
            continue
        drawn += 1
        geometry = candidate['_geometry']
        if geometry is None or geometry.is_empty or any(iou(geometry, other) >= SAME_OBJECT_IOU for other in kept):
            continue
        if not similar(row, geometry):
            continue
        kept.append(geometry)
        if appearance_min is None or candidate['appearance'] is None or candidate['appearance'] >= appearance_min:
            proposals.append(candidate)
    return proposals, drawn


def measure(row, proposals):
    """(precision, recall) of the proposals; None when undefined."""
    for candidate in proposals:
        if candidate['_match'] is None:
            candidate['_match'] = matches(row, candidate['_geometry'])
    precision = (sum(1 for c in proposals if c['_match']) / len(proposals)) if proposals else None
    truth = set(row['truth'])
    recalled = {index for c in proposals for index in c['_match'] if index in truth}
    recall = len(recalled) / len(truth) if truth else None
    return precision, recall


def colour_prompts(row):
    return [c for c in row['candidates'] if c['source'] == 'colour'][:COLOUR_LIMIT]


def feature_prompts(row, similarity_min, count):
    return [c for c in row['candidates'] if c['source'] == 'feature' and c['similarity'] >= similarity_min][:count]


def summary(rows, make, appearance_min):
    precisions, recalls, prompts = [], [], []
    for row in rows:
        proposals, drawn = replay(row, make(row), appearance_min)
        precision, recall = measure(row, proposals)
        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
        prompts.append(drawn)
    median = lambda values: statistics.median(values) if values else 0.0  # noqa: E731
    return {'precision': round(median(precisions), 3), 'recall': round(median(recalls), 3),
            'prompts': median(prompts), 'searches': len(rows)}


def variants():
    yield 'colour', None, None, lambda row: colour_prompts(row)
    for similarity_min in GRID_SIMILARITY:
        for count in GRID_COUNT:
            yield 'feature', similarity_min, count, \
                lambda row, s=similarity_min, n=count: feature_prompts(row, s, n)
            yield 'union', similarity_min, count, \
                lambda row, s=similarity_min, n=count: colour_prompts(row) + feature_prompts(row, s, n)


def decide_candidates(a, b):
    base_a = summary(a, colour_prompts, BASELINE_APPEARANCE)
    base_b = summary(b, colour_prompts, BASELINE_APPEARANCE)
    print(f"baseline A {base_a}\nbaseline B {base_b}")
    for kind in ('colour', 'feature', 'union'):
        best = None
        for name, similarity_min, count, make in variants():
            if name != kind:
                continue
            for appearance_min in GRID_APPEARANCE:
                result = summary(a, make, appearance_min)
                if result['precision'] < base_a['precision'] - 0.05:
                    continue
                key = (result['recall'], -result['prompts'])
                if best is None or key > best[0]:
                    best = (key, similarity_min, count, appearance_min, make, result)
        if best is None:
            print(f"{kind}: no setting keeps the precision on A")
            continue
        _key, similarity_min, count, appearance_min, make, on_a = best
        on_b = summary(b, make, appearance_min)
        adopted = (on_b['recall'] >= base_b['recall'] + 0.10 and on_b['precision'] >= base_b['precision'] - 0.05
                   and on_b['prompts'] <= 2 * max(base_b['prompts'], 1))
        print(f"{kind}: s={similarity_min} N={count} a={appearance_min}\n  A {on_a}\n  B {on_b}\n"
              f"  {'ADOPTED' if adopted else 'not adopted'}")


def rerank(row, proposals):
    """The proposals left once the first ones are kept or rejected by the oracle, and those hidden by the rule."""
    first, rest = proposals[:RERANK_FIRST], proposals[RERANK_FIRST:]
    for candidate in first:
        if candidate['_match'] is None:
            candidate['_match'] = matches(row, candidate['_geometry'])
    kept = [np.asarray(c['features']) for c in first if c['_match'] and c['features']]
    rejected = [np.asarray(c['features']) for c in first if not c['_match'] and c['features']]
    kept.append(np.asarray(row['clicked_features']))
    if not rejected:
        return rest, rest

    def unit(vectors):
        mean = np.mean(vectors, axis=0)
        norm = np.linalg.norm(mean)
        return mean / norm if norm else mean
    keep, reject = unit(kept), unit(rejected)
    shown = [c for c in rest if not c['features'] or float(np.dot(c['features'], keep)) >= float(np.dot(c['features'], reject))]
    return rest, shown


def decide_rerank(rows_by_set):
    for name, rows in rows_by_set.items():
        before_p, before_r, after_p, after_r = [], [], [], []
        for row in rows:
            proposals, _drawn = replay(row, colour_prompts(row), BASELINE_APPEARANCE)
            rest, shown = rerank(row, proposals)
            for values, subset in ((before_p, rest), (after_p, shown)):
                precision, _recall = measure(row, subset)
                if precision is not None:
                    values.append(precision)
            truth = set(row['truth'])
            reachable = {i for c in rest for i in (c['_match'] or []) if i in truth}
            if reachable:
                before_r.append(1.0)
                after_r.append(len({i for c in shown for i in (c['_match'] or []) if i in truth}) / len(reachable))
        median = lambda values: round(statistics.median(values), 3) if values else 0.0  # noqa: E731
        print(f"re-ranking {name}: precision {median(before_p)} -> {median(after_p)}, recall of the reachable "
              f"{median(before_r)} -> {median(after_r)} ({len(before_p)} searches with proposals left)")
        if name == 'B':
            adopted = median(after_p) >= median(before_p) + 0.10 and median(after_r) >= median(before_r) - 0.05
            print(f"  {'ADOPTED' if adopted else 'not adopted'}")


def main():
    rows = load(sys.argv[1])
    a = [row for row in rows if row['set'] == 'A']
    b = [row for row in rows if row['set'] == 'B']
    print(f"{len(a)} searches on A, {len(b)} on B; clicked IoU median "
          f"{statistics.median([r.get('clicked_iou', 0) for r in rows]):.3f}")
    print("candidates per search: colour", statistics.median([len(colour_prompts(r)) for r in rows]),
          "feature", statistics.median([sum(1 for c in r['candidates'] if c['source'] == 'feature') for r in rows]))
    decide_candidates(a, b)
    decide_rerank({'A': a, 'B': b})


if __name__ == '__main__':
    main()
