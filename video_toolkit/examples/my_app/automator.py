"""
Notepad Automator — Example App-Specific Automator
====================================================
This demonstrates how to subclass AppAutomator for a specific application.

Replace "Notepad" with your actual application and add methods for
every interaction you need in your sequences.

The base class (AppAutomator) already provides:
  - focus_window()        — bring app to foreground
  - click_region(name)    — click a calibrated region
  - click_image(name)     — click by image template
  - type_text(text)       — keyboard input
  - type_text_unicode()   — clipboard paste for unicode
  - hotkey(*keys)         — keyboard shortcut
  - press_key(key)        — single key press
  - scroll(n, direction)  — mouse wheel
  - move_to(x, y)         — smooth mouse movement
  - highlight(region)     — visual attention circle
  - hover(region)         — hover without clicking
  - wait(seconds)         — timed pause
  - screenshot(path)      — capture screen
  - clear_field()         — Ctrl+A, Delete
  - close_dialog()        — Escape
"""

from __future__ import annotations

import logging
from toolkit.app_automator import AppAutomator

logger = logging.getLogger(__name__)


class NotepadAutomator(AppAutomator):
    """
    Automates Notepad (or any simple text editor) interactions.

    All coordinates come from config.yaml regions (calibrated with
    scripts/calibrate.py).
    """

    # ------------------------------------------------------------------
    # Application-specific methods
    # ------------------------------------------------------------------

    def open_file_menu(self) -> None:
        """Open the File menu."""
        self.click_region("menu_file")
        self.wait(self.timing.get("action_pause", 0.5))
        logger.info("Opened File menu")

    def open_edit_menu(self) -> None:
        """Open the Edit menu."""
        self.click_region("menu_edit")
        self.wait(self.timing.get("action_pause", 0.5))
        logger.info("Opened Edit menu")

    def new_file(self) -> None:
        """Create a new document (Ctrl+N)."""
        self.hotkey("ctrl", "n")
        self.wait(1.0)
        logger.info("Created new file")

    def open_file(self) -> None:
        """Open file dialog (Ctrl+O)."""
        self.hotkey("ctrl", "o")
        self.wait(1.0)
        logger.info("Opened file dialog")

    def save_file(self) -> None:
        """Save the current file (Ctrl+S)."""
        self.hotkey("ctrl", "s")
        self.wait(1.0)
        logger.info("Saved file")

    def select_all_text(self) -> None:
        """Select all text in the editor (Ctrl+A)."""
        # Click in content area first to make sure editor has focus
        self.click_region("content_area")
        self.hotkey("ctrl", "a")
        self.wait(0.3)
        logger.info("Selected all text")

    def delete_all_text(self) -> None:
        """Clear all text in the editor."""
        self.click_region("content_area")
        self.hotkey("ctrl", "a")
        self.press_key("delete")
        self.wait(0.3)
        logger.info("Deleted all text")

    def type_in_editor(self, text: str) -> None:
        """Click the content area and type text."""
        self.click_region("content_area")
        self.wait(0.3)
        self.type_text_unicode(text)
        logger.info("Typed text in editor: %r...", text[:30])

    def find_text(self, search_term: str) -> None:
        """Open Find dialog and search for text (Ctrl+F)."""
        self.hotkey("ctrl", "f")
        self.wait(0.5)
        self.type_text(search_term)
        self.press_key("return")
        self.wait(0.5)
        logger.info("Searched for: %r", search_term)

    def close_find_dialog(self) -> None:
        """Close the Find dialog."""
        self.close_dialog()
        logger.info("Closed Find dialog")

    def zoom_in(self) -> None:
        """Zoom in (Ctrl+Plus in some editors)."""
        self.hotkey("ctrl", "+")
        self.wait(0.3)
        logger.info("Zoomed in")

    def zoom_out(self) -> None:
        """Zoom out (Ctrl+Minus)."""
        self.hotkey("ctrl", "-")
        self.wait(0.3)
        logger.info("Zoomed out")

    def show_status_bar(self) -> None:
        """Toggle status bar visibility via View menu."""
        self.click_region("menu_view")
        self.wait(0.3)
        # Notepad's View menu has a "Status Bar" item — adjust key navigation for your app
        import pyautogui  # type: ignore
        pyautogui.press("s")  # "s" for "Status Bar" on English Notepad
        self.wait(0.5)
        logger.info("Toggled status bar")
