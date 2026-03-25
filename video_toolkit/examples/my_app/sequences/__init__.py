"""
Sequences for My App Tutorial
==============================
Import all sequences and list them in order here.
The orchestrator (run.py) will run them in this order.
"""

from .intro import IntroSequence
from .demo import DemoSequence

# Order matters — this is the sequence of the final video
SEQUENCES = [
    IntroSequence,
    DemoSequence,
]

__all__ = ["SEQUENCES", "IntroSequence", "DemoSequence"]
