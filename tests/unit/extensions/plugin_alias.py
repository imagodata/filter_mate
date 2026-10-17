# -*- coding: utf-8 -*-
"""Let top-level imported plugin modules (``extensions.*``) reach ``filter_mate.*`` test doubles.

The plugin imports its own modules RELATIVELY (``from ..config.config import ENV_VARS``): the
folder name is not ``filter_mate`` once installed from a GitHub zip. The extension tests import
``extensions.registry`` as a top-level package, where ``..`` would climb above the top-level
package. Re-rooting ``__package__`` of the one module under test under a fake ``filter_mate``
parent makes those lazy imports resolve to the ``sys.modules['filter_mate.*']`` stubs the tests
register.
"""
import importlib
import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path


def alias_package(monkeypatch, *module_names, root="filter_mate"):
    for name in module_names:
        module = importlib.import_module(name)
        spec = module.__spec__
        # __spec__.parent must agree with __package__, or every relative import warns
        monkeypatch.setattr(module, "__spec__", importlib.machinery.ModuleSpec(
            f"{root}.{spec.name}", spec.loader, origin=spec.origin))
        monkeypatch.setattr(module, "__package__", f"{root}.{spec.parent}")


def register_plugin_package_helper(monkeypatch, root="filter_mate"):
    """Register the real ``core/domain/plugin_package.py`` as ``<root>.core.domain.plugin_package``.

    Modules re-rooted under ``<root>`` import it relatively; its PLUGIN_PACKAGE then reads ``<root>``.
    """
    repo = Path(__file__).resolve().parents[3]
    for name, path in ((root, repo), (f"{root}.core", repo / "core"), (f"{root}.core.domain", repo / "core" / "domain")):
        existing = sys.modules.get(name)
        if existing is None or not hasattr(existing, "__path__"):
            package = types.ModuleType(name)
            package.__path__ = [str(path)]
            monkeypatch.setitem(sys.modules, name, package)
    name = f"{root}.core.domain.plugin_package"
    spec = importlib.util.spec_from_file_location(name, repo / "core" / "domain" / "plugin_package.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, name, module)
    return module
