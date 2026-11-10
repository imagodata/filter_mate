"""Appearance threshold chosen on set A, judged on set B, by the rule fixed before the run (see appearance_features.py)."""
import json
import statistics
import sys

rows = json.load(open(sys.argv[1], encoding='utf-8'))


def metrics(row, threshold):
    kept = [i for i, o in enumerate(row['objects']) if o['appearance'] >= threshold]
    precision = sum(1 for i in kept if row['objects'][i]['match']) / len(kept) if kept else None
    matched = {t for t, i in row['truth_matched_by'] if i in kept}
    return precision, (len(matched) / row['truth'] if row['truth'] else None), len(kept)


def medians(subset, threshold):
    values = [metrics(row, threshold) for row in subset]
    precision = [p for p, _r, _n in values if p is not None]
    recall = [r for _p, r, _n in values if r is not None]
    return (statistics.median(precision) if precision else 0.0, statistics.median(recall) if recall else 0.0,
            sum(n for _p, _r, n in values))


a = [row for row in rows if row['set'] == 'A']
b = [row for row in rows if row['set'] == 'B']
base_a, base_b = medians(a, -2.0), medians(b, -2.0)
print(f'baseline A: precision {base_a[0]:.3f} recall {base_a[1]:.3f} objects {base_a[2]}')
print(f'baseline B: precision {base_b[0]:.3f} recall {base_b[1]:.3f} objects {base_b[2]}')
best = None
for step in range(-50, 100):
    threshold = step / 100
    precision, recall, count = medians(a, threshold)
    if recall < base_a[1] - 0.05:
        continue
    key = (round(precision, 4), -threshold)
    if best is None or key > best[0]:
        best = (key, threshold, precision, recall, count)
_key, threshold, pa, ra, na = best
pb, rb, nb = medians(b, threshold)
print(f'chosen on A: appearance >= {threshold:.2f} -> A precision {pa:.3f} recall {ra:.3f} objects {na}')
print(f'judged on B: precision {pb:.3f} (gain {pb - base_b[0]:+.3f}) recall {rb:.3f} (change {rb - base_b[1]:+.3f}) objects {nb}')
print('ADOPTED' if pb - base_b[0] >= 0.10 and rb - base_b[1] >= -0.05 else 'NOT ADOPTED')
for name, keep in (('buildings', True), ('not buildings', False)):
    values = [o['appearance'] for row in rows for o in row['objects'] if o['match'] is keep]
    if values:
        print(f'{name}: {len(values)} objects, appearance median {statistics.median(values):.3f}, '
              f'quartiles {statistics.quantiles(values, n=4)}')
