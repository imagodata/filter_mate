# -*- coding: utf-8 -*-
"""
GdalErrorHandler must only pop the handler it pushed.

It used to call ``gdal.GetErrorHandler`` (not in the Python bindings): __enter__ raised before the
push, __exit__ popped anyway and removed the handler of a third party.
"""
import importlib.util
from pathlib import Path

import pytest

gdal = pytest.importorskip("osgeo.gdal")

pytestmark = pytest.mark.unit

_PATH = Path(__file__).resolve().parents[4] / "infrastructure" / "utils" / "gdal_error_handler.py"
_spec = importlib.util.spec_from_file_location("_fm_gdal_error_handler", _PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
GdalErrorHandler = _module.GdalErrorHandler


@pytest.fixture
def third_party_handler():
    seen = []

    def handler(error_class, error_no, message):
        seen.append(message)

    gdal.PushErrorHandler(handler)
    yield seen
    gdal.PopErrorHandler()


def test_inside_is_quiet_and_the_third_party_handler_survives(third_party_handler):
    with GdalErrorHandler():
        gdal.Error(gdal.CE_Warning, 1, "inside")
    gdal.Error(gdal.CE_Warning, 1, "after")
    assert third_party_handler == ["after"]


def test_nested_use_unwinds_one_level_at_a_time(third_party_handler):
    with GdalErrorHandler():
        with GdalErrorHandler():
            gdal.Error(gdal.CE_Warning, 1, "deep")
        gdal.Error(gdal.CE_Warning, 1, "inside")
    gdal.Error(gdal.CE_Warning, 1, "after")
    assert third_party_handler == ["after"]


def test_without_gdal_nothing_is_popped(third_party_handler, monkeypatch):
    import builtins
    real_import = builtins.__import__

    def no_gdal(name, *args, **kwargs):
        if name == "osgeo" or name.startswith("osgeo."):
            raise ImportError("no GDAL")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_gdal)
    with GdalErrorHandler():
        pass
    monkeypatch.undo()
    gdal.Error(gdal.CE_Warning, 1, "after")
    assert third_party_handler == ["after"]
