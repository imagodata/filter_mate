"""
Video Toolkit — Reusable Desktop App Tutorial Video Automation
==============================================================
A batteries-included toolkit for creating high-quality tutorial videos
of any desktop application, with synchronized narration, diagrams, and
precise timing.

Components:
    OBSController     — OBS WebSocket 5.x recording control
    FrameCapturer     — Headless Xvfb frame capture (Docker/CI mode)
    AppAutomator      — Generic desktop app automation via PyAutoGUI
    DiagramGenerator  — Mermaid → HTML/PNG diagram slides
    Narrator          — TTS audio (edge-tts, ElevenLabs, F5-TTS)
    TimelineExecutor  — Narration-synchronized UI action timing
    VideoAssembler    — FFmpeg post-production pipeline
    VideoSequence     — Base class for reusable sequence modules
    TimelineSequence  — Narration-cue-driven sequence base class
"""

__version__ = "1.0.0"
__author__ = "Video Toolkit Contributors"

from toolkit.obs_controller import OBSController
from toolkit.frame_capturer import FrameCapturer
from toolkit.app_automator import AppAutomator
from toolkit.diagram_generator import DiagramGenerator
from toolkit.narrator import Narrator
from toolkit.timeline import NarrationCue, TimelineExecutor, TimelineResult
from toolkit.video_assembler import VideoAssembler
from toolkit.sequence import VideoSequence, TimelineSequence

__all__ = [
    "OBSController",
    "FrameCapturer",
    "AppAutomator",
    "DiagramGenerator",
    "Narrator",
    "NarrationCue",
    "TimelineExecutor",
    "TimelineResult",
    "VideoAssembler",
    "VideoSequence",
    "TimelineSequence",
]
