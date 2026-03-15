"""
V01 Sequence 1 — INSTALLATION VIA LE PLUGIN MANAGER (0:15 - 0:45)
==================================================================
QGIS > Extensions > Gerer les extensions > Rechercher "FilterMate" > Installer.
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S01Install(VideoSequence):
    name = "V01 — Installation Plugin Manager"
    sequence_id = "v01_s01"
    duration_estimate = 30.0
    obs_scene = "QGIS Fullscreen"
    diagram_ids = ["v01_install_flow"]
    narration_text = (
        "L'installation se fait en 3 clics depuis QGIS. "
        "Allez dans le menu Extensions, puis Gerer les extensions. "
        "Dans l'onglet Toutes, tapez FilterMate dans la barre de recherche. "
        "Le plugin apparait. Cliquez sur Installer. C'est tout. "
        "FilterMate est gratuit, open source, et disponible sur le depot officiel QGIS "
        "Windows, Linux et macOS."
    )

    def execute(self, obs, qgis, config):
        import pyautogui

        regions = config["qgis"]["regions"]

        qgis.focus_qgis()
        qgis.wait(1.0)

        # 1. Open Plugin Manager
        qgis.open_plugin_manager()
        qgis.wait(1.5)

        # 2. Type "FilterMate" in the search box (focused by default)
        pyautogui.typewrite("FilterMate", interval=0.08)
        qgis.wait(1.5)

        # 3. Hover over the plugin entry in the list
        plugin_entry = regions.get("plugin_manager_entry", {"x": 640, "y": 400})
        qgis.move_mouse_to(plugin_entry["x"], plugin_entry["y"], duration=0.8)
        qgis.wait(1.0)

        # 4. Point at the Install button (bottom right)
        plugin_install = regions.get("plugin_manager_install_btn", {"x": 900, "y": 700})
        qgis.move_mouse_to(plugin_install["x"], plugin_install["y"], duration=0.8)
        qgis.wait(1.5)

        # 5. Show installation flow diagram
        self.show_diagram(obs, "v01_install_flow", duration=5.0)

        # 6. Close dialog
        qgis.close_dialog()
        qgis.wait(0.5)
