"""
V01 Sequence 7 — THEME SOMBRE AUTOMATIQUE (5:00 - 5:20)
========================================================
Basculer QGIS en theme sombre, montrer FilterMate qui s'adapte.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S07DarkTheme(VideoSequence):
    name = "V01 — Theme sombre automatique"
    sequence_id = "v01_s07"
    duration_estimate = 20.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = []
    narration_text = V01_NARRATION_TEXTS["v01_s07"]

    def execute(self, obs, qgis, config):
        import pyautogui

        regions = config["qgis"]["regions"]
        move_dur = config["timing"].get("mouse_move_duration", 0.5)

        qgis.focus_qgis()
        qgis.wait(0.5)

        # 1. Show current (light) theme
        qgis.focus_filtermate()
        qgis.wait(1.5)

        # 2. Open QGIS Settings > Options (robust navigation)
        self._log.info("Opening QGIS Options for theme switch")
        qgis.open_settings_options()
        qgis.wait(1.0)

        # 3. Ensure General tab is selected (usually default)
        general_tab = regions.get("settings_options_general_tab")
        if general_tab:
            pyautogui.click(
                general_tab["x"], general_tab["y"],
                duration=move_dur,
            )
            qgis.wait(0.5)

        # 4. Click the UI Theme dropdown and select dark theme
        self._log.info("Selecting dark theme in Options dialog")
        theme_dropdown = regions.get("settings_options_theme_dropdown")
        if theme_dropdown:
            pyautogui.click(
                theme_dropdown["x"], theme_dropdown["y"],
                duration=move_dur,
            )
            qgis.wait(0.3)
            # Type to search for "Night Mapping" theme
            pyautogui.typewrite("Night", interval=0.05)
            qgis.wait(0.3)
            pyautogui.press("return")
        qgis.wait(1.0)

        # 5. Apply with OK (Alt+O or click OK button)
        self._log.info("Applying theme change")
        pyautogui.hotkey("enter")
        qgis.wait(2.0)

        # 6. Show FilterMate adapted to dark theme
        qgis.focus_filtermate()
        qgis.highlight_area("filtermate_dock", duration=2.0)
        qgis.wait(1.0)
