"""
Demo Sequence — Example using basic VideoSequence
==================================================
Demonstrates the simpler VideoSequence approach with explicit wait() calls.

This approach is easier to write but timing is approximate (you manually
estimate how long each step takes). Use TimelineSequence when you want
precise narration synchronization.

For sequences that don't need narration synchronization — or where timing
is driven by the UI (e.g., waiting for a dialog) — this approach works well.
"""

from __future__ import annotations

import time
from toolkit.sequence import VideoSequence


class DemoSequence(VideoSequence):
    """Demo sequence: show how to type and save a file."""

    name = "Demo — Typing and Saving"
    sequence_id = "seq01_demo"
    duration_estimate = 30.0
    narration_text = (
        "Now let's type some text and save the file. "
        "Type your content in the editor. "
        "Then use Control+S to save."
    )
    obs_scene = "App Fullscreen"

    def execute(self, recorder, app, config):
        """Main automation steps for the demo sequence."""
        timing = config.get("timing", {})
        pause = timing.get("action_pause", 1.0)

        # Ensure app is visible and focused
        app.focus_window()
        app.wait(1.0)

        # Switch to the fullscreen scene
        try:
            recorder.switch_scene("App Fullscreen")
        except Exception:
            pass

        # Step 1: Click in the content area
        app.click_region("content_area")
        app.wait(0.5)

        # Step 2: Type some text
        demo_text = "Hello, world!\n\nThis is a tutorial video demonstration.\n"
        app.type_text_unicode(demo_text)
        app.wait(pause)

        # Step 3: Show a diagram (optional — requires OBS browser source or skip in headless)
        # self.show_diagram(recorder, "overview", duration=4.0)

        # Step 4: Select all text to highlight it
        app.select_all_text()
        app.wait(1.0)

        # Step 5: Click to deselect
        app.click_region("content_area", offset_x=50, offset_y=50)
        app.wait(0.5)

        # Step 6: Save the file
        app.save_file()
        app.wait(pause)

        # Step 7: Add more text
        app.type_text_unicode("\nLet's add another paragraph.\n")
        app.wait(0.5)

        # Step 8: Save again
        app.save_file()
        app.wait(pause)

        # Step 9: Find a word using Ctrl+F
        app.find_text("tutorial")
        app.wait(1.5)
        app.close_find_dialog()
        app.wait(pause)
