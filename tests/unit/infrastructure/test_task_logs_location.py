# -*- coding: utf-8 -*-
"""
The task logs live next to the main log, never in the user's project folder.

Every task module called ``setup_logger(name, <PATH_ABSOLUTE_PROJECT>/logs/filtermate_tasks.log)``:
a ``logs`` folder was created in the folder of the user's QGIS project (or in their
home folder for an unsaved one) and filled with a rotating journal. ``setup_logger``
keeps the file name it is given and writes it in the plugin's log folder
(``FILTERMATE_LOG_DIR``, like ``filtermate.log``).
"""
import logging
from pathlib import Path

import pytest

from infrastructure import logging as fm_logging

pytestmark = pytest.mark.unit


@pytest.fixture
def plugin_logs(tmp_path, monkeypatch):
    folder = tmp_path / "plugin_logs"
    monkeypatch.setattr(fm_logging, "_LOG_DIR", str(folder))
    return folder


def _file_handlers(logger):
    return [h for h in logger.handlers if isinstance(h, logging.FileHandler)]


def test_a_log_file_in_the_project_folder_is_written_in_the_plugin_log_folder(tmp_path, plugin_logs):
    project = tmp_path / "my_project"
    project.mkdir()
    name = "FilterMate.Tasks.LocationProbe1"
    logging.getLogger(name).handlers = []

    logger = fm_logging.setup_logger(name, str(project / "logs" / "filtermate_tasks.log"))
    logger.info("task record")
    for handler in _file_handlers(logger):
        handler.flush()

    handlers = _file_handlers(logger)
    assert len(handlers) == 1
    assert Path(handlers[0].baseFilename) == plugin_logs / "filtermate_tasks.log"
    assert "task record" in (plugin_logs / "filtermate_tasks.log").read_text(encoding="utf-8")
    assert list(project.iterdir()) == []  # no logs/ folder made in the user's project folder


def test_a_bare_file_name_goes_there_too(tmp_path, plugin_logs, monkeypatch):
    monkeypatch.chdir(tmp_path)
    name = "FilterMate.Tasks.LocationProbe2"
    logging.getLogger(name).handlers = []

    logger = fm_logging.setup_logger(name, "x.log")
    logger.info("record")

    assert Path(_file_handlers(logger)[0].baseFilename) == plugin_logs / "x.log"
    assert not (tmp_path / "x.log").exists()


def test_an_uncreatable_log_folder_means_no_file_handler_but_a_working_logger(tmp_path, monkeypatch):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where a folder should be", encoding="utf-8")
    monkeypatch.setattr(fm_logging, "_LOG_DIR", str(blocker / "logs"))
    name = "FilterMate.Tasks.LocationProbe3"
    logging.getLogger(name).handlers = []

    logger = fm_logging.setup_logger(name, str(tmp_path / "project" / "logs" / "filtermate_tasks.log"))
    logger.warning("still logged to the console")

    assert _file_handlers(logger) == []
    assert not (tmp_path / "project").exists()


def test_no_task_module_builds_its_log_path_from_the_project_folder_any_more_except_through_setup_logger():
    """Guard: the only users of PATH_ABSOLUTE_PROJECT + 'logs' pass it to setup_logger, which relocates it."""
    import ast
    root = Path(__file__).resolve().parents[3]
    for path in list((root / "core" / "tasks").glob("*.py")) + [root / "infrastructure" / "utils" / "task_utils.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "join" and any(
                    getattr(arg, "value", None) == "logs" for arg in node.args):
                outer = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                         and getattr(n.func, "id", None) == "setup_logger" and node in list(ast.walk(n))]
                assert outer, f"{path.name}:{node.lineno}: a logs path not given to setup_logger"
