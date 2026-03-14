"""
Séquence 5 — EXPLORATION DE DONNÉES (1:00)
===========================================
Visuel: Onglet Exploration — naviguer entité par entité, raster tools.
Diagramme 6 (Outils Raster) affiché.
"""

from __future__ import annotations

from sequences.base import VideoSequence


class Seq05Exploration(VideoSequence):
    name = "Exploration de Données"
    sequence_id = "seq05"
    duration_estimate = 60.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["06_raster"]
    narration_text = (
        "L'onglet Exploration vous permet de parcourir vos entités une à une, "
        "avec centrage automatique sur la carte. "
        "Pour les couches raster, 5 outils interactifs sont disponibles : "
        "sélection par clic, rectangle, synchronisation histogramme, "
        "affichage multi-bandes, et réinitialisation de plage."
    )

    def execute(self, obs, qgis, config):
        import pyautogui  # type: ignore

        qgis.focus_qgis()
        qgis.focus_filtermate()

        # 1. Switch to EXPLORING tab
        qgis.select_tab("EXPLORING")
        qgis.wait(1.0)

        # 2. Navigate through vector features (Next / Previous buttons)
        #    We click the "Next feature" button several times
        for i in range(5):
            qgis.click_button("btn_next_feature")
            qgis.wait(0.8)
            # The map auto-centers on each feature

        qgis.wait(1.0)

        # 3. Switch to a raster layer context (user would click on raster in layers)
        #    We demonstrate the raster tools panel
        self._log.info("Demonstrating raster tools")
        qgis.wait(1.0)

        # Move mouse to highlight each raster tool icon in the toolbar
        raster_tools = [
            "btn_pixel_picker",
            "btn_rectangle_range",
            "btn_sync_histogram",
            "btn_all_bands",
            "btn_reset_range",
        ]
        for tool in raster_tools:
            success = qgis.click_button(tool, confidence=0.75)
            if not success:
                self._log.debug("Raster tool button '%s' not found (image missing).", tool)
            qgis.wait(0.8)
            pyautogui.press("escape")  # Deactivate tool
            qgis.wait(0.3)

        qgis.wait(1.0)

        # 4. Show the raster tools diagram
        self.show_diagram(obs, "06_raster", duration=8.0)

        qgis.focus_qgis()
        qgis.wait(1.0)
