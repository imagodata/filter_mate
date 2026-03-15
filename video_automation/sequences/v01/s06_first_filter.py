"""
V01 Sequence 6 — PREMIER FILTRAGE : SHAPEFILE LOCAL (3:30 - 5:00)
=================================================================
Demo live : departements + communes. Selectionner Gironde, filtrer Intersects.

Steps:
  1. Exploring Zone: selectionner couche "departements"
  2. Parcourir les entites, choisir "Gironde"
  3. Onglet FILTERING: verifier couche source (auto)
  4. Selectionner cible "communes"
  5. Predicat "Intersects"
  6. Cliquer Filter
  7. Voir le resultat sur la carte
"""
from __future__ import annotations

import time

from sequences.base import VideoSequence


class V01S06FirstFilter(VideoSequence):
    name = "V01 — Premier filtrage Shapefile"
    sequence_id = "v01_s06"
    duration_estimate = 90.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_first_filter_workflow"]
    narration_text = (
        "Passons a la pratique. Nos deux couches sont chargees : les departements "
        "et les communes. Dans la Zone d'Exploration, je selectionne la couche "
        "departements. Je choisis Gironde. "
        "Dans l'onglet FILTERING, FilterMate a reconnu ma selection. "
        "En couche cible, je choisis communes. "
        "Predicat spatial : Intersects. Je clique sur Filter. "
        "Les 35 000 communes sont filtrees instantanement. "
        "Seules celles qui intersectent la Gironde restent visibles. "
        "FilterMate a detecte le backend OGR automatiquement."
    )

    def execute(self, obs, qgis, config):
        import pyautogui

        action_pause = config["timing"].get("action_pause", 1.0)
        regions = config["qgis"]["regions"]

        # --- PART 1: Layer & feature selection ---

        qgis.focus_filtermate()
        qgis.wait(0.5)

        # 1. Select exploring layer "departements"
        self._log.info("Step 1: Selecting exploring layer 'departements'")
        qgis.select_exploring_layer("departements")
        qgis.wait(action_pause)

        # 2. Navigate features to find "Gironde"
        self._log.info("Step 2: Navigating to 'Gironde'")
        # Type "Gironde" in the feature selector
        qgis.select_combobox_item("exploring_feature_selector", "Gironde")
        qgis.wait(action_pause)

        # 3. Pause to show the selection on the map
        qgis.wait(1.5)

        # --- PART 2: Configure filter ---

        # 4. Switch to FILTERING tab (should already show source = departements)
        self._log.info("Step 3-4: Verifying FILTERING tab")
        qgis.select_tab("FILTERING")
        qgis.wait(action_pause)

        # Hover over source layer to show it's auto-filled
        qgis.hover_region("source_layer_combo", duration=1.5)

        # 5. Select target layer "communes"
        self._log.info("Step 5: Selecting target layer 'communes'")
        qgis.select_target_layer("communes")
        qgis.wait(action_pause)

        # 6. Select predicate "Intersects"
        self._log.info("Step 6: Selecting predicate 'Intersects'")
        qgis.select_predicate("intersects")
        qgis.wait(action_pause)

        # --- PART 3: Execute filter ---

        # 7. Click Filter button!
        self._log.info("Step 7: Clicking FILTER")
        qgis.click_action_button("filter")
        time.sleep(3.0)  # Wait for query completion

        # 8. Show result on map — pan around
        self._log.info("Step 8: Showing result on map")
        canvas = regions.get("main_canvas", {})
        if canvas:
            cx = canvas["x"] + canvas["width"] // 2
            cy = canvas["y"] + canvas["height"] // 2
            qgis.move_mouse_to(cx - 200, cy, duration=1.5)
            qgis.wait(1.0)
            qgis.move_mouse_to(cx + 200, cy, duration=1.5)
        qgis.wait(2.0)

        # 9. Point at backend badge to show OGR detection
        qgis.hover_region("badge_backend", duration=2.0)

        # 10. Show workflow diagram
        self.show_diagram(obs, "v01_first_filter_workflow", duration=6.0)

        qgis.focus_qgis()
        qgis.wait(1.0)
