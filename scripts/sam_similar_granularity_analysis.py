"""Decide by the rule fixed before the run (see sam_similar_granularity.py): the mask nearest the clicked object's size.

    uvx --with shapely --with numpy python scripts/sam_similar_granularity_analysis.py granularity.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sam_similar_candidates_analysis as analysis  # noqa: E402


def as_candidates(path: str, choice: str) -> list:
    """The rows of the bench in the form of sam_similar_candidates.py, each candidate drawn with ``choice``."""
    rows = json.load(open(path, encoding='utf-8'))
    for row in rows:
        row['candidates'] = [{'source': c['source'], 'rank': c['rank'], 'similarity': 1.0, 'x': c['x'], 'y': c['y'],
                              'wkt': c[choice]['wkt'], 'appearance': c[choice]['appearance'], 'features': None}
                             for c in row['candidates']]
    return rows


def main() -> None:
    path = sys.argv[1]
    results = {}
    for choice in ('best', 'sized'):
        out = path + f'.{choice}.json'
        json.dump(as_candidates(path, choice), open(out, 'w', encoding='utf-8'))
        rows = analysis.load(out)
        make = lambda row: analysis.colour_prompts(row) + analysis.feature_prompts(row, 0.0, 10)  # noqa: E731
        sets = sorted({r['set'] for r in rows})
        results[choice] = {name: analysis.summary([r for r in rows if r['set'] == name], make,
                                                  analysis.BASELINE_APPEARANCE) for name in sets}
    raw = json.load(open(path, encoding='utf-8'))
    same = sum(c['same_mask'] for r in raw for c in r['candidates'])
    total = sum(len(r['candidates']) for r in raw)
    print(f"candidates drawn with the same mask either way: {same} of {total}")
    for name in sets:
        print(f"set {name}: best score {results['best'][name]}\n       nearest size {results['sized'][name]}")
    judged = 'C' if 'C' in sets else 'B'  # the confirmation decides when it is there
    base, sized = results['best'][judged], results['sized'][judged]
    print(f"judged on set {judged}")
    adopted = ((sized['recall'] >= base['recall'] + 0.10 and sized['precision'] >= base['precision'] - 0.05)
               or (sized['precision'] >= base['precision'] + 0.10 and sized['recall'] >= base['recall'] - 0.05))
    print('ADOPTED' if adopted else 'not adopted')


if __name__ == '__main__':
    main()
