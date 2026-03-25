"""
App Automator — Generic Desktop App Automation
===============================================
Base class for automating any desktop application via PyAutoGUI.
Supports both Windows (win32gui) and Linux/headless (xdotool/Xvfb).

Subclass this for your specific application and add app-specific
interaction methods (menus, dialogs, toolbars, etc.).

Usage:
    from toolkit.app_automator import AppAutomator

    class NotepadAutomator(AppAutomator):
        def type_in_editor(self, text: str):
            self.click_region("editor")
            self.type_text(text)

    automator = NotepadAutomator(config)
    automator.focus_window()
    automator.type_in_editor("Hello, world!")

Notes:
  - pyautogui.FAILSAFE is True: move mouse to top-left corner to abort.
  - All coordinates are absolute screen pixels. Run calibrate.py first.
  - Supports Windows (win32gui) and headless Linux (xdotool/Xvfb).
"""

from __future__ import annotations

import logging
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True
except ImportError as exc:
    raise ImportError("pyautogui is not installed. Run: pip install pyautogui") from exc


def _is_headless() -> bool:
    """Detect if we're running in a headless/Docker/Xvfb environment."""
    return (
        os.environ.get("DISPLAY", "").startswith(":") and sys.platform != "win32"
    )


class AppAutomator:
    """
    Generic desktop application automation via PyAutoGUI.

    Subclass this to create an automator for your specific application.
    Add app-specific methods (click menus, fill forms, navigate dialogs)
    in the subclass while inheriting all the generic primitives here.

    Parameters
    ----------
    config : dict
        Full config dict loaded from config.yaml.
        Expected keys:
          - window_title: str — title substring to identify the app window
          - regions: dict — calibrated UI element positions
          - timing: dict — timing parameters (click_delay, etc.)
    """

    def __init__(self, config: dict) -> None:
        # Support both flat config and nested under an app key
        app_cfg: dict = config.get("app", config)
        self.timing: dict = config.get("timing", {})
        self.window_title: str = app_cfg.get("window_title", "")
        self.regions: dict = app_cfg.get("regions", {})
        self._assets_dir = Path(app_cfg.get("assets_dir", "assets/buttons"))
        self.headless: bool = _is_headless()

        # Apply global timing from config
        pyautogui.PAUSE = self.timing.get("click_delay", 0.3)
        mode = "headless/xdotool" if self.headless else "desktop/win32"
        logger.debug(
            "AppAutomator initialised (PAUSE=%.2fs, mode=%s, title=%r)",
            pyautogui.PAUSE, mode, self.window_title,
        )

    # ------------------------------------------------------------------
    # Window focus
    # ------------------------------------------------------------------

    def focus_window(self) -> None:
        """Bring the application window to the foreground."""
        if not self.window_title:
            logger.warning("window_title not configured — skipping focus")
            return

        if self.headless:
            self._focus_xdotool(self.window_title)
        elif sys.platform == "win32":
            self._focus_win32(self.window_title)
        else:
            logger.warning(
                "Non-Windows platform without DISPLAY. Ensure the app is in the foreground."
            )

        wait_time = self.timing.get("startup_wait", 2.0)
        self.wait(wait_time)

    def _focus_win32(self, title_substring: str) -> None:
        """Use win32gui to find and bring window to front (Windows only)."""
        try:
            import win32gui  # type: ignore
            import win32con  # type: ignore

            def _enum_cb(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    text = win32gui.GetWindowText(hwnd)
                    if title_substring.lower() in text.lower():
                        results.append(hwnd)

            hwnds: list[int] = []
            win32gui.EnumWindows(_enum_cb, hwnds)
            if not hwnds:
                raise RuntimeError(
                    f"No window found with title containing '{title_substring}'"
                )
            hwnd = hwnds[0]
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(hwnd)
            logger.info("Focused window (hwnd=%d, title=%r).", hwnd, title_substring)
        except ImportError:
            logger.warning("pywin32 not available. Skipping win32 focus.")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to focus window: %s", exc)

    def _focus_xdotool(self, title_substring: str) -> None:
        """Use xdotool to find and bring window to front (headless/Linux)."""
        if not shutil.which("xdotool"):
            logger.warning("xdotool not available. Skipping focus.")
            return
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", title_substring],
                capture_output=True,
                text=True,
                timeout=5,
            )
            wids = [w for w in result.stdout.strip().split("\n") if w]
            if not wids:
                logger.warning(
                    "No window found with title containing '%s'", title_substring
                )
                return
            wid = wids[0]
            subprocess.run(["xdotool", "windowactivate", "--sync", wid], check=True, timeout=5)
            subprocess.run(["xdotool", "windowfocus", "--sync", wid], check=True, timeout=5)
            # Maximize the window
            subprocess.run(["xdotool", "windowsize", wid, "1920", "1080"], timeout=5)
            subprocess.run(["xdotool", "windowmove", wid, "0", "0"], timeout=5)
            logger.info("Focused window via xdotool (wid=%s, title=%r).", wid, title_substring)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to focus window via xdotool: %s", exc)

    # ------------------------------------------------------------------
    # Region-based clicks
    # ------------------------------------------------------------------

    def click_region(self, region_name: str, offset_x: int = 0, offset_y: int = 0) -> None:
        """
        Click the centre of a named calibrated region.

        Parameters
        ----------
        region_name : str
            Key from config.yaml regions (calibrated via calibrate.py).
        offset_x, offset_y : int
            Additional pixel offset from the centre.
        """
        region = self.regions.get(region_name)
        if region is None:
            raise ValueError(
                f"Region '{region_name}' not found in config. Run calibrate.py first."
            )
        if "width" in region:
            cx = region["x"] + region["width"] // 2 + offset_x
            cy = region["y"] + region["height"] // 2 + offset_y
        else:
            cx = region["x"] + offset_x
            cy = region["y"] + offset_y
        self.move_to(cx, cy)
        pyautogui.click()
        logger.debug("Clicked region '%s' at (%d, %d)", region_name, cx, cy)

    def click_at(self, x: int, y: int) -> None:
        """Click at absolute screen coordinates."""
        self.move_to(x, y)
        pyautogui.click()
        logger.debug("Clicked at (%d, %d)", x, y)

    def double_click_region(self, region_name: str) -> None:
        """Double-click the centre of a named calibrated region."""
        region = self.regions.get(region_name)
        if region is None:
            raise ValueError(f"Region '{region_name}' not found in config.")
        if "width" in region:
            cx = region["x"] + region["width"] // 2
            cy = region["y"] + region["height"] // 2
        else:
            cx, cy = region["x"], region["y"]
        self.move_to(cx, cy)
        pyautogui.doubleClick()
        logger.debug("Double-clicked region '%s' at (%d, %d)", region_name, cx, cy)

    def right_click_region(self, region_name: str) -> None:
        """Right-click the centre of a named calibrated region."""
        region = self.regions.get(region_name)
        if region is None:
            raise ValueError(f"Region '{region_name}' not found in config.")
        if "width" in region:
            cx = region["x"] + region["width"] // 2
            cy = region["y"] + region["height"] // 2
        else:
            cx, cy = region["x"], region["y"]
        self.move_to(cx, cy)
        pyautogui.rightClick()
        logger.debug("Right-clicked region '%s' at (%d, %d)", region_name, cx, cy)

    # ------------------------------------------------------------------
    # Image-based clicks (fallback for dynamic UI elements)
    # ------------------------------------------------------------------

    def click_image(self, image_name: str, confidence: float = 0.85) -> bool:
        """
        Locate and click an element by image template matching.

        Images must exist at self._assets_dir / <image_name>.png.

        Parameters
        ----------
        image_name : str
            Filename (without .png) in the assets/buttons directory.
        confidence : float
            Match confidence threshold (0.0–1.0).

        Returns
        -------
        bool
            True if found and clicked, False otherwise.
        """
        img_path = self._assets_dir / f"{image_name}.png"
        if not img_path.exists():
            logger.warning(
                "Button image not found: %s. Capture it with pyautogui.screenshot().", img_path
            )
            return False
        try:
            location = pyautogui.locateOnScreen(str(img_path), confidence=confidence)
            if location is None:
                logger.warning("Image '%s' not found on screen.", image_name)
                return False
            cx, cy = pyautogui.center(location)
            self.move_to(cx, cy)
            pyautogui.click()
            logger.info("Clicked image '%s' at (%d, %d)", image_name, cx, cy)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Image click failed for '%s': %s", image_name, exc)
            return False

    # ------------------------------------------------------------------
    # Keyboard input
    # ------------------------------------------------------------------

    def type_text(self, text: str, interval: Optional[float] = None) -> None:
        """Type text with natural keystroke timing."""
        if interval is None:
            interval = self.timing.get("type_delay", 0.05)
        pyautogui.typewrite(text, interval=interval)
        logger.debug("Typed: %r", text)

    def type_text_unicode(self, text: str) -> None:
        """
        Type unicode text (accented characters etc.) via clipboard paste.

        Falls back to typewrite if pyperclip is not available.
        """
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        except ImportError:
            logger.warning("pyperclip not available; using typewrite (may fail for unicode).")
            self.type_text(text)
        logger.debug("Pasted unicode text: %r", text)

    def hotkey(self, *keys: str) -> None:
        """Press a keyboard shortcut (e.g. hotkey('ctrl', 'z') for undo)."""
        pyautogui.hotkey(*keys)
        logger.debug("Hotkey: %s", "+".join(keys))

    def press_key(self, key: str, presses: int = 1) -> None:
        """Press a key one or more times."""
        pyautogui.press(key, presses=presses)
        logger.debug("Key press: %s x%d", key, presses)

    # ------------------------------------------------------------------
    # Mouse operations
    # ------------------------------------------------------------------

    def move_to(self, x: int, y: int, duration: Optional[float] = None) -> None:
        """Move the mouse smoothly to absolute screen coordinates."""
        if duration is None:
            duration = self.timing.get("mouse_move_duration", 0.5)
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeOutQuad)

    def scroll(self, clicks: int, direction: str = "down") -> None:
        """
        Scroll the mouse wheel.

        Parameters
        ----------
        clicks : int
            Number of scroll steps.
        direction : str
            "down" (negative) or "up" (positive).
        """
        amount = -clicks if direction == "down" else clicks
        scroll_delay = self.timing.get("scroll_delay", 0.2)
        for _ in range(abs(clicks)):
            pyautogui.scroll(int(amount / abs(clicks)) if clicks else 0)
            time.sleep(scroll_delay)
        logger.debug("Scrolled %s %d clicks", direction, clicks)

    def drag(
        self,
        start_x: int, start_y: int,
        end_x: int, end_y: int,
        duration: Optional[float] = None,
    ) -> None:
        """Drag from one screen position to another."""
        if duration is None:
            duration = self.timing.get("mouse_move_duration", 0.5)
        pyautogui.moveTo(start_x, start_y, duration=0.2)
        pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
        logger.debug("Dragged (%d,%d) -> (%d,%d)", start_x, start_y, end_x, end_y)

    # ------------------------------------------------------------------
    # Visual attention / highlighting
    # ------------------------------------------------------------------

    def highlight(self, region_name: str, duration: float = 2.0) -> None:
        """
        Draw attention to a region by slowly circling the mouse around it.

        Parameters
        ----------
        region_name : str
            Calibrated region name.
        duration : float
            Total time (seconds) to spend circling.
        """
        region = self.regions.get(region_name) if isinstance(region_name, str) else region_name
        if region is None:
            logger.warning("highlight: region '%s' not found.", region_name)
            return

        cx = region.get("x", 0) + region.get("width", 100) // 2
        cy = region.get("y", 0) + region.get("height", 60) // 2
        radius = min(region.get("width", 80), region.get("height", 60)) * 0.4

        steps = 60
        step_delay = duration / steps
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            nx = int(cx + radius * math.cos(angle))
            ny = int(cy + radius * math.sin(angle))
            pyautogui.moveTo(nx, ny, duration=step_delay)
        logger.debug("Highlighted region '%s' for %.1fs", region_name, duration)

    def hover(self, region_name: str, duration: float = 1.5) -> None:
        """Move mouse to a region center and pause (no click)."""
        region = self.regions.get(region_name)
        if region is None:
            logger.warning("hover: region '%s' not found.", region_name)
            return
        if "width" in region:
            cx = region["x"] + region["width"] // 2
            cy = region["y"] + region["height"] // 2
        else:
            cx, cy = region["x"], region["y"]
        self.move_to(cx, cy)
        self.wait(duration)
        logger.debug("Hovered region '%s' for %.1fs", region_name, duration)

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def wait(self, seconds: float) -> None:
        """Sleep for the given number of seconds."""
        if seconds <= 0:
            return
        if seconds > 2:
            logger.info("Waiting %.1fs...", seconds)
        time.sleep(seconds)

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, filepath: str) -> str:
        """Capture a full-screen screenshot and save to filepath."""
        if self.headless:
            display = os.environ.get("DISPLAY", ":99")
            try:
                subprocess.run(
                    ["import", "-display", display, "-window", "root", "-silent", filepath],
                    check=True, capture_output=True, timeout=5,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                subprocess.run(
                    ["scrot", "-o", filepath],
                    check=True, capture_output=True, timeout=5,
                    env={**os.environ, "DISPLAY": display},
                )
        else:
            try:
                from PIL import ImageGrab  # type: ignore
                img = ImageGrab.grab()
                img.save(filepath)
            except ImportError:
                import pyautogui as pag
                pag.screenshot(filepath)
        logger.info("Screenshot saved: %s", filepath)
        return filepath

    # ------------------------------------------------------------------
    # Generic dialog helpers
    # ------------------------------------------------------------------

    def close_dialog(self) -> None:
        """Close the currently focused dialog with Escape."""
        pyautogui.press("escape")
        self.wait(0.5)
        logger.debug("Closed dialog")

    def select_all(self) -> None:
        """Select all text in the current field (Ctrl+A)."""
        pyautogui.hotkey("ctrl", "a")

    def clear_field(self) -> None:
        """Clear the current text field (Ctrl+A, Delete)."""
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("delete")

    def confirm_dialog(self) -> None:
        """Confirm the current dialog (Enter key)."""
        pyautogui.press("return")
        self.wait(0.5)

    def undo(self) -> None:
        """Undo (Ctrl+Z)."""
        pyautogui.hotkey("ctrl", "z")

    def redo(self) -> None:
        """Redo (Ctrl+Y)."""
        pyautogui.hotkey("ctrl", "y")

    def copy(self) -> None:
        """Copy selection (Ctrl+C)."""
        pyautogui.hotkey("ctrl", "c")

    def paste(self) -> None:
        """Paste clipboard (Ctrl+V)."""
        pyautogui.hotkey("ctrl", "v")

    def save(self) -> None:
        """Save (Ctrl+S)."""
        pyautogui.hotkey("ctrl", "s")
