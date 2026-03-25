"""
Video Sequence Base Classes
============================
All sequence classes inherit from VideoSequence. The orchestrator calls
setup() -> execute() -> teardown() in order.

Works with both OBSController (desktop) and FrameCapturer (headless/Docker).
Both implement the same recording interface (start/stop/switch_scene).

For narration-synchronized sequences, use **TimelineSequence** instead.
Override ``build_timeline()`` to return a list of ``NarrationCue`` objects
that pair narration text with UI actions.

Example usage::

    class IntroSequence(VideoSequence):
        name = "Intro"
        sequence_id = "seq00"
        duration_estimate = 15.0
        narration_text = "Welcome to the tutorial!"

        def execute(self, recorder, app, config):
            app.focus_window()
            app.wait(2.0)
            app.screenshot("output/intro_frame.png")

    class DemoSequence(TimelineSequence):
        name = "Demo"
        sequence_id = "seq01"

        def build_timeline(self, recorder, app, config):
            return [
                NarrationCue(
                    text="Let's open the file menu.",
                    actions=lambda: app.hotkey("alt", "f"),
                ),
                NarrationCue(
                    text="Now we select New.",
                    actions=lambda: app.press_key("n"),
                    post_delay=1.0,
                ),
            ]
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from toolkit.frame_capturer import FrameCapturer
    from toolkit.obs_controller import OBSController
    from toolkit.app_automator import AppAutomator
    from toolkit.timeline import NarrationCue, TimelineExecutor, TimelineResult

    Recorder = Union[OBSController, FrameCapturer]

logger = logging.getLogger(__name__)


class VideoSequence(ABC):
    """
    Abstract base class for a single video sequence.

    Subclasses must implement execute(). Set class attributes to describe
    the sequence.

    Class Attributes
    ----------------
    name : str
        Human-readable name for this sequence.
    sequence_id : str
        Short identifier, e.g. "seq04".
    duration_estimate : float
        Estimated recording duration in seconds.
    narration_text : str
        Full narration text for this sequence (used for TTS generation).
    diagram_ids : list[str]
        Which diagram IDs to show during this sequence.
    obs_scene : str
        OBS scene name to activate before recording this sequence.
    """

    name: str = "Unnamed Sequence"
    sequence_id: str = "seq00"
    duration_estimate: float = 30.0
    narration_text: str = ""
    diagram_ids: list[str] = []
    obs_scene: str = "App Fullscreen"

    # Populated after execution for TimelineSequence; always None for basic sequences.
    timeline_result: Optional["TimelineResult"] = None

    def __init__(self) -> None:
        self._start_time: float = 0.0
        self._log = logging.getLogger(f"sequences.{self.sequence_id}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setup(self, recorder: "Recorder", app: "AppAutomator", config: dict) -> None:
        """
        Called before recording starts. Switch scene, focus app window, etc.
        Override to add sequence-specific setup.
        """
        self._log.info("=== SETUP: %s ===", self.name)
        try:
            recorder.switch_scene(self.obs_scene)
        except Exception as exc:  # noqa: BLE001
            self._log.warning("Scene switch failed: %s", exc)

        app.focus_window()
        transition_pause = config.get("timing", {}).get("transition_pause", 2.0)
        time.sleep(transition_pause)

    @abstractmethod
    def execute(self, recorder: "Recorder", app: "AppAutomator", config: dict) -> None:
        """
        Main automation steps for this sequence.
        Must be implemented by each subclass.
        """
        ...

    def teardown(self, recorder: "Recorder", app: "AppAutomator", config: dict) -> None:
        """
        Called after the sequence finishes. Override if cleanup is needed.
        """
        transition_pause = config.get("timing", {}).get("transition_pause", 2.0)
        self._log.info(
            "=== TEARDOWN: %s (%.1fs elapsed) ===", self.name, self.elapsed()
        )
        time.sleep(transition_pause)

    # ------------------------------------------------------------------
    # Lifecycle runner
    # ------------------------------------------------------------------

    def run(self, recorder: "Recorder", app: "AppAutomator", config: dict) -> None:
        """Run the full sequence: setup -> execute -> teardown."""
        self._start_time = time.time()
        self._log.info("Starting sequence: %s", self.name)
        try:
            self.setup(recorder, app, config)
            self.execute(recorder, app, config)
        finally:
            self.teardown(recorder, app, config)

    def elapsed(self) -> float:
        """Return elapsed seconds since sequence started."""
        return time.time() - self._start_time if self._start_time else 0.0

    # ------------------------------------------------------------------
    # Shared helpers available to all sequences
    # ------------------------------------------------------------------

    def show_diagram(
        self,
        recorder: "Recorder",
        diagram_id: str,
        duration: float = 5.0,
    ) -> None:
        """
        Switch to the Diagram Overlay scene, wait, then switch back.

        Parameters
        ----------
        diagram_id : str
            The diagram to display (used for logging).
        duration : float
            How long to show the diagram.
        """
        self._log.info("Showing diagram: %s for %.1fs", diagram_id, duration)
        recorder.show_diagram_overlay(visible=True)
        time.sleep(duration)
        recorder.show_diagram_overlay(visible=False)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name!r} est={self.duration_estimate:.0f}s>"
        )


class TimelineSequence(VideoSequence):
    """
    A video sequence driven by narration-synchronized cues.

    Instead of implementing ``execute()`` with manual ``wait()`` calls,
    subclasses override ``build_timeline()`` to return a list of
    ``NarrationCue`` objects. The timeline executor handles timing
    automatically based on actual narration audio durations.

    The ``timeline_result`` attribute is populated after execution and
    contains timecodes for post-production narration placement.

    Class Attributes
    ----------------
    play_audio : bool
        If True, play narration through speakers during recording (captured
        by OBS). If False, use durations for timing only and mix in post.
    """

    play_audio: bool = False

    def build_timeline(
        self,
        recorder: "Recorder",
        app: "AppAutomator",
        config: dict,
    ) -> list["NarrationCue"]:
        """
        Build the list of narration cues for this sequence.

        Override this method instead of ``execute()``.

        Parameters
        ----------
        recorder : Recorder
            OBS controller or frame capturer.
        app : AppAutomator
            Application automation controller.
        config : dict
            Full config dict.

        Returns
        -------
        list[NarrationCue]
            Ordered list of cues to execute.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build_timeline()"
        )

    def execute(self, recorder: "Recorder", app: "AppAutomator", config: dict) -> None:
        """Execute the timeline: prepare narration audio, then run cues."""
        from toolkit.narrator import Narrator
        from toolkit.timeline import TimelineExecutor

        cues = self.build_timeline(recorder, app, config)
        if not cues:
            self._log.warning("No cues defined for %s", self.name)
            return

        narr_config = config.get("narration", {})
        narrator = Narrator(narr_config)

        # Determine cache directory for audio segments
        video_id = self.sequence_id.split("_")[0] if "_" in self.sequence_id else ""
        cache_dir = narrator.output_dir
        if video_id:
            cache_dir = cache_dir / video_id / "segments"

        executor = TimelineExecutor(
            narrator=narrator,
            sequence_id=self.sequence_id,
            cache_dir=cache_dir,
            play_audio=self.play_audio,
        )

        # Pre-generate all audio (before recording starts to avoid latency)
        executor.prepare(cues)

        estimated = executor.get_total_estimated_duration(cues)
        self._log.info(
            "%s: %d cues, ~%.0fs estimated", self.name, len(cues), estimated,
        )

        # Execute the timeline
        self.timeline_result = executor.execute(cues, recorder=recorder)
        self._log.info(
            "%s complete: %.1fs actual", self.name, self.timeline_result.total_duration,
        )
