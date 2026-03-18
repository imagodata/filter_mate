"""
Intro Sequence — Example using TimelineSequence
================================================
Demonstrates narration-synchronized automation using NarrationCue.

The TimelineSequence approach:
  1. Define cues with text + actions
  2. TTS audio is pre-generated automatically
  3. Actions are synchronized to audio duration
  4. Timecodes are recorded for post-production assembly

Sync modes:
  "during" (default): actions run parallel to narration
  "before":           actions run first, then narration plays
  "after":            narration plays first, then actions run
"""

from __future__ import annotations

from toolkit.sequence import TimelineSequence
from toolkit.timeline import NarrationCue


class IntroSequence(TimelineSequence):
    """Introduction sequence: show the app and explain what we'll cover."""

    name = "Introduction"
    sequence_id = "seq00_intro"
    duration_estimate = 20.0
    obs_scene = "App Fullscreen"

    def build_timeline(self, recorder, app, config):
        """
        Build the narration timeline for the intro sequence.

        Each NarrationCue pairs a voiceover line with UI automation actions.
        The executor handles timing: if actions finish before the voiceover,
        it pads with silence. If narration finishes first, actions continue.
        """
        return [
            NarrationCue(
                text="Welcome to this tutorial on My App.",
                actions=lambda: app.wait(1.0),
                sync="during",
                post_delay=0.5,
            ),
            NarrationCue(
                text="In this tutorial, we will cover the basic features "
                     "of the application.",
                actions=lambda: app.focus_window(),
                sync="during",
                post_delay=0.5,
            ),
            NarrationCue(
                text="Let's start by opening the application and creating a new file.",
                actions=lambda: _open_new_file(app),
                sync="during",
                post_delay=1.0,
            ),
            NarrationCue(
                text="The interface is simple and intuitive.",
                actions=lambda: app.wait(2.0),
                sync="during",
                post_delay=0.5,
            ),
        ]


def _open_new_file(app) -> None:
    """Open a new file and wait for it to appear."""
    app.new_file()
    app.wait(1.0)
