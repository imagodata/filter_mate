"""
V01 Sequence 3 — ARCHITECTURE DE L'INTERFACE (1:15 - 2:30)
==========================================================
3 zones annotees : Exploring Zone (violet), Toolbox (vert), Action Bar (bleu).
Header bar avec pastilles Favoris + Backend.
"""
from __future__ import annotations

from sequences.base import VideoSequence


class V01S03Interface(VideoSequence):
    name = "V01 — Architecture interface (3 zones)"
    sequence_id = "v01_s03"
    duration_estimate = 75.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_interface_zones"]
    narration_text = (
        "Prenons un moment pour comprendre l'interface. "
        "Elle est divisee en 3 zones principales, separees par un splitter vertical. "
        "En haut, la Zone d'Exploration. C'est ici que vous parcourez et "
        "selectionnez les entites de vos couches. "
        "En bas, la Toolbox. Elle contient deux onglets : FILTERING et EXPORTING. "
        "Et enfin, l'Action Bar. Ce sont les 6 boutons d'action. "
        "Remarquez aussi le header : la pastille orange indique vos favoris, "
        "et la pastille bleue affiche le backend actif."
    )

    def execute(self, obs, qgis, config):
        qgis.focus_qgis()
        qgis.focus_filtermate()
        qgis.wait(1.0)

        # 1. ZONE A — Exploring Zone (highlight violet area)
        self._log.info("Highlighting Zone A: Exploring Zone")
        qgis.highlight_area("exploring_zone", duration=3.0)
        qgis.wait(1.0)

        # 2. Show exploring zone internals — hover over selector
        qgis.hover_region("exploring_layer_combo", duration=1.5)
        qgis.hover_region("exploring_feature_selector", duration=1.5)

        # 3. ZONE B — Toolbox (highlight green area)
        self._log.info("Highlighting Zone B: Toolbox")
        qgis.highlight_area("toolbox_zone", duration=3.0)
        qgis.wait(1.0)

        # Show FILTERING tab
        qgis.select_tab("FILTERING")
        qgis.wait(1.5)

        # Show EXPORTING tab
        qgis.select_tab("EXPORTING")
        qgis.wait(1.5)

        # Return to FILTERING
        qgis.select_tab("FILTERING")
        qgis.wait(0.5)

        # 4. ZONE C — Action Bar (highlight blue area)
        self._log.info("Highlighting Zone C: Action Bar")
        qgis.highlight_area("action_bar_zone", duration=3.0)
        qgis.wait(1.0)

        # 5. Header bar — hover over badges
        self._log.info("Showing header badges")
        qgis.hover_region("badge_favorites", duration=1.5)
        qgis.hover_region("badge_backend", duration=1.5)

        # 6. Show interface zones diagram
        self.show_diagram(obs, "v01_interface_zones", duration=6.0)

        qgis.focus_qgis()
        qgis.wait(1.0)
