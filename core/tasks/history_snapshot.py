# -*- coding: utf-8 -*-
"""The filter history of the layers of a task, taken before it runs and put back for refused filters.

2026-11-16: a task writes ``fm_subset_history`` in run(), before its subsets are applied on the main
thread: a filter adds an entry, an unfilter deletes the last one, a reset deletes them all. When the
provider then refuses the subset (the PostgreSQL server gone: 9 layers in the ticket of that day), the
layer keeps its previous filter while its history had moved: the next unfilter went one step too far
back, and a reset left a filtered layer without history.

The rows of the task's layers are read when run() starts; ``FinishedHandler`` puts back those of the
layers whose subset was refused. Plain sqlite3 on the local history file (no Spatialite function
involved); never raises: without the file or the table, nothing is taken and nothing is put back.

2026-11-18: a task canceled by a second click applies nothing, yet its run() may have inserted its entries
already. Its finished() deletes those rows by the ids recorded when they were written
(``discard_history_rows``), whatever the newer task wrote meanwhile; the ids are remembered so that the
newer task, refused, does not write them back from its snapshot (taken before they were deleted).
"""
import logging
import os
import sqlite3
from typing import Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

_COLUMNS = 'id, _updated_at, fk_project, layer_id, layer_source_id, seq_order, subset_string'
HistorySnapshot = Dict[str, List[tuple]]

# The ids of the rows canceled tasks deleted (main thread only: finished()); restore_history skips them.
_DISCARDED_ROW_IDS: Set[str] = set()


def take_history_snapshot(db_path: Optional[str], project_uuid: Optional[str],
                          layer_ids: Iterable[str]) -> Optional[HistorySnapshot]:
    """The history rows of each layer, by layer id; None when the history cannot be read."""
    layer_ids = sorted({layer_id for layer_id in layer_ids if layer_id})
    if not db_path or not project_uuid or not layer_ids or not os.path.isfile(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        try:
            marks = ', '.join('?' * len(layer_ids))
            rows = conn.execute(
                f'SELECT {_COLUMNS} FROM fm_subset_history WHERE fk_project = ? AND layer_id IN ({marks})',  # nosec B608 - placeholders only
                [project_uuid, *layer_ids]).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.debug(f"Filter history not read before the task: {exc}")
        return None
    snapshot: HistorySnapshot = {layer_id: [] for layer_id in layer_ids}
    for row in rows:
        snapshot[row[3]].append(tuple(row))
    return snapshot


def restore_history(db_path: Optional[str], project_uuid: Optional[str],
                    snapshot: Optional[HistorySnapshot], layer_ids: Iterable[str]) -> List[str]:
    """Put back the rows of the snapshot for these layers; the ids of the layers put back."""
    if not snapshot or not db_path or not project_uuid or not os.path.isfile(db_path):
        return []
    layer_ids = [layer_id for layer_id in dict.fromkeys(layer_ids) if layer_id in snapshot]
    if not layer_ids:
        return []
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        try:
            with conn:  # one transaction: all the layers or none
                for layer_id in layer_ids:
                    conn.execute('DELETE FROM fm_subset_history WHERE fk_project = ? AND layer_id = ?',
                                 (project_uuid, layer_id))
                    conn.executemany(
                        f'INSERT INTO fm_subset_history ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)',  # nosec B608 - fixed columns
                        [row for row in snapshot[layer_id] if row[0] not in _DISCARDED_ROW_IDS])
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.warning(f"Filter history of the refused layers not put back: {exc}")
        return []
    return layer_ids


def discard_history_rows(db_path: Optional[str], project_uuid: Optional[str], row_ids: Iterable[str]) -> int:
    """Delete the rows of these ids (inserted by a canceled task); the number of rows deleted.

    The ids are remembered first, so that a later restore_history leaves them out even when the
    file cannot be written now.
    """
    row_ids = [row_id for row_id in dict.fromkeys(row_ids or ()) if row_id]
    if not row_ids:
        return 0
    _DISCARDED_ROW_IDS.update(row_ids)
    if not db_path or not project_uuid or not os.path.isfile(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        try:
            with conn:
                marks = ', '.join('?' * len(row_ids))
                cursor = conn.execute(
                    f'DELETE FROM fm_subset_history WHERE fk_project = ? AND id IN ({marks})',  # nosec B608 - placeholders only
                    [project_uuid, *row_ids])
                return max(cursor.rowcount, 0)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.warning(f"Filter history rows of the canceled task not deleted: {exc}")
        return 0
