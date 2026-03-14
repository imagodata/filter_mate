"""
Video Sequences
===============
Each module implements one sequence from the FilterMate video script.
Import them via SEQUENCES registry for use by the orchestrator.
"""
from __future__ import annotations

from sequences.seq00_intro import Seq00Intro
from sequences.seq01_problem import Seq01Problem
from sequences.seq02_install import Seq02Install
from sequences.seq03_interface import Seq03Interface
from sequences.seq04_filtering_demo import Seq04FilteringDemo
from sequences.seq05_exploration import Seq05Exploration
from sequences.seq06_export import Seq06Export
from sequences.seq07_backends import Seq07Backends
from sequences.seq08_architecture import Seq08Architecture
from sequences.seq09_advanced import Seq09Advanced
from sequences.seq10_conclusion import Seq10Conclusion

SEQUENCES = [
    Seq00Intro,
    Seq01Problem,
    Seq02Install,
    Seq03Interface,
    Seq04FilteringDemo,
    Seq05Exploration,
    Seq06Export,
    Seq07Backends,
    Seq08Architecture,
    Seq09Advanced,
    Seq10Conclusion,
]

__all__ = [
    "SEQUENCES",
    "Seq00Intro", "Seq01Problem", "Seq02Install", "Seq03Interface",
    "Seq04FilteringDemo", "Seq05Exploration", "Seq06Export", "Seq07Backends",
    "Seq08Architecture", "Seq09Advanced", "Seq10Conclusion",
]
