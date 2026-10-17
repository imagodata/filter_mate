# -*- coding: utf-8 -*-
"""
A pytest run must not write in the repository's logs/ folder.

The plugin's rotating handler opened logs/filtermate.log on the first record
emitted while the tests imported it: the file grew by hundreds of KB per run
(10 MB with its five backups), and a local plugin zip embedded it. The root
conftest points FILTERMATE_LOG_DIR to a temporary folder before any plugin
module is imported, and redirects handlers that were made for logs/ anyway.
"""
import logging
import os
import sys
from pathlib import Path

import pytest

from infrastructure import logging as fm_logging

pytestmark = pytest.mark.unit

_REPO_LOGS = Path(__file__).resolve().parents[3] / "logs"


def _repo_log_state():
    return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns)
                  for p in _REPO_LOGS.iterdir() if p.name != ".gitkeep") if _REPO_LOGS.is_dir() else []


def test_log_folder_is_not_the_repository_one():
    assert os.environ.get("FILTERMATE_LOG_DIR")
    assert Path(fm_logging.get_log_file_path()).resolve().parent != _REPO_LOGS.resolve()


def test_records_do_not_reach_the_repository_logs():
    before = _repo_log_state()

    logger = fm_logging.get_logger("FilterMate.IsolationProbe")
    logger.warning("isolation probe record")
    logging.getLogger("filter_mate.isolation_probe").warning("isolation probe record (package family)")
    fm_logging.flush_logs()

    assert _repo_log_state() == before


def test_a_handler_made_for_the_repository_logs_is_redirected(tmp_path):
    from logging.handlers import RotatingFileHandler

    conftest = sys.modules["tests.conftest"]

    handler = RotatingFileHandler(str(_REPO_LOGS / "filtermate_probe.log"), delay=True)
    probe = logging.getLogger("fm.isolation.redirect")
    probe.addHandler(handler)
    try:
        conftest._redirect_repo_log_handlers()
        assert Path(handler.baseFilename).parent == Path(conftest._TEST_LOG_DIR)
    finally:
        probe.removeHandler(handler)
        handler.close()
