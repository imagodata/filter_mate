"""
Base Video Sequence
===================
All sequence classes inherit from VideoSequence. The orchestrator calls
setup() → execute() → teardown() in order.

Works with both OBSController (desktop) and FrameCapturer (headless/Docker).
Both implement the same recording interface (start/stop/switch_scene).
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from core.frame_capturer import FrameCapturer
    from core.obs_controller import OBSController
    from core.qgis_automator import QGISAutomator

    Recorder = Union[OBSController, FrameCapturer]

logger = logging.getLogger(__name__)


class VideoSequence(ABC):
    """
    Abstract base class for a single video sequence.

    Subclasses must set class attributes and implement execute().

    Attributes
    ----------
    name : str
        Human-readable name for this sequence.
    sequence_id : str
        Short identifier, e.g. "seq04".
    duration_estimate : float
        Estimated recording duration in seconds.
    narration_text : str
        Full narration text (used for TTS generation).
    diagram_ids : list[str]
        Which diagram IDs to show during this sequence (from mermaid_definitions.py).
    obs_scene : str
        OBS scene name to activate before recording this sequence.
    """

    name: str = "Unnamed Sequence"
    sequence_id: str = "seq00"
    duration_estimate: float = 30.0
    narration_text: str = ""
    diagram_ids: list[str] = []
    obs_scene: str = "QGIS + FilterMate"

    def __init__(self) -> None:
        self._start_time: float = 0.0
        self._log = logging.getLogger(f"sequences.{self.sequence_id}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(self, obs: "Recorder", qgis: "QGISAutomator", config: dict) -> None:
        """
        Called before recording starts. Switch OBS scene, focus QGIS, etc.
        Override to add sequence-specific setup.
        """
        self._log.info("=== SETUP: %s ===", self.name)
        try:
            obs.switch_scene(self.obs_scene)
        except Exception as exc:  # noqa: BLE001
            self._log.warning("Scene switch failed: %s", exc)

        qgis.focus_qgis()
        transition_pause = config.get("timing", {}).get("transition_pause", 2.0)
        time.sleep(transition_pause)

    @abstractmethod
    def execute(self, obs: "Recorder", qgis: "QGISAutomator", config: dict) -> None:
        """
        Main automation steps for this sequence.
        Must be implemented by each subclass.
        """
        ...

    def teardown(self, obs: "Recorder", qgis: "QGISAutomator", config: dict) -> None:
        """
        Called after the sequence finishes. Pause before next sequence.
        Override if cleanup is needed.
        """
        transition_pause = config.get("timing", {}).get("transition_pause", 2.0)
        self._log.info("=== TEARDOWN: %s (%.1fs elapsed) ===", self.name, self.elapsed())
        time.sleep(transition_pause)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def run(self, obs: "Recorder", qgis: "QGISAutomator", config: dict) -> None:
        """Run the full sequence: setup → execute → teardown."""
        self._start_time = time.time()
        self._log.info("Starting sequence: %s", self.name)
        try:
            self.setup(obs, qgis, config)
            self.execute(obs, qgis, config)
        finally:
            self.teardown(obs, qgis, config)

    def elapsed(self) -> float:
        """Return elapsed seconds since sequence started."""
        return time.time() - self._start_time if self._start_time else 0.0

    def show_diagram(self, obs: "Recorder", diagram_id: str, duration: float = 5.0) -> None:
        """
        Switch to the Diagram Overlay scene, wait, then switch back.

        Parameters
        ----------
        diagram_id : str
            The diagram to display (used for logging; OBS browser source must be pre-configured).
        duration : float
            How long to show the diagram.
        """
        self._log.info("Showing diagram: %s for %.1fs", diagram_id, duration)
        obs.show_diagram_overlay(visible=True)
        time.sleep(duration)
        obs.show_diagram_overlay(visible=False)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} est={self.duration_estimate:.0f}s>"
