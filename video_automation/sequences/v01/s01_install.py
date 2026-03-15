"""
V01 Sequence 1 — INSTALLATION VIA LE PLUGIN MANAGER (0:15 - 0:45)
==================================================================
QGIS > Extensions > Gerer les extensions > Rechercher "FilterMate" > Installer.
"""
from __future__ import annotations

from core.narrator import V01_NARRATION_TEXTS
from sequences.base import VideoSequence


class V01S01Install(VideoSequence):
    name = "V01 — Installation Plugin Manager"
    sequence_id = "v01_s01"
    duration_estimate = 30.0
    obs_scene = "QGIS Fullscreen"
    diagram_ids = ["v01_install_flow"]
    narration_text = V01_NARRATION_TEXTS["v01_s01"]

    def execute(self, obs, qgis, config):
        import pyautogui

        regions = config["qgis"]["regions"]

        qgis.focus_qgis()
        qgis.wait(1.0)

        # 1. Open Plugin Manager (uses region-based navigation)
        qgis.open_plugin_manager()
        qgis.wait(1.5)

        # 2. Click the "All" / "Toutes" tab to ensure full listing
        all_tab = regions.get("plugin_manager_all_tab")
        if all_tab:
            pyautogui.click(
                all_tab["x"], all_tab["y"],
                duration=config["timing"].get("mouse_move_duration", 0.5),
            )
            qgis.wait(0.5)

        # 3. Click the search bar and type "FilterMate"
        search_bar = regions.get("plugin_manager_search")
        if search_bar:
            pyautogui.click(
                search_bar["x"], search_bar["y"],
                duration=config["timing"].get("mouse_move_duration", 0.5),
            )
            qgis.wait(0.3)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.typewrite("FilterMate", interval=0.08)
        qgis.wait(1.5)

        # 4. Hover over the plugin entry in the list
        plugin_entry = regions.get("plugin_manager_entry", {"x": 400, "y": 450})
        qgis.move_mouse_to(plugin_entry["x"], plugin_entry["y"], duration=0.8)
        pyautogui.click()
        qgis.wait(1.0)

        # 5. Point at the Install button
        plugin_install = regions.get("plugin_manager_install_btn", {"x": 1400, "y": 780})
        qgis.move_mouse_to(plugin_install["x"], plugin_install["y"], duration=0.8)
        qgis.wait(1.5)

        # 6. Show installation flow diagram
        self.show_diagram(obs, "v01_install_flow", duration=5.0)

        # 7. Close dialog
        qgis.close_dialog()
        qgis.wait(0.5)
