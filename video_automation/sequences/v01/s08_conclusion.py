"""
V01 Sequence 8 — PERSISTANCE + CONCLUSION & RESSOURCES
========================================================
Merge de 2 anciennes séquences :
- Persistance SQLite (sauvegarde automatique)
- Conclusion avec récapitulatif et ressources

Uses TimelineSequence for narration-synchronized execution.
"""
from __future__ import annotations

from core.timeline import NarrationCue
from sequences.base import TimelineSequence


class V01S08Conclusion(TimelineSequence):
    name = "V01 — Persistance & Conclusion"
    sequence_id = "v01_s08"
    duration_estimate = 25.0
    obs_scene = "QGIS + FilterMate"
    diagram_ids = ["v01_persistence"]
    narration_text = ""  # Narration is now in the cues

    def build_timeline(self, obs, qgis, config):
        scenes = config["obs"]["scenes"]
        outro_scene = scenes.get("outro_scene", "Outro")

        return [
            # Cue 0: Persistence intro
            NarrationCue(
                label="Persistance SQLite",
                text=(
                    "Tout ce que vous configurez dans FilterMate est sauvegardé "
                    "automatiquement. Le champ d'affichage, vos préférences, "
                    "l'état des toggles — tout est persisté dans une base SQLite locale. "
                    "Fermez QGIS, rouvrez-le demain — FilterMate retrouve vos réglages."
                ),
                sync="during",
                actions=lambda: (
                    qgis.focus_filtermate(),
                    qgis.highlight_area("filtermate_dock", duration=2.0),
                ),
                post_delay=0.3,
            ),
            # Cue 1: Persistence diagram
            NarrationCue(
                label="Diagramme persistance",
                text="",
                actions=lambda: self.show_diagram(
                    obs, "v01_persistence", duration=5.0
                ),
                post_delay=0.5,
            ),
            # Cue 2: Conclusion — switch to outro
            NarrationCue(
                label="Conclusion",
                text=(
                    "Voilà, vous avez installé FilterMate, "
                    "découvert les 3 zones de l'interface, "
                    "navigué entre vos entités avec les boutons précédent et suivant, "
                    "exploré la carte avec le suivi automatique, "
                    "synchronisé la couche source avec le panneau de couches QGIS, "
                    "et réalisé votre premier filtrage spatial avec undo et redo. "
                    "Pas mal pour 7 minutes !"
                ),
                scene=outro_scene,
                sync="before",
                actions=lambda: qgis.wait(1.0),
                post_delay=0.5,
            ),
            # Cue 3: Resources + CTA
            NarrationCue(
                label="Ressources & CTA",
                text=(
                    "Retrouvez le code source sur GitHub, "
                    "le plugin sur le dépôt officiel QGIS, "
                    "et la documentation complète sur le site dédié. "
                    "Les liens sont dans la description. "
                    "Dans la prochaine vidéo, on approfondit le filtrage géométrique. "
                    "À très vite !"
                ),
                sync="during",
                actions=lambda: qgis.wait(8.0),  # Hold on outro card
                post_delay=1.0,
            ),
        ]
