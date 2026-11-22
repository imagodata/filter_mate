# -*- coding: utf-8 -*-
"""Entry of the host when the launcher starts it in another Python.

That Python (the one of a QGIS install) does not have FilterMate on its path, and must not
get the launcher's ``site-packages`` either: binary packages of another Python would follow.
So the package is registered by its folder, under the name the plugin expects, whatever the
folder is called (a pip install, a checkout, a worktree).

    python-qgis.bat .../standalone/_bootstrap.py [options of the host]
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_DIR = os.path.dirname(_HERE)
_NAME = "filter_mate"

# Run as a script, this folder is first on the path: its modules (cli, runtime, ...) must not be importable bare.
sys.path[:] = [entry for entry in sys.path if os.path.abspath(entry or os.getcwd()) != _HERE]


def register_package():
    """Make ``filter_mate`` importable from its folder, without touching ``sys.path``."""
    module = sys.modules.get(_NAME)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(
        _NAME, os.path.join(_PACKAGE_DIR, "__init__.py"), submodule_search_locations=[_PACKAGE_DIR])
    module = importlib.util.module_from_spec(spec)
    sys.modules[_NAME] = module
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    register_package()
    from filter_mate.standalone.host.app import main as host_main
    return host_main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    sys.exit(main())
