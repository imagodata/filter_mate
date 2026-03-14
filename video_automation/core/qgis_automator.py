"""
QGIS Automator
==============
Controls QGIS and the FilterMate plugin via PyAutoGUI.

Usage:
    from core.qgis_automator import QGISAutomator
    qgis = QGISAutomator(config)
    qgis.focus_qgis()
    qgis.select_tab("FILTERING")
    qgis.select_layer("routes")
    qgis.click_action_button("filter")

Notes
-----
- pyautogui.FAILSAFE is True: move mouse to top-left corner to abort immediately.
- All coordinates are absolute screen pixels. Run calibrate.py first.
- Designed for Windows; win32gui is used to bring QGIS to the foreground.
"""

from __future__ import annotations

import logging
import math
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


class QGISAutomator:
    """
    Automates QGIS + FilterMate interaction via PyAutoGUI.

    Parameters
    ----------
    config : dict
        Full config dict loaded from config.yaml.
    """

    def __init__(self, config: dict) -> None:
        self.qgis_cfg: dict = config.get("qgis", {})
        self.timing: dict = config.get("timing", {})
        self.window_title: str = self.qgis_cfg.get("window_title", "QGIS")
        self.filtermate_panel: str = self.qgis_cfg.get("filtermate_panel", "FilterMate")
        self.regions: dict = self.qgis_cfg.get("regions", {})
        self._assets_dir = Path(__file__).parent.parent / "assets" / "buttons"

        # Apply global timing from config
        pyautogui.PAUSE = self.timing.get("click_delay", 0.3)
        logger.debug("QGISAutomator initialised (PAUSE=%.2fs)", pyautogui.PAUSE)

    # ------------------------------------------------------------------
    # Window focus
    # ------------------------------------------------------------------

    def focus_qgis(self) -> None:
        """Bring the QGIS window to the foreground."""
        if sys.platform == "win32":
            self._focus_win32(self.window_title)
        else:
            # Fallback: user must ensure QGIS is focused
            logger.warning(
                "Non-Windows platform detected. Please ensure QGIS is in the foreground."
            )
        wait_time = self.qgis_cfg.get("startup_wait", 3)
        self.wait(wait_time)

    def focus_filtermate(self) -> None:
        """Click on the FilterMate dock panel to ensure it has focus."""
        dock = self.regions.get("filtermate_dock", {})
        if dock:
            cx = dock.get("x", 0) + dock.get("width", 400) // 2
            cy = dock.get("y", 0) + 30  # Title bar area
            pyautogui.click(cx, cy, duration=self.timing.get("mouse_move_duration", 0.5))
            logger.debug("Clicked FilterMate dock at (%d, %d)", cx, cy)
        else:
            logger.warning("FilterMate dock region not calibrated.")

    def _focus_win32(self, title_substring: str) -> None:
        """Use win32gui to find and bring window to front."""
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
                raise RuntimeError(f"No window found with title containing '{title_substring}'")
            hwnd = hwnds[0]
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            logger.info("Focused QGIS window (hwnd=%d).", hwnd)
        except ImportError:
            logger.warning("pywin32 not available. Skipping win32 focus.")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to focus QGIS: %s", exc)

    # ------------------------------------------------------------------
    # Region-based clicks
    # ------------------------------------------------------------------

    def click_at(self, region_name: str, offset_x: int = 0, offset_y: int = 0) -> None:
        """
        Click the centre of a named calibrated region.

        Parameters
        ----------
        region_name : str
            Key from config.yaml qgis.regions.
        offset_x, offset_y : int
            Additional pixel offset from the centre.
        """
        region = self.regions.get(region_name)
        if region is None:
            raise ValueError(
                f"Region '{region_name}' not found in config. Run calibrate.py first."
            )
        # Regions can be either {x,y,width,height} or direct {x,y} point
        if "width" in region:
            cx = region["x"] + region["width"] // 2 + offset_x
            cy = region["y"] + region["height"] // 2 + offset_y
        else:
            cx = region["x"] + offset_x
            cy = region["y"] + offset_y
        self.move_mouse_to(cx, cy)
        pyautogui.click()
        logger.debug("Clicked region '%s' at (%d, %d)", region_name, cx, cy)

    def click_at_xy(self, x: int, y: int) -> None:
        """Click at absolute screen coordinates."""
        self.move_mouse_to(x, y)
        pyautogui.click()
        logger.debug("Clicked at (%d, %d)", x, y)

    # ------------------------------------------------------------------
    # Image-based clicks (fallback for dynamic UI elements)
    # ------------------------------------------------------------------

    def click_button(self, button_name: str, confidence: float = 0.85) -> bool:
        """
        Locate and click a button by image template matching.

        Images must exist in assets/buttons/<button_name>.png.
        Returns True if found and clicked, False otherwise.
        """
        img_path = self._assets_dir / f"{button_name}.png"
        if not img_path.exists():
            logger.warning(
                "Button image not found: %s. Use screenshot tool to capture it.", img_path
            )
            return False
        try:
            location = pyautogui.locateOnScreen(
                str(img_path), confidence=confidence
            )
            if location is None:
                logger.warning("Button '%s' not found on screen.", button_name)
                return False
            cx, cy = pyautogui.center(location)
            self.move_mouse_to(cx, cy)
            pyautogui.click()
            logger.info("Clicked image button '%s' at (%d, %d)", button_name, cx, cy)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Image click failed for '%s': %s", button_name, exc)
            return False

    # ------------------------------------------------------------------
    # FilterMate-specific interactions
    # ------------------------------------------------------------------

    def select_layer(self, layer_name: str) -> None:
        """
        Select a layer in the source layer combobox.
        Strategy: click the combobox, clear it, type the name, press Enter.
        """
        region = self.regions.get("source_layer_combo")
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
        else:
            self.click_at("filtermate_dock")

        pyautogui.hotkey("ctrl", "a")
        self.type_text(layer_name)
        pyautogui.press("return")
        self.wait(self.timing.get("action_pause", 1.0))
        logger.info("Selected source layer: %s", layer_name)

    def select_target_layer(self, layer_name: str) -> None:
        """Toggle the 'Layers to Filter' panel and select a target layer."""
        self.toggle_sidebar_button("layers_to_filter")
        self.wait(0.5)
        # Type the layer name in the search box (if available) or select from list
        self.type_text(layer_name)
        pyautogui.press("return")
        self.wait(self.timing.get("action_pause", 1.0))
        logger.info("Selected target layer: %s", layer_name)

    def select_tab(self, tab_name: str) -> None:
        """
        Click a main tab in the FilterMate dockwidget.

        Parameters
        ----------
        tab_name : str
            One of: "FILTERING", "EXPLORING", "EXPORTING"  (case-insensitive).
        """
        tab_map = {
            "filtering": "tab_filtering",
            "exploring": "tab_exploring",
            "exporting": "tab_exporting",
        }
        key = tab_name.lower()
        region_key = tab_map.get(key)
        if region_key is None:
            raise ValueError(
                f"Unknown tab: '{tab_name}'. Valid values: FILTERING, EXPLORING, EXPORTING"
            )
        region = self.regions.get(region_key)
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
        else:
            logger.warning("Tab region '%s' not calibrated.", region_key)
        self.wait(self.timing.get("action_pause", 0.5))
        logger.info("Selected tab: %s", tab_name)

    def toggle_sidebar_button(self, button_name: str) -> None:
        """
        Click a sidebar toggle button (e.g., 'layers_to_filter', 'predicates').
        Falls back to image recognition if no region is calibrated.
        """
        region = self.regions.get(button_name)
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
            logger.info("Toggled sidebar button: %s", button_name)
        else:
            success = self.click_button(button_name)
            if not success:
                logger.error("Could not find sidebar button '%s'. Calibrate or add button image.", button_name)
        self.wait(0.3)

    def select_predicate(self, predicate: str) -> None:
        """
        Enable Geometric Predicates and select a specific predicate.

        Parameters
        ----------
        predicate : str
            e.g. "intersects", "touches", "contains", "within", "overlaps",
                 "is_within_distance"
        """
        region = self.regions.get("predicate_combo")
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
            pyautogui.hotkey("ctrl", "a")
            self.type_text(predicate)
            # Optionally press Down to select from dropdown
            pyautogui.press("down")
            pyautogui.press("return")
        else:
            logger.warning("predicate_combo region not calibrated.")
        self.wait(self.timing.get("action_pause", 0.5))
        logger.info("Selected predicate: %s", predicate)

    def set_buffer_value(self, value: float, unit: str = "m") -> None:
        """
        Enable buffer and set the buffer distance.

        Parameters
        ----------
        value : float
            Buffer distance.
        unit : str
            "m" for metres, "km" for kilometres.
        """
        # Enable checkbox
        region = self.regions.get("buffer_enable_checkbox")
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
            self.wait(0.3)
        # Set value in spinbox
        spinbox = self.regions.get("buffer_value_spinbox")
        if spinbox:
            pyautogui.triple_click(spinbox["x"], spinbox["y"])
            self.type_text(str(value))
        self.wait(self.timing.get("action_pause", 0.5))
        logger.info("Set buffer to %s %s", value, unit)

    def click_action_button(self, action: str) -> None:
        """
        Click a main action button.

        Parameters
        ----------
        action : str
            One of: "filter", "undo", "redo", "unfilter", "export", "about"
        """
        region_map = {
            "filter": "filter_button",
            "undo": "undo_button",
            "redo": "redo_button",
            "unfilter": "unfilter_button",
            "favorites": "favorites_button",
            "export": "filter_button",  # remapped based on context
        }
        region_key = region_map.get(action.lower())
        if region_key is None:
            logger.warning("Unknown action button: %s", action)
            return
        region = self.regions.get(region_key)
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
        else:
            success = self.click_button(f"btn_{action.lower()}")
            if not success:
                logger.error("Action button '%s' not found. Calibrate first.", action)
                return
        pause = self.timing.get("action_pause", 1.0)
        if action.lower() == "filter":
            pause = max(pause, 2.0)  # Allow time for query to complete
        self.wait(pause)
        logger.info("Clicked action button: %s", action)

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    def type_text(self, text: str, interval: Optional[float] = None) -> None:
        """Type text with natural keystroke timing."""
        if interval is None:
            interval = self.timing.get("type_delay", 0.05)
        pyautogui.typewrite(text, interval=interval)
        logger.debug("Typed: %r", text)

    def type_text_unicode(self, text: str) -> None:
        """Type unicode text (accented characters etc.) via clipboard paste."""
        try:
            import pyperclip  # type: ignore

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        except ImportError:
            logger.warning("pyperclip not available; using typewrite (may fail for unicode).")
            self.type_text(text)
        logger.debug("Pasted unicode text: %r", text)

    # ------------------------------------------------------------------
    # Scrolling
    # ------------------------------------------------------------------

    def scroll_down(self, clicks: int = 3) -> None:
        """Scroll down in the currently focused widget."""
        for _ in range(clicks):
            pyautogui.scroll(-3)
            time.sleep(self.timing.get("scroll_delay", 0.2))
        logger.debug("Scrolled down %d clicks", clicks)

    def scroll_up(self, clicks: int = 3) -> None:
        """Scroll up in the currently focused widget."""
        for _ in range(clicks):
            pyautogui.scroll(3)
            time.sleep(self.timing.get("scroll_delay", 0.2))
        logger.debug("Scrolled up %d clicks", clicks)

    # ------------------------------------------------------------------
    # Mouse movement
    # ------------------------------------------------------------------

    def move_mouse_to(self, x: int, y: int, duration: Optional[float] = None) -> None:
        """Move the mouse smoothly to absolute screen coordinates."""
        if duration is None:
            duration = self.timing.get("mouse_move_duration", 0.5)
        pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeOutQuad)

    def highlight_area(self, region_name: str, duration: float = 2.0) -> None:
        """
        Draw attention to a region by slowly circling the mouse around it.

        Parameters
        ----------
        region_name : str
            Calibrated region name, or pass a dict with x/y/width/height directly.
        duration : float
            Total time (seconds) to spend circling.
        """
        region = self.regions.get(region_name) if isinstance(region_name, str) else region_name
        if region is None:
            logger.warning("highlight_area: region '%s' not found.", region_name)
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

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------

    def wait(self, seconds: float) -> None:
        """Sleep with a periodic progress log for long waits."""
        if seconds <= 0:
            return
        if seconds <= 2:
            time.sleep(seconds)
        else:
            logger.info("Waiting %.1fs…", seconds)
            time.sleep(seconds)

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, filepath: str) -> str:
        """Capture a full-screen screenshot and save to filepath."""
        from PIL import ImageGrab  # type: ignore

        img = ImageGrab.grab()
        img.save(filepath)
        logger.info("Screenshot saved: %s", filepath)
        return filepath
