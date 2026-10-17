"""Entry point: ``python -m filtermate_api.mcp`` (or ``python path/to/filtermate_api/mcp/__main__.py``)."""

import os
import sys

MIN_MCP = "1.7"  # oldest release tested; the first with ToolAnnotations (see requirements-mcp.txt)

if not __package__:
    # Run as a script: sys.path[0] is this folder, whose modules (server.py, settings.py...) would
    # shadow installed packages, and the package itself is not importable. Point sys.path at the
    # folder that holds ``filtermate_api`` instead.
    _here = os.path.dirname(os.path.realpath(__file__))
    _root = os.path.dirname(os.path.dirname(_here))
    sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.getcwd()) != _here]
    sys.path.insert(0, _root)
    __package__ = "filtermate_api.mcp"


def _run() -> int:
    from filtermate_api.mcp.server import main
    return main()


if __name__ == "__main__":
    try:
        sys.exit(_run())
    except ImportError as exc:  # the SDK is the only dependency that may be missing or too old
        if getattr(exc, "name", None) == "mcp":
            print("filtermate-mcp: the 'mcp' package is not installed. Run: pip install \"mcp>=%s,<3\" "
                  "(Python 3.10 or later)." % MIN_MCP, file=sys.stderr)
            sys.exit(2)
        if str(getattr(exc, "name", "") or "").startswith("mcp."):
            print("filtermate-mcp: the installed 'mcp' package is too old (%s). Run: pip install --upgrade "
                  "\"mcp>=%s,<3\"." % (exc, MIN_MCP), file=sys.stderr)
            sys.exit(2)
        raise
