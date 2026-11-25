# -*- coding: utf-8 -*-
"""The rows "@" offers for the layers of the project (2026-11-24).

Pure: the panel shows the labels, and inserts what the model resolves. A name of one layer only is written as is;
a name several layers share is shown with its group, and the layer id is written, the only reference every tool
resolves to the layer meant (a bare name would reach the first layer of that name, or none).
"""
from __future__ import annotations

from collections import Counter
from typing import List, Sequence, Tuple


def mention_rows(entries: Sequence[Tuple[str, str, str]]) -> List[Tuple[str, str]]:
    """``[(label, text to insert)]`` for ``[(layer id, name, qualifier)]``: nameless layers stay out."""
    counts = Counter(name for _, name, _ in entries if name)
    rows = []
    for layer_id, name, qualifier in entries:
        if not name:
            continue
        if counts[name] > 1:
            tag = qualifier or ("…" + layer_id[-6:] if len(layer_id) > 6 else layer_id)
            rows.append((f"{name} ({tag})", layer_id))
        else:
            rows.append((name, name))
    return sorted(rows, key=lambda row: row[0].lower())
