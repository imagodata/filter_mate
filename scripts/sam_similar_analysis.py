"""Thresholds chosen on set A, judged on set B, by the rule fixed before the run (see similar_features.py)."""
import json
import statistics
import sys

rows = json.load(open(sys.argv[1], encoding='utf-8'))


def metrics(row, score_min, colour_max):
    kept = [i for i, o in enumerate(row['objects']) if o['score'] >= score_min and o['colour'] <= colour_max]
    precision = sum(1 for i in kept if row['objects'][i]['match']) / len(kept) if kept else None
    matched = {t for t, i in row['truth_matched_by'] if i in kept}
    recall = len(matched) / row['truth'] if row['truth'] else None
    return precision, recall, len(kept)


def medians(subset, score_min, colour_max):
    values = [metrics(row, score_min, colour_max) for row in subset]
    precision = [p for p, _r, _n in values if p is not None]
    recall = [r for _p, r, _n in values if r is not None]
    return (statistics.median(precision) if precision else 0.0, statistics.median(recall) if recall else 0.0,
            sum(n for _p, _r, n in values))


a = [row for row in rows if row['set'] == 'A']
b = [row for row in rows if row['set'] == 'B']
base_a, base_b = medians(a, 0.0, 1e9), medians(b, 0.0, 1e9)
print(f'baseline A: precision {base_a[0]:.3f} recall {base_a[1]:.3f} objects {base_a[2]}')
print(f'baseline B: precision {base_b[0]:.3f} recall {base_b[1]:.3f} objects {base_b[2]}')
best = None
for score_min in [x / 100 for x in range(0, 100, 2)]:
    for colour_max in list(range(5, 125, 5)) + [1e9]:
        precision, recall, count = medians(a, score_min, colour_max)
        if recall < base_a[1] - 0.05:
            continue
        key = (round(precision, 4), -score_min, colour_max)  # the loosest of the best
        if best is None or key > best[0]:
            best = (key, score_min, colour_max, precision, recall, count)
_key, score_min, colour_max, pa, ra, na = best
pb, rb, nb = medians(b, score_min, colour_max)
print(f'chosen on A: score >= {score_min}, colour <= {colour_max} -> A precision {pa:.3f} recall {ra:.3f} objects {na}')
print(f'judged on B: precision {pb:.3f} (baseline {base_b[0]:.3f}, gain {pb - base_b[0]:+.3f}) '
      f'recall {rb:.3f} (baseline {base_b[1]:.3f}, change {rb - base_b[1]:+.3f}) objects {nb}')
adopted = pb - base_b[0] >= 0.10 and rb - base_b[1] >= -0.05
print('ADOPTED' if adopted else 'NOT ADOPTED')
matched = [o for row in rows for o in row['objects'] if o['match']]
wrong = [o for row in rows for o in row['objects'] if not o['match']]
for name, objects in (('buildings', matched), ('not buildings', wrong)):
    if objects:
        print(f'{name}: {len(objects)} objects, median score {statistics.median(o["score"] for o in objects):.3f}, '
              f'median colour distance {statistics.median(o["colour"] for o in objects):.1f}')
