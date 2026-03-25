"""
Timeline — Narration-synchronized execution
=============================================
Provides a cue-based system where narration segments are paired with UI
actions. Each cue knows its audio duration, so actions are timed precisely
to match the voiceover.

Usage in a sequence::

    class MySequence(TimelineSequence):
        def build_timeline(self, obs, qgis, config):
            return [
                NarrationCue(
                    text="Bienvenue dans FilterMate.",
                    actions=lambda: qgis.wait(1.0),
                ),
                NarrationCue(
                    text="Ouvrons le plugin.",
                    actions=lambda: qgis.open_filtermate_toolbar(),
                    post_delay=1.0,
                ),
            ]
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from core.narrator import Narrator

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
        UI actions to execute during this cue.  Called with no arguments.
        Use a lambda or closure that captures ``obs``, ``qgis``, ``config``.
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
        If set, switch OBS to this scene before executing this cue.
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
            # Derive label from first ~50 chars of text
            self.label = self.text[:50].rstrip() + ("…" if len(self.text) > 50 else "")


@dataclass
class TimelineResult:
    """Result of executing a timeline — used for post-production."""

    cues: list[NarrationCue]
    total_duration: float
    # List of (timecode_seconds, audio_path) for each narration segment
    narration_timecodes: list[tuple[float, Path]]


class TimelineExecutor:
    """
    Executes a list of NarrationCues with precise timing.

    1. Pre-generates TTS audio for each cue (if not already done).
    2. Measures audio durations.
    3. During recording, plays audio and/or runs actions with correct timing.

    Parameters
    ----------
    narrator : Narrator
        TTS engine for generating audio segments.
    sequence_id : str
        Used for naming audio segment files.
    cache_dir : Path or None
        Directory for cached audio segments.  Defaults to output/narration/segments/.
    play_audio : bool
        If True, play narration audio through speakers during recording
        (so OBS captures it).  If False, only use durations for timing
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
        self._log.info("Preparing %d cues…", len(cues))
        for i, cue in enumerate(cues):
            if not cue.text:
                cue._audio_path = None
                cue._audio_duration = 0.0
                continue

            audio_file = self.cache_dir / f"{self.sequence_id}_cue{i:02d}.mp3"

            # Regenerate if text changed or file doesn't exist
            if audio_file.exists():
                # Check if cached version matches (simple size check)
                cue._audio_path = audio_file
                cue._audio_duration = self.narrator.get_narration_duration(audio_file)
                self._log.debug(
                    "Cue %d cached: %.1fs — %s", i, cue._audio_duration, cue.label
                )
            else:
                cue._audio_path = self.narrator.generate_narration(
                    cue.text, audio_file
                )
                cue._audio_duration = self.narrator.get_narration_duration(audio_file)
                self._log.info(
                    "Cue %d generated: %.1fs — %s", i, cue._audio_duration, cue.label
                )

    def execute(self, cues: list[NarrationCue], obs=None) -> TimelineResult:
        """
        Execute the timeline: play narration + run actions with precise timing.

        Parameters
        ----------
        cues : list[NarrationCue]
            Prepared cues (call ``prepare()`` first).
        obs : OBSController or FrameCapturer, optional
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
            if cue.scene and obs:
                try:
                    obs.switch_scene(cue.scene)
                except Exception as exc:
                    self._log.warning("Scene switch failed: %s", exc)

            # Execute based on sync mode.
            # Timecode is recorded at the moment narration should start
            # playing in post-production — this varies by sync mode.
            if cue.sync == "before":
                # Actions first, THEN narration
                self._run_actions(cue)
                narration_start = time.time() - timeline_start
                if cue._audio_path:
                    narration_timecodes.append((narration_start, cue._audio_path))
                self._play_or_wait(cue)
            elif cue.sync == "after":
                # Narration first, THEN actions
                narration_start = time.time() - timeline_start
                if cue._audio_path:
                    narration_timecodes.append((narration_start, cue._audio_path))
                self._play_or_wait(cue)
                self._run_actions(cue)
            else:  # "during" (default)
                # Narration and actions start simultaneously
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
            # No actions, just play/wait the narration
            self._play_or_wait(cue)
            return

        if not cue._audio_duration:
            # No narration, just run actions
            self._run_actions(cue)
            return

        # Both narration and actions: start audio first (background),
        # then run actions, then pad remaining time if needed.
        if self.play_audio and cue._audio_path:
            # Start audio playback in background so it plays alongside actions
            self._play_audio_background(cue._audio_path)

        action_start = time.time()
        self._run_actions(cue)
        action_elapsed = time.time() - action_start

        # If actions were shorter than narration, wait the difference
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
            # Just wait the narration duration (mix audio in post)
            time.sleep(cue._audio_duration)

    def _play_audio_blocking(self, audio_path: Path) -> None:
        """Play an audio file and block until it finishes."""
        try:
            # Use ffplay (from FFmpeg) for cross-platform audio playback
            proc = subprocess.run(
                [
                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                    str(audio_path),
                ],
                timeout=60,
                capture_output=True,
            )
            if proc.returncode != 0:
                self._log.warning("ffplay returned %d", proc.returncode)
        except FileNotFoundError:
            self._log.warning("ffplay not found — falling back to duration wait")
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
            # Rough estimate for action time in "after"/"before" modes
            total += cue.post_delay
        return total
