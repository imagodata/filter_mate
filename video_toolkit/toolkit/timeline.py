"""
Timeline — Narration-synchronized execution
=============================================
Provides a cue-based system where narration segments are paired with UI
actions. Each cue knows its audio duration, so actions are timed precisely
to match the voiceover.

Sync modes:
  "during" (default): narration and actions run in parallel. Actions pad
                      to match narration length if they finish first.
  "after":  narration plays first, then actions run.
  "before": actions run first, then narration plays.

Usage in a sequence::

    class MySequence(TimelineSequence):
        def build_timeline(self, recorder, app, config):
            return [
                NarrationCue(
                    text="Welcome to the tutorial.",
                    actions=lambda: app.wait(1.0),
                ),
                NarrationCue(
                    text="Let's open the file menu.",
                    actions=lambda: app.hotkey("alt", "f"),
                    post_delay=1.0,
                ),
            ]
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from toolkit.narrator import Narrator

logger = logging.getLogger(__name__)


@dataclass
class NarrationCue:
    """
    A single narration segment with associated UI actions.

    Parameters
    ----------
    text : str
        Narration text for TTS. Empty string = silent cue (just actions).
    actions : callable or None
        UI actions to execute during this cue. Called with no arguments.
        Use a lambda or closure that captures ``recorder``, ``app``, ``config``.
    sync : str
        When to run actions relative to narration:
        - ``"during"``: start actions immediately, narration plays in parallel.
          If actions finish before narration, pad with silence.
        - ``"after"``: run actions after narration audio finishes.
        - ``"before"``: run actions first, then play narration.
    pre_delay : float
        Seconds to wait before this cue starts.
    post_delay : float
        Seconds to wait after this cue completes (actions + narration).
    scene : str or None
        If set, switch the recorder to this scene before executing this cue.
    label : str
        Human-readable label for logging (auto-derived from text if empty).
    """

    text: str = ""
    actions: Optional[Callable[[], None]] = None
    sync: str = "during"  # "during", "after", "before"
    pre_delay: float = 0.0
    post_delay: float = 0.5
    scene: Optional[str] = None
    label: str = ""

    # Filled at runtime by TimelineExecutor
    _audio_path: Optional[Path] = field(default=None, repr=False)
    _audio_duration: float = field(default=0.0, repr=False)

    def __post_init__(self):
        if not self.label and self.text:
            self.label = self.text[:50].rstrip() + ("..." if len(self.text) > 50 else "")


@dataclass
class TimelineResult:
    """Result of executing a timeline — used for post-production assembly."""

    cues: list[NarrationCue]
    total_duration: float
    # List of (timecode_seconds, audio_path) for each narration segment
    narration_timecodes: list[tuple[float, Path]]


class TimelineExecutor:
    """
    Executes a list of NarrationCues with precise timing.

    1. Pre-generates TTS audio for each cue (if not already cached).
    2. Measures audio durations.
    3. During recording, plays audio and/or runs actions with correct timing.

    Parameters
    ----------
    narrator : Narrator
        TTS engine for generating audio segments.
    sequence_id : str
        Used for naming audio segment files.
    cache_dir : Path or None
        Directory for cached audio segments. Defaults to output/narration/segments/.
    play_audio : bool
        If True, play narration audio through speakers during recording
        (so the recorder captures it). If False, use durations for timing only
        (narration mixed in post-production).
    """

    def __init__(
        self,
        narrator: "Narrator",
        sequence_id: str,
        cache_dir: Optional[Path] = None,
        play_audio: bool = False,
    ):
        self.narrator = narrator
        self.sequence_id = sequence_id
        self.cache_dir = cache_dir or Path("output/narration/segments")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.play_audio = play_audio
        self._log = logging.getLogger(f"timeline.{sequence_id}")

    def prepare(self, cues: list[NarrationCue]) -> None:
        """
        Pre-generate all narration audio and measure durations.

        Call this before recording starts so there's no TTS latency
        during the actual sequence execution.
        """
        self._log.info("Preparing %d cues...", len(cues))
        for i, cue in enumerate(cues):
            if not cue.text:
                cue._audio_path = None
                cue._audio_duration = 0.0
                continue

            audio_file = self.cache_dir / f"{self.sequence_id}_cue{i:02d}.mp3"

            if audio_file.exists():
                cue._audio_path = audio_file
                cue._audio_duration = self.narrator.get_narration_duration(audio_file)
                self._log.debug("Cue %d cached: %.1fs - %s", i, cue._audio_duration, cue.label)
            else:
                cue._audio_path = self.narrator.generate_narration(cue.text, audio_file)
                cue._audio_duration = self.narrator.get_narration_duration(audio_file)
                self._log.info("Cue %d generated: %.1fs - %s", i, cue._audio_duration, cue.label)

    def execute(self, cues: list[NarrationCue], recorder=None) -> TimelineResult:
        """
        Execute the timeline: play narration + run actions with precise timing.

        Parameters
        ----------
        cues : list[NarrationCue]
            Prepared cues (call ``prepare()`` first).
        recorder : OBSController or FrameCapturer, optional
            Recorder for scene switching.

        Returns
        -------
        TimelineResult
            Timing data for post-production narration placement.
        """
        narration_timecodes: list[tuple[float, Path]] = []
        timeline_start = time.time()

        for i, cue in enumerate(cues):
            cue_start = time.time()
            elapsed = cue_start - timeline_start
            self._log.info(
                "[%6.1fs] Cue %d/%d: %s",
                elapsed, i + 1, len(cues), cue.label or "(silent)",
            )

            # Pre-delay
            if cue.pre_delay > 0:
                time.sleep(cue.pre_delay)

            # Scene switch
            if cue.scene and recorder:
                try:
                    recorder.switch_scene(cue.scene)
                except Exception as exc:
                    self._log.warning("Scene switch failed: %s", exc)

            # Execute based on sync mode
            if cue.sync == "before":
                self._run_actions(cue)
                narration_start = time.time() - timeline_start
                if cue._audio_path:
                    narration_timecodes.append((narration_start, cue._audio_path))
                self._play_or_wait(cue)
            elif cue.sync == "after":
                narration_start = time.time() - timeline_start
                if cue._audio_path:
                    narration_timecodes.append((narration_start, cue._audio_path))
                self._play_or_wait(cue)
                self._run_actions(cue)
            else:  # "during" (default)
                narration_start = time.time() - timeline_start
                if cue._audio_path:
                    narration_timecodes.append((narration_start, cue._audio_path))
                self._run_during(cue)

            # Post-delay
            if cue.post_delay > 0:
                time.sleep(cue.post_delay)

            cue_total = time.time() - cue_start
            self._log.debug(
                "  Cue %d complete: %.1fs (audio=%.1fs, pre=%.1f, post=%.1f)",
                i, cue_total, cue._audio_duration, cue.pre_delay, cue.post_delay,
            )

        total_duration = time.time() - timeline_start
        self._log.info("Timeline complete: %.1fs total", total_duration)

        return TimelineResult(
            cues=cues,
            total_duration=total_duration,
            narration_timecodes=narration_timecodes,
        )

    def _run_during(self, cue: NarrationCue) -> None:
        """Run actions in parallel with narration audio/wait."""
        if not cue.actions and not cue._audio_duration:
            return

        if not cue.actions:
            self._play_or_wait(cue)
            return

        if not cue._audio_duration:
            self._run_actions(cue)
            return

        # Both narration and actions: start audio in background, run actions, then pad.
        if self.play_audio and cue._audio_path:
            self._play_audio_background(cue._audio_path)

        action_start = time.time()
        self._run_actions(cue)
        action_elapsed = time.time() - action_start

        remaining = cue._audio_duration - action_elapsed
        if remaining > 0:
            self._log.debug(
                "  Actions took %.1fs, padding %.1fs to match narration",
                action_elapsed, remaining,
            )
            time.sleep(remaining)

    def _run_actions(self, cue: NarrationCue) -> None:
        """Execute the cue's actions callable."""
        if cue.actions:
            try:
                cue.actions()
            except Exception as exc:
                self._log.error("Action failed in cue '%s': %s", cue.label, exc)

    def _play_or_wait(self, cue: NarrationCue) -> None:
        """Play audio or wait the equivalent duration."""
        if cue._audio_duration <= 0:
            return
        if self.play_audio and cue._audio_path:
            self._play_audio_blocking(cue._audio_path)
        else:
            time.sleep(cue._audio_duration)

    def _play_audio_blocking(self, audio_path: Path) -> None:
        """Play an audio file and block until it finishes."""
        try:
            proc = subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(audio_path)],
                timeout=60,
                capture_output=True,
            )
            if proc.returncode != 0:
                self._log.warning("ffplay returned %d", proc.returncode)
        except FileNotFoundError:
            self._log.warning("ffplay not found - falling back to duration wait")
            dur = self.narrator.get_narration_duration(audio_path)
            time.sleep(dur)
        except Exception as exc:
            self._log.error("Audio playback failed: %s", exc)

    def _play_audio_background(self, audio_path: Path) -> None:
        """Play audio in a background thread (non-blocking)."""
        thread = threading.Thread(
            target=self._play_audio_blocking,
            args=(audio_path,),
            daemon=True,
        )
        thread.start()

    def get_total_estimated_duration(self, cues: list[NarrationCue]) -> float:
        """Estimate total timeline duration from prepared cues."""
        total = 0.0
        for cue in cues:
            total += cue.pre_delay
            total += cue._audio_duration
            total += cue.post_delay
        return total
