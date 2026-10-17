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


def alias_package(monkeypatch, *module_names):
    for name in module_names:
        module = importlib.import_module(name)
        spec = module.__spec__
        # __spec__.parent must agree with __package__, or every relative import warns
        monkeypatch.setattr(module, "__spec__", importlib.machinery.ModuleSpec(
            f"filter_mate.{spec.name}", spec.loader, origin=spec.origin))
        monkeypatch.setattr(module, "__package__", f"filter_mate.{spec.parent}")
