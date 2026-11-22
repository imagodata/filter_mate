# -*- coding: utf-8 -*-
"""The stall watch of the layer tasks (2026-11-22, QGIS frozen after an elevation raster of the agent): one thread
started with the plugin; noting a task starts no thread; a task that lasts too long gets the stacks of every thread
written once, a task that ends in time nothing; it never touches the timer of faulthandler that others may use."""
import faulthandler
import importlib.util
import os
import sys
import threading
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PATH = Path(__file__).resolve().parents[4] / "infrastructure" / "utils" / "stall_watch.py"


@pytest.fixture
def watch(tmp_path, monkeypatch):
    # by path: the infrastructure.utils package imports half of the plugin
    monkeypatch.setenv("FILTERMATE_LOG_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("fmtest_stall_watch", _PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.STALL_SECONDS = 0.3
    module.POLL_SECONDS = 0.05
    yield module
    module.shutdown()
    sys.modules.pop(spec.name, None)


def _written(tmp_path):
    path = tmp_path / "stall_stacks.log"
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _wait_for(condition, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


def test_noting_a_task_starts_no_thread(watch):
    before = threading.active_count()
    token = watch.begin("add_layers")
    watch.end(token)
    assert threading.active_count() == before


def test_tasks_ended_in_time_write_nothing(watch, tmp_path):
    watch.start()
    watch.end(watch.begin("add_layers"))
    watch.end(watch.begin("remove_layers"))
    time.sleep(0.6)
    assert _written(tmp_path) == ""


def test_a_stalled_task_writes_every_thread_once(watch, tmp_path):
    watch.start()
    token = watch.begin("add_layers")
    assert _wait_for(lambda: "add_layers running" in _written(tmp_path))
    time.sleep(0.4)  # more looks: still one dump for this task
    text = _written(tmp_path)
    assert text.count("add_layers running") == 1
    assert "test_stall_watch.py" in text  # this test's own frame: the stacks of the threads follow the line
    watch.end(token)


def test_each_stalled_task_is_written_even_when_another_ran_first(watch, tmp_path):
    watch.start()
    first = watch.begin("add_layers")
    assert _wait_for(lambda: "add_layers running" in _written(tmp_path))
    second = watch.begin("remove_layers")  # started while the first still runs
    watch.end(first)
    assert _wait_for(lambda: "remove_layers running" in _written(tmp_path))
    watch.end(second)


def test_end_is_idempotent_and_takes_none(watch):
    token = watch.begin("add_layers")
    watch.end(token)
    watch.end(token)
    watch.end(None)
    watch.end(12345)


def test_the_timer_of_faulthandler_of_others_is_left_alone(watch, tmp_path):
    with open(tmp_path / "theirs.log", "wb") as theirs:
        faulthandler.dump_traceback_later(0.5, file=theirs)
        try:
            watch.start()
            watch.end(watch.begin("add_layers"))
            watch.shutdown()
            time.sleep(0.8)
        finally:
            faulthandler.cancel_dump_traceback_later()
    assert (tmp_path / "theirs.log").read_bytes()  # their dump came: nothing canceled it


def test_shutdown_ends_the_thread(watch):
    watch.start()
    thread = watch._watcher[0]
    watch.shutdown()
    thread.join(2)
    assert not thread.is_alive()


def test_a_large_file_starts_again(watch, tmp_path):
    (tmp_path / "stall_stacks.log").write_bytes(b"x" * (watch.MAX_BYTES + 10))
    watch.write_stacks(["add_layers"])
    assert os.path.getsize(tmp_path / "stall_stacks.log") < watch.MAX_BYTES
