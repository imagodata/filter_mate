"""Entry point: ``python -m filtermate_api.mcp`` (or ``python path/to/filtermate_api/mcp/__main__.py``)."""

import os
import sys

if not __package__:
    # Run as a script: sys.path[0] is this folder, whose modules (server.py, settings.py...) would
    # shadow installed packages, and the package itself is not importable. Point sys.path at the
    # folder that holds ``filtermate_api`` instead.
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(os.path.dirname(_here))
    sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.getcwd()) != _here]
    sys.path.insert(0, _root)
    __package__ = "filtermate_api.mcp"


def _run() -> int:
    from filtermate_api.mcp.server import main
    return main()


if __name__ == "__main__":
    try:
        sys.exit(_run())
    except ImportError as exc:  # the SDK is the only dependency that may be missing
        if getattr(exc, "name", "") and exc.name.split(".")[0] == "mcp":
            print("filtermate-mcp: the 'mcp' package is not installed. Run: pip install mcp "
                  "(Python 3.10 or later).", file=sys.stderr)
            sys.exit(2)
        raise
