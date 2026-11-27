"""QGIS profile location for the local, bounded conversation archive."""
import logging
import hashlib
import sqlite3
from pathlib import Path

from ...core.agent.conversations import ConversationStore

logger = logging.getLogger('FilterMate.agent')


def open_store():
    from qgis.core import QgsApplication
    directory = QgsApplication.qgisSettingsDirPath()
    if not isinstance(directory, str) or not directory:
        return None
    try:
        store = ConversationStore(Path(directory) / 'filter_mate' / 'agent-conversations.sqlite3')
        _migrate(store)
        return store
    except (OSError, sqlite3.Error, ValueError):
        logger.warning('Agent: conversation archive unavailable', exc_info=True)
        return None


def _migrate(store):
    """Import the old per-project slots once; never resurrect an intentionally emptied conversation."""
    from qgis.core import QgsSettings
    from . import request_log_store, session_store, transcript_store
    paths = {}
    for item in request_log_store.load():
        path = item.get('path')
        if path:
            paths[hashlib.blake2b(path.encode('utf-8'), digest_size=10).hexdigest()] = path
    for key in transcript_store._index(QgsSettings()):
        if store.has_alias(key):
            continue
        transcript = transcript_store.load(key)
        if not transcript:
            continue
        project = store.project(key)
        identifier = store.start(project, paths.get(key, ''))
        store.save(identifier, project, transcript, session_store.load(key), paths.get(key, ''))
