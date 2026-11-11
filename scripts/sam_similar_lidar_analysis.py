"""Would the LiDAR sort the SAM similar objects? Set A only, on the search the dock runs.

Explored 2026-11-11 on the first ten buildings (set A) only, before any rule: a filter would keep the proposals the
footprint of the LiDAR class of the clicked object (scripts/sam_similar_lidar.py) covers enough. Rule it would have
had to pass on set B, as the appearance filter: median precision +0.10, recall -0.05 at most.

Result: every clicked object lies on class 6 (buildings); the share of a proposal on the class 6 footprint has a
median of 0.96 for the right proposals (52) and 0.99 for the wrong ones (59): no threshold separates them (pooled
precision 0.47 to 0.49 at best). The wrong proposals overlap buildings with a wrong outline (a part of a roof, two
roofs in one); of the 59, 3 touch no BD TOPO building of the tile, 2 of them on class 6 (buildings missing from the
BD TOPO). Not taken to set B; not adopted.

    uvx --with shapely --with numpy python scripts/sam_similar_lidar_analysis.py candidates.json lidar.json
"""
import json
import statistics
import sys

from shapely import wkt as shapely_wkt

import sam_similar_candidates_analysis as base


def main():
    rows = [row for row in base.load(sys.argv[1]) if row['set'] == 'A']
    lidar = {(record['fid'], record['set']): record for record in json.load(open(sys.argv[2], encoding='utf-8'))}
    right, wrong = [], []
    for row in rows:
        footprint = shapely_wkt.loads(lidar[(row['fid'], row['set'])]['footprint_6']).buffer(0)
        prompts = base.colour_prompts(row) + base.feature_prompts(row, 0.3, 10)  # the search of the dock
        proposals, _drawn = base.replay(row, prompts, base.BASELINE_APPEARANCE)
        for candidate in proposals:
            geometry = candidate['_geometry']
            share = geometry.intersection(footprint).area / geometry.area if geometry.area else 0.0
            (right if base.matches(row, geometry) else wrong).append(share)
    print(f"right {len(right)} median share {statistics.median(right):.2f}, "
          f"wrong {len(wrong)} median share {statistics.median(wrong):.2f}")
    for threshold in (0.2, 0.4, 0.6, 0.8):
        kept_right = sum(1 for share in right if share >= threshold)
        kept_wrong = sum(1 for share in wrong if share >= threshold)
        print(f"t={threshold}: pooled precision {kept_right / max(1, kept_right + kept_wrong):.2f} "
              f"(all {len(right) / max(1, len(right) + len(wrong)):.2f})")


if __name__ == '__main__':
    main()
