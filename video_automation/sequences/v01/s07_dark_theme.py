"""
V01 Sequence 7 — THEME SOMBRE AUTOMATIQUE (5:00 - 5:20)
========================================================
Basculer QGIS en theme sombre, montrer FilterMate qui s'adapte.
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S07DarkTheme(VideoSequence):
    name = "V01 — Theme sombre automatique"
    sequence_id = "v01_s07"
    duration_estimate = 20.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = []
    narration_text = (
        "FilterMate s'adapte automatiquement au theme de QGIS. "
        "Vous etes en mode sombre ? Le plugin le detecte et ajuste ses couleurs, "
        "ses icones et ses bordures. Pas besoin de configurer quoi que ce soit. "
        "Trois modes : automatique, theme clair force, ou theme sombre force."
    )

    def execute(self, obs, qgis, config):
        import pyautogui

        qgis.focus_qgis()
        qgis.wait(0.5)

        # 1. Show current (light) theme
        qgis.focus_filtermate()
        qgis.wait(1.5)

        # 2. Open QGIS preferences: Settings > Options > General > UI Theme
        self._log.info("Opening QGIS preferences for theme switch")
        region = config["qgis"]["regions"].get("menu_settings")
        if region:
            pyautogui.click(
                region["x"], region["y"],
                duration=config["timing"].get("mouse_move_duration", 0.5),
            )
        else:
            pyautogui.hotkey("alt", "s")  # Settings menu
        qgis.wait(0.5)

        # Navigate to Options
        pyautogui.press("down")
        pyautogui.press("return")
        qgis.wait(2.0)

        # 3. Theme change is hard to automate precisely
        #    (depends on dialog layout) — pause for manual or pre-configured
        qgis.wait(3.0)

        # 4. Close preferences
        qgis.close_dialog()
        qgis.wait(1.0)

        # 5. Show FilterMate adapted to dark theme
        qgis.focus_filtermate()
        qgis.highlight_area("filtermate_dock", duration=2.0)
        qgis.wait(1.0)
