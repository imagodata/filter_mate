# -*- coding: utf-8 -*-
"""Spatialite connection with the extension loaded and WAL enabled.

Same behaviour as ``infrastructure.utils.task_utils.spatialite_connect``, which
the plugin keeps for its own callers; the core's temp-table manager uses this one.
"""
import sqlite3

from ...log import get_logger

logger = get_logger(__name__)

# Seconds to wait for a locked database before giving up.
SQLITE_TIMEOUT = 60.0


def spatialite_connect(db_path: str, timeout: float = SQLITE_TIMEOUT) -> sqlite3.Connection:
    """Connect to ``db_path`` with the Spatialite extension loaded.

    Enables WAL mode so several readers and one writer can work at once.

    Raises:
        sqlite3.OperationalError: if the connection fails or no Spatialite
            extension can be loaded.
    """
    try:
        conn = sqlite3.connect(db_path, timeout=timeout, isolation_level=None)

        try:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA busy_timeout=60000')
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not configure PRAGMA settings for {db_path}: {e}")

        conn.enable_load_extension(True)

        # Several library names, depending on the platform.
        try:
            conn.load_extension('mod_spatialite')
        except (OSError, sqlite3.OperationalError):
            try:
                conn.load_extension('mod_spatialite.dll')  # Windows
            except (OSError, sqlite3.OperationalError):
                try:
                    conn.load_extension('libspatialite')  # Linux/Mac
                except (OSError, sqlite3.OperationalError) as e:
                    logger.error(f"Could not load Spatialite extension: {e}")
                    raise

        return conn

    except Exception as e:
        logger.error(f"Failed to connect to Spatialite database {db_path}: {e}")
        raise


__all__ = ['spatialite_connect', 'SQLITE_TIMEOUT']
