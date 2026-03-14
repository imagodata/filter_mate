"""
Séquence 3 — INTERFACE — VUE D'ENSEMBLE (0:45)
================================================
Visuel: Survol de l'interface dockwidget — 3 onglets avec annotations.
Diagramme 3 (Interface Utilisateur) affiché.
"""

from __future__ import annotations

from sequences.base import VideoSequence


class Seq03Interface(VideoSequence):
    name = "Interface — Vue d'ensemble"
    sequence_id = "seq03"
    duration_estimate = 45.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["03_interface"]
    narration_text = (
        "L'interface se présente sous forme d'un panneau ancré dans QGIS, "
        "organisé en 3 onglets principaux : Filtrage, Exploration des données, et Export. "
        "Support du thème sombre automatique, 22 langues disponibles."
    )

    def execute(self, obs, qgis, config):
        """
        Navigate all three tabs of the FilterMate dockwidget, pausing on each.
        Then display the interface diagram.
        """
        qgis.focus_qgis()
        qgis.focus_filtermate()
        qgis.wait(1.0)

        # 1. FILTERING tab — highlight and narrate
        qgis.select_tab("FILTERING")
        qgis.wait(1.0)
        # Highlight the FilterMate dock region
        regions = config.get("qgis", {}).get("regions", {})
        dock = regions.get("filtermate_dock")
        if dock:
            qgis.highlight_area("filtermate_dock", duration=2.0)

        # 2. Move mouse slowly through key elements
        #    Source layer combobox
        qgis.click_at("source_layer_combo")
        qgis.wait(0.5)
        import pyautogui  # type: ignore
        pyautogui.press("escape")

        # 3. EXPLORING tab
        qgis.select_tab("EXPLORING")
        qgis.wait(2.0)

        # 4. EXPORTING tab
        qgis.select_tab("EXPORTING")
        qgis.wait(2.0)

        # 5. Return to FILTERING tab
        qgis.select_tab("FILTERING")
        qgis.wait(1.0)

        # 6. Show the interface overview diagram
        self.show_diagram(obs, "03_interface", duration=8.0)

        qgis.focus_qgis()
        qgis.wait(1.0)
