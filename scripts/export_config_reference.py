#!/usr/bin/env python3
"""Regenerate ``knowledge/SETTINGS_REFERENCE.md`` from ``config/config.default.json``.

Run it after adding or changing a setting; ``--check`` fails when the file is out of date (for the tests).

    python scripts/export_config_reference.py [--check]
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "knowledge" / "SETTINGS_REFERENCE.md"


def _module():
    """``core/agent/settings_reference.py`` alone: ``core`` imports its domain package on import."""
    spec = importlib.util.spec_from_file_location("settings_reference", ROOT / "core" / "agent" / "settings_reference.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up there
    spec.loader.exec_module(module)
    return module


def main(argv) -> int:
    reference = _module()
    text = reference.reference_markdown(reference.read_settings(None))
    if "--check" in argv:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
            print(f"{OUTPUT.relative_to(ROOT)} is out of date: run python scripts/export_config_reference.py")
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}: written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
