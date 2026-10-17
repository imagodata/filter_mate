# -*- coding: utf-8 -*-
"""
2026-10-17: the user's settings reach the tasks.

``get_optimization_thresholds`` / ``get_simplification_config`` read
``task_parameters['config']['APP']['SETTINGS']``: nothing ever set a
``config`` key (the app passes the configuration as ``config_data``, and
``ENV_VARS`` holds it as ``CONFIG_DATA``) and config.default.json keeps these
sections under ``APP.OPTIONS``. Every threshold was the hard-coded default.
"""
import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[4]


def _load():
    spec = importlib.util.spec_from_file_location(
        "fmtest_config_provider", _ROOT / "core" / "optimization" / "config_provider.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cp = _load()


def _config(**options):
    return {"APP": {"OPTIONS": options}}


THRESHOLDS = {"OPTIMIZATION_THRESHOLDS": {"source_mv_fid_threshold": {"value": 42},
                                          "large_dataset_warning": {"value": 7}}}


@pytest.mark.unit
class TestAppOptionsLookup:

    @pytest.mark.parametrize("params", [
        {"task": {"config_data": _config(**THRESHOLDS)}},   # filter / export tasks
        {"config_data": _config(**THRESHOLDS)},             # TaskParameters.to_legacy_format
        {"CONFIG_DATA": _config(**THRESHOLDS)},             # ENV_VARS
    ])
    def test_thresholds_are_read_from_app_options(self, params):
        thresholds = cp.get_optimization_thresholds(params)
        assert thresholds["source_mv_fid_threshold"] == 42
        assert thresholds["large_dataset_warning"] == 7
        assert thresholds["update_extents_threshold"] == cp.DEFAULT_OPTIMIZATION_THRESHOLDS["update_extents_threshold"]

    def test_simplification_is_read_from_app_options(self):
        params = {"task": {"config_data": _config(GEOMETRY_SIMPLIFICATION={
            "enabled": {"value": False}, "show_simplification_warnings": {"value": False}})}}
        config = cp.get_simplification_config(params)
        assert config["enabled"] is False
        assert config["show_warnings"] is False
        assert config["max_wkt_length"] == cp.DEFAULT_SIMPLIFICATION_CONFIG["max_wkt_length"]

    def test_plain_values_are_accepted(self):
        params = {"CONFIG_DATA": _config(OPTIMIZATION_THRESHOLDS={"source_mv_fid_threshold": 9})}
        assert cp.get_optimization_thresholds(params)["source_mv_fid_threshold"] == 9

    def test_defaults_without_configuration(self):
        assert cp.get_optimization_thresholds({"task": {}}) == cp.DEFAULT_OPTIMIZATION_THRESHOLDS
        assert cp.get_optimization_thresholds(None) == cp.DEFAULT_OPTIMIZATION_THRESHOLDS
        assert cp.get_app_options({"task": {"config_data": None}}) == {}

    def test_app_option_value(self):
        params = {"task": {"config_data": _config(PARALLEL_FILTERING={"enabled": {"value": False}})}}
        assert cp.get_app_option_value(params, "PARALLEL_FILTERING", "enabled", True) is False
        assert cp.get_app_option_value(params, "PARALLEL_FILTERING", "min_layers", 2) == 2
        assert cp.get_app_option_value({}, "STREAMING_EXPORT", "enabled", True) is True

    def test_shipped_default_configuration_matches_the_defaults(self):
        shipped = json.loads((_ROOT / "config" / "config.default.json").read_text(encoding="utf-8"))
        assert cp.get_optimization_thresholds({"CONFIG_DATA": shipped}) == cp.DEFAULT_OPTIMIZATION_THRESHOLDS
        assert cp.get_simplification_config({"CONFIG_DATA": shipped}) == cp.DEFAULT_SIMPLIFICATION_CONFIG
