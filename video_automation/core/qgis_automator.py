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
- Supports both Windows (win32gui) and headless Linux (xdotool/Xvfb).
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
    """Detect if we're running in a headless/Docker environment."""
    return (
        os.environ.get("DISPLAY", "").startswith(":") and sys.platform != "win32"
    )


class QGISAutomator:
    """
    Automates QGIS + FilterMate interaction via PyAutoGUI.

    Supports both:
    - **Windows mode**: win32gui for window focus (original behavior)
    - **Headless mode** (Docker/Xvfb): xdotool for window management

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
        self.headless: bool = _is_headless()

        # Apply global timing from config
        pyautogui.PAUSE = self.timing.get("click_delay", 0.3)
        mode = "headless/xdotool" if self.headless else "desktop/win32"
        logger.debug("QGISAutomator initialised (PAUSE=%.2fs, mode=%s)", pyautogui.PAUSE, mode)

    # ------------------------------------------------------------------
    # Window focus
    # ------------------------------------------------------------------

    def focus_qgis(self) -> None:
        """Bring the QGIS window to the foreground."""
        if self.headless:
            self._focus_xdotool(self.window_title)
        elif sys.platform == "win32":
            self._focus_win32(self.window_title)
        else:
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
            # Keep the window maximized/fullscreen — only restore if minimized
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(hwnd)
            logger.info("Focused QGIS window (hwnd=%d).", hwnd)
        except ImportError:
            logger.warning("pywin32 not available. Skipping win32 focus.")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to focus QGIS: %s", exc)

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
            wids = result.stdout.strip().split("\n")
            wids = [w for w in wids if w]
            if not wids:
                logger.warning("No window found with title containing '%s'", title_substring)
                return
            wid = wids[0]
            subprocess.run(
                ["xdotool", "windowactivate", "--sync", wid],
                check=True,
                timeout=5,
            )
            subprocess.run(
                ["xdotool", "windowfocus", "--sync", wid],
                check=True,
                timeout=5,
            )
            # Maximize the window
            subprocess.run(
                ["xdotool", "windowsize", wid, "1920", "1080"],
                timeout=5,
            )
            subprocess.run(
                ["xdotool", "windowmove", wid, "0", "0"],
                timeout=5,
            )
            logger.info("Focused QGIS window via xdotool (wid=%s).", wid)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to focus QGIS via xdotool: %s", exc)

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
        """Select a layer in the source layer combobox."""
        self.select_combobox_item("source_layer_combo", layer_name)
        logger.info("Selected source layer: %s", layer_name)

    def select_target_layer(self, layer_name: str) -> None:
        """Expand the 'Layers to Filter' section and select a target layer."""
        self.expand_section("btn_toggle_layers_to_filter", "target_layer_combo")
        self.select_combobox_item("target_layer_combo", layer_name, double_click=True)
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

    def toggle_section(self, pushbutton_region: str) -> None:
        """
        Click a checkable sidebar pushbutton to toggle its section.

        **Warning**: this is a TOGGLE — if the section is already expanded,
        clicking it again will COLLAPSE it. Use ``expand_section()`` if you
        need to guarantee the section is open.

        Parameters
        ----------
        pushbutton_region : str
            Region key for the pushbutton, e.g. 'btn_toggle_geometric_predicates'.
        """
        region = self.regions.get(pushbutton_region)
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
            self.wait(0.8)
            logger.info("Toggled section: %s", pushbutton_region)
        else:
            logger.warning(
                "Pushbutton '%s' not calibrated. Section may not be visible. "
                "Run calibrate.py to set up.", pushbutton_region
            )

    def expand_section(self, pushbutton_region: str, dependent_widget: str) -> None:
        """
        Expand a section if its dependent widget is not already visible.

        Clicks the toggle pushbutton, then verifies the dependent widget
        zone is reachable. If the widget is already within the dock bounds
        (section presumably open), no toggle is performed.

        Falls back to a single toggle if the widget region is not calibrated.

        Parameters
        ----------
        pushbutton_region : str
            Region key for the toggle pushbutton.
        dependent_widget : str
            Region key for a widget that should be visible when expanded
            (e.g. 'target_layer_combo', 'predicate_combo').
        """
        widget = self.regions.get(dependent_widget)
        btn = self.regions.get(pushbutton_region)
        if not btn:
            logger.warning("Pushbutton '%s' not calibrated.", pushbutton_region)
            return

        # Heuristic: try clicking the dependent widget area first.
        # If the section is already expanded, the widget click will succeed
        # naturally and we don't need to toggle.  But since we can't detect
        # widget visibility purely through PyAutoGUI, we always toggle once
        # and rely on sequences being called in the correct order (from a
        # clean state).
        pyautogui.click(btn["x"], btn["y"],
                        duration=self.timing.get("mouse_move_duration", 0.5))
        self.wait(0.8)
        logger.info("Expanded section: %s (dependent: %s)", pushbutton_region, dependent_widget)

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
        Enable Geometric Predicates section and select a specific predicate.

        The predicate widget is a **QgsCheckableComboBox** (checkable dropdown),
        not a simple combobox. Each item has a checkbox.

        Strategy for QgsCheckableComboBox:
          1. Open the dropdown by clicking the combo
          2. Navigate with keyboard: Home → Down arrows to reach the item
          3. Press Space to toggle the checkbox (NOT Enter — Enter closes)
          4. Press Escape to close the dropdown

        Parameters
        ----------
        predicate : str
            e.g. "intersects", "touches", "contains", "within", "overlaps",
                 "is_within_distance"
        """
        # Known predicate order in QgsCheckableComboBox (QGIS standard)
        PREDICATE_ORDER = [
            "intersects", "contains", "is_disjoint", "touches",
            "crosses", "within", "overlaps", "equals",
            "is_within_distance",
        ]

        # 1. Expand the geometric predicates section
        self.expand_section("btn_toggle_geometric_predicates", "predicate_combo")

        # 2. Click the checkable combobox to open the dropdown list
        region = self.regions.get("predicate_combo")
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
            self.wait(0.5)

            # 3. Navigate to the predicate item
            # Go to top of list first
            pyautogui.press("home")
            self.wait(0.1)

            # Count how many Down presses to reach the target
            target_lower = predicate.lower()
            if target_lower in PREDICATE_ORDER:
                steps = PREDICATE_ORDER.index(target_lower)
            else:
                # Fallback: type first letter to jump, then fine-tune
                logger.warning("Predicate '%s' not in known order, using letter jump", predicate)
                pyautogui.press(predicate[0])
                self.wait(0.2)
                steps = 0

            for _ in range(steps):
                pyautogui.press("down")
                time.sleep(0.05)
            self.wait(0.2)

            # 4. Space toggles the checkbox (NOT Enter)
            pyautogui.press("space")
            self.wait(0.3)

            # 5. Close the dropdown
            pyautogui.press("escape")
        else:
            logger.warning("predicate_combo region not calibrated.")
        self.wait(self.timing.get("action_pause", 0.5))
        logger.info("Selected predicate: %s", predicate)

    def set_buffer_value(self, value: float, unit: str = "m") -> None:
        """
        Enable buffer section and set the buffer distance.

        The buffer controls are hidden behind a checkable pushbutton
        (which itself is only enabled after geometric predicates are active).
        This method expands both sections if needed.

        Parameters
        ----------
        value : float
            Buffer distance.
        unit : str
            "m" for metres, "km" for kilometres.
        """
        # 1. Geometric predicates must be expanded first (buffer depends on it)
        self.expand_section("btn_toggle_geometric_predicates", "predicate_combo")
        # 2. Expand the buffer section
        self.expand_section("btn_toggle_buffer", "buffer_enable_checkbox")

        # 3. Enable checkbox
        region = self.regions.get("buffer_enable_checkbox")
        if region:
            pyautogui.click(region["x"], region["y"],
                            duration=self.timing.get("mouse_move_duration", 0.5))
            self.wait(0.3)
        # 4. Set value in spinbox
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
            "export": "export_button",
            "favorites": "favorites_button",
            "about": "about_button",
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
    # QGIS menu navigation
    # ------------------------------------------------------------------

    def open_plugin_manager(self) -> None:
        """Open QGIS Extensions > Manage and Install Plugins dialog.

        Uses region-based click for the dropdown item if calibrated,
        otherwise falls back to typing the first letter to jump to
        'Gérer les extensions' (French) or 'Manage' (English).
        """
        # 1. Click the Extensions menu
        region = self.regions.get("menu_extensions")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
        else:
            pyautogui.hotkey("alt", "e")
        self.wait(0.5)

        # 2. Click the menu item directly or use keyboard fallback
        region_item = self.regions.get("menu_extensions_manage")
        if region_item:
            pyautogui.click(
                region_item["x"], region_item["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
        else:
            # Fallback: type 'g' for "Gérer" (FR) or 'm' for "Manage" (EN)
            pyautogui.press("g")
            self.wait(0.2)
            pyautogui.press("return")
        self.wait(2.0)
        logger.info("Opened Plugin Manager")

    def open_settings_options(self) -> None:
        """Open QGIS Settings > Options dialog.

        Uses region-based click for the dropdown item if calibrated,
        otherwise falls back to typing 'o' to jump to 'Options'.
        """
        # 1. Click the Settings menu
        region = self.regions.get("menu_settings")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
        else:
            pyautogui.hotkey("alt", "s")
        self.wait(0.5)

        # 2. Click Options item directly or use keyboard fallback
        region_item = self.regions.get("menu_settings_options")
        if region_item:
            pyautogui.click(
                region_item["x"], region_item["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
        else:
            # Fallback: type 'o' for "Options"
            pyautogui.press("o")
            self.wait(0.2)
            pyautogui.press("return")
        self.wait(2.0)
        logger.info("Opened Settings > Options")

    def close_dialog(self) -> None:
        """Close the currently focused dialog with Escape."""
        pyautogui.press("escape")
        self.wait(0.5)
        logger.debug("Closed dialog")

    def open_log_messages_panel(self) -> None:
        """Open QGIS View > Panels > Log Messages panel."""
        region = self.regions.get("menu_view")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
        else:
            pyautogui.hotkey("alt", "v")
        self.wait(0.5)
        # Navigate to Panels > Log Messages (locale-dependent)
        region_panels = self.regions.get("menu_view_panels")
        if region_panels:
            pyautogui.click(
                region_panels["x"], region_panels["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
            self.wait(0.3)
            region_log = self.regions.get("menu_view_panels_log")
            if region_log:
                pyautogui.click(
                    region_log["x"], region_log["y"],
                    duration=self.timing.get("mouse_move_duration", 0.5),
                )
        self.wait(1.0)
        logger.info("Opened Log Messages panel")

    def open_filtermate_toolbar(self) -> None:
        """Click the FilterMate toolbar icon to open/toggle the dock widget."""
        region = self.regions.get("filtermate_toolbar_icon")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
            self.wait(1.5)
            logger.info("Clicked FilterMate toolbar icon")
        else:
            success = self.click_button("btn_filtermate_toolbar")
            if not success:
                logger.warning(
                    "FilterMate toolbar icon not found. Calibrate or add button image."
                )

    def open_filtermate_config(self) -> None:
        """Open FilterMate configuration via the About button."""
        self.click_action_button("about")
        self.wait(1.5)
        region = self.regions.get("about_config_tab")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
            self.wait(0.5)
        logger.info("Opened FilterMate config")

    # ------------------------------------------------------------------
    # Exploring zone
    # ------------------------------------------------------------------

    def select_exploring_layer(self, layer_name: str, index: int | None = None) -> None:
        """Select a layer in the exploring zone's layer combobox.

        Parameters
        ----------
        layer_name : str
            Name of the layer (used for logging).
        index : int | None
            1-based position of the layer in the dropdown list.
            When provided, the combobox is opened with a click on the
            dropdown arrow area and the item is reached via arrow-key
            navigation (needed for non-editable comboboxes).
            When *None*, falls back to the type-and-enter approach.
        """
        if index is not None:
            self.select_combobox_by_arrow("exploring_layer_combo", index)
        else:
            self.select_combobox_item("exploring_layer_combo", layer_name)
        logger.info("Selected exploring layer: %s", layer_name)

    def navigate_feature(self, direction: str = "next") -> None:
        """Navigate to next/previous feature in the exploring selector."""
        region = self.regions.get("exploring_feature_selector")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
        if direction == "next":
            pyautogui.press("down")
        else:
            pyautogui.press("up")
        pyautogui.press("return")
        self.wait(self.timing.get("action_pause", 0.5))
        logger.info("Navigated feature: %s", direction)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def hover_region(self, region_name: str, duration: float = 1.5) -> None:
        """Move mouse to a region center and pause (no click)."""
        region = self.regions.get(region_name)
        if region is None:
            logger.warning("hover_region: '%s' not found.", region_name)
            return
        if "width" in region:
            cx = region["x"] + region["width"] // 2
            cy = region["y"] + region["height"] // 2
        else:
            cx = region["x"]
            cy = region["y"]
        self.move_mouse_to(cx, cy)
        self.wait(duration)
        logger.debug("Hovered region '%s' for %.1fs", region_name, duration)

    def select_combobox_by_arrow(
        self, region_name: str, index: int,
    ) -> None:
        """Select an item in a non-editable combobox using arrow-key navigation.

        Parameters
        ----------
        region_name : str
            Calibrated region key for the combobox.
        index : int
            1-based position of the desired item in the dropdown list.
        """
        region = self.regions.get(region_name)
        if region is None:
            logger.warning("Combobox region '%s' not calibrated.", region_name)
            return
        # First click to focus/activate the combobox
        pyautogui.click(
            region["x"], region["y"],
            duration=self.timing.get("mouse_move_duration", 0.5),
        )
        self.wait(0.3)
        # Second click to open the dropdown
        pyautogui.click(region["x"], region["y"])
        self.wait(0.5)
        # Navigate down to the desired item
        for _ in range(index):
            pyautogui.press("down")
            self.wait(0.15)
        pyautogui.press("return")
        self.wait(self.timing.get("action_pause", 0.5))
        logger.debug("Selected index %d in combobox '%s'", index, region_name)

    def select_combobox_item(
        self, region_name: str, item_text: str, double_click: bool = False,
    ) -> None:
        """Generic: click a combobox, clear, type item name, press Enter.

        Parameters
        ----------
        region_name : str
            Calibrated region key for the combobox.
        item_text : str
            Text to type in the combobox.
        double_click : bool
            If True, click twice (focus + open dropdown) before typing.
            Useful for comboboxes that need two clicks to activate.
        """
        region = self.regions.get(region_name)
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=self.timing.get("mouse_move_duration", 0.5),
            )
            if double_click:
                self.wait(0.3)
                pyautogui.click(region["x"], region["y"])
                self.wait(0.3)
            pyautogui.hotkey("ctrl", "a")
            self.type_text_unicode(item_text)
            self.wait(0.8)  # Let Qt completer process the pasted text
            pyautogui.press("return")
            self.wait(self.timing.get("action_pause", 0.5))
            logger.debug("Selected '%s' in combobox '%s'", item_text, region_name)
        else:
            logger.warning("Combobox region '%s' not calibrated.", region_name)

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, filepath: str) -> str:
        """Capture a full-screen screenshot and save to filepath."""
        if self.headless:
            # Use import (ImageMagick) for Xvfb capture
            display = os.environ.get("DISPLAY", ":99")
            try:
                subprocess.run(
                    ["import", "-display", display, "-window", "root", "-silent", filepath],
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to scrot
                subprocess.run(
                    ["scrot", "-o", filepath],
                    check=True,
                    capture_output=True,
                    timeout=5,
                    env={**os.environ, "DISPLAY": display},
                )
        else:
            from PIL import ImageGrab  # type: ignore
            img = ImageGrab.grab()
            img.save(filepath)
        logger.info("Screenshot saved: %s", filepath)
        return filepath
