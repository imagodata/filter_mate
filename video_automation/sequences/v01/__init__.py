"""
Video V01 — Installation & Premier Pas
=======================================
9 sequence files (s00-s08) covering the 12 sections of SCRIPT_V01_INSTALLATION.md.
Auto-discovered from this package and sorted by sequence_id.
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from sequences.base import VideoSequence

# Auto-discover all sequence subclasses in this sub-package.
_pkg_dir = Path(__file__).parent
for _info in pkgutil.iter_modules([str(_pkg_dir)]):
    importlib.import_module(f"sequences.v01.{_info.name}")


def _collect_subclasses(base: type) -> list[type]:
    """Recursively collect all subclasses of *base* in sequences.v01."""
    result = []
    for cls in base.__subclasses__():
        if cls.__module__.startswith("sequences.v01."):
            result.append(cls)
        result.extend(_collect_subclasses(cls))
    return result


# Collect and sort by sequence_id (e.g. "v01_s00", "v01_s01", …)
V01_SEQUENCES: list[type[VideoSequence]] = sorted(
    _collect_subclasses(VideoSequence),
    key=lambda cls: cls.sequence_id,
)

__all__ = ["V01_SEQUENCES"]
