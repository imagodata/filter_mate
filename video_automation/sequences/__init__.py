"""
Video Sequences
===============
Each module implements one sequence from the FilterMate video script.
Sequences are auto-discovered from this package and sorted by sequence_id.
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from sequences.base import VideoSequence

# Auto-discover all VideoSequence subclasses in this package (top-level only).
_pkg_dir = Path(__file__).parent
for _info in pkgutil.iter_modules([str(_pkg_dir)]):
    if _info.ispkg:
        continue  # skip sub-packages like v01/
    importlib.import_module(f"sequences.{_info.name}")

# Collect and sort by sequence_id (e.g. "seq00", "seq01", …)
SEQUENCES: list[type[VideoSequence]] = sorted(
    [
        cls for cls in VideoSequence.__subclasses__()
        if cls.__module__.startswith("sequences.seq")
    ],
    key=lambda cls: cls.sequence_id,
)

__all__ = ["SEQUENCES", "VideoSequence"]
