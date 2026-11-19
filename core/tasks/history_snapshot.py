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
from typing import Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_COLUMNS = 'id, _updated_at, fk_project, layer_id, layer_source_id, seq_order, subset_string'
HistorySnapshot = Dict[str, List[tuple]]

# The ids of the rows canceled tasks deleted (main thread only: finished()); restore_history skips them.
_DISCARDED_ROW_IDS: Set[str] = set()

# 2026-11-19: the deletion runs on the main thread, where the file may be locked for writing by the run() of the
# next task: a short wait, not the 5 s of the other functions, and what could not be deleted is retried at the
# next finished() (db path, project, ids, layers or None).
_DISCARD_TIMEOUT = 0.2
_MAX_PENDING_DISCARDS = 50
_PENDING_DISCARDS: List[Tuple[str, str, List[str], Optional[List[str]]]] = []


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


def discard_history_rows(db_path: Optional[str], project_uuid: Optional[str], row_ids: Iterable[str],
                         layer_ids: Optional[Iterable[str]] = None) -> int:
    """Delete the rows of these ids (inserted by a task whose filter is not kept); the number deleted.

    ``layer_ids`` narrows it to the rows of these layers (a refused source: the targets keep theirs).
    Never waits long (``_DISCARD_TIMEOUT``: main thread): a row that cannot be deleted now, the file
    being locked by the run() of the next task, is retried by ``retry_pending_discards``.
    The ids are remembered, so that a later restore_history leaves them out in the meantime.
    """
    row_ids = [row_id for row_id in dict.fromkeys(row_ids or ()) if row_id]
    if not row_ids:
        return 0
    layer_list = [layer_id for layer_id in dict.fromkeys(layer_ids) if layer_id] if layer_ids is not None else None
    if layer_list is not None and not layer_list:
        return 0
    if layer_list is None:
        _DISCARDED_ROW_IDS.update(row_ids)
    if not db_path or not project_uuid or not os.path.isfile(db_path):
        return 0
    removed = _delete_rows(db_path, project_uuid, row_ids, layer_list)
    if removed is None:  # locked or unreadable: later
        _PENDING_DISCARDS.append((db_path, project_uuid, row_ids, layer_list))
        del _PENDING_DISCARDS[:-_MAX_PENDING_DISCARDS]
        return 0
    return removed


def _delete_rows(db_path: str, project_uuid: str, row_ids: List[str],
                 layer_list: Optional[List[str]]) -> Optional[int]:
    """Delete the rows; None when the file could not be written within the short delay."""
    try:
        conn = sqlite3.connect(db_path, timeout=_DISCARD_TIMEOUT)
        try:
            with conn:
                marks = ', '.join('?' * len(row_ids))
                query = f'FROM fm_subset_history WHERE fk_project = ? AND id IN ({marks})'  # nosec B608 - placeholders only
                params: list = [project_uuid, *row_ids]
                if layer_list is not None:
                    query += f' AND layer_id IN ({", ".join("?" * len(layer_list))})'  # nosec B608 - placeholders only
                    params += layer_list
                    found = [row[0] for row in conn.execute(f'SELECT id {query}', params)]  # nosec B608
                    _DISCARDED_ROW_IDS.update(found)
                cursor = conn.execute(f'DELETE {query}', params)  # nosec B608 - placeholders only
                return max(cursor.rowcount, 0)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.info(f"Filter history rows not deleted now, retried later: {exc}")
        return None


def retry_pending_discards() -> int:
    """Delete again the rows a locked file kept (call it from finished()); the number deleted."""
    if not _PENDING_DISCARDS:
        return 0
    pending = _PENDING_DISCARDS[:]
    del _PENDING_DISCARDS[:]
    removed = 0
    for db_path, project_uuid, row_ids, layer_list in pending:
        if not os.path.isfile(db_path):
            continue
        done = _delete_rows(db_path, project_uuid, row_ids, layer_list)
        if done is None:
            _PENDING_DISCARDS.append((db_path, project_uuid, row_ids, layer_list))
        else:
            removed += done
    return removed
