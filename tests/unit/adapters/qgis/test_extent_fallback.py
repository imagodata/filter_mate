# -*- coding: utf-8 -*-
"""The cut by extent left for an exact filter a web service may refuse (adapters/qgis/extent_fallback.py)."""
import importlib.util
import pathlib
import threading

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "extent_fallback.py"


@pytest.fixture
def fallback():
    spec = importlib.util.spec_from_file_location("fm_extent_fallback", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KEYS, BOX = '"id" IN (1, 2)', "intersects_bbox($geometry, geom_from_wkt('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'))"


def test_what_was_left_is_taken_once(fallback):
    fallback.remember("layer", KEYS, BOX)
    assert fallback.take("layer", KEYS) == BOX
    assert fallback.take("layer", KEYS) is None and fallback.pending() == 0


def test_only_the_filter_it_was_left_for_takes_it(fallback):
    """Another layer, or another filter of the same layer (a later run), finds nothing."""
    fallback.remember("layer", KEYS, BOX)
    assert fallback.take("other", KEYS) is None
    assert fallback.take("layer", '"id" IN (3)') is None
    assert fallback.take("layer", KEYS) == BOX


def test_a_later_run_replaces_what_an_earlier_one_left(fallback):
    fallback.remember("layer", KEYS, BOX)
    fallback.remember("layer", KEYS, "another box")
    assert fallback.pending() == 1 and fallback.take("layer", KEYS) == "another box"


def test_forget_drops_everything_of_a_layer_only(fallback):
    fallback.remember("layer", KEYS, BOX)
    fallback.remember("layer", '"id" IN (3)', BOX)
    fallback.remember("other", KEYS, BOX)
    fallback.forget("layer")
    assert fallback.pending() == 1 and fallback.take("other", KEYS) == BOX


@pytest.mark.parametrize("layer_id, subset, box", [("", KEYS, BOX), ("layer", "", BOX), ("layer", KEYS, ""),
                                                   ("layer", BOX, BOX), (None, KEYS, BOX)])
def test_nothing_is_left_for_nothing(fallback, layer_id, subset, box):
    fallback.remember(layer_id, subset, box)
    assert fallback.pending() == 0


def test_what_canceled_tasks_left_does_not_pile_up(fallback):
    for number in range(fallback.MAX_PENDING + 20):
        fallback.remember(f"layer{number}", KEYS, BOX)
    assert fallback.pending() == fallback.MAX_PENDING
    assert fallback.take("layer0", KEYS) is None  # the oldest went
    assert fallback.take(f"layer{fallback.MAX_PENDING + 19}", KEYS) == BOX


def test_left_by_a_task_and_taken_by_the_main_thread(fallback):
    threads = [threading.Thread(target=fallback.remember, args=(f"layer{number}", KEYS, BOX)) for number in range(32)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(fallback.take(f"layer{number}", KEYS) for number in range(32)) == [BOX] * 32
