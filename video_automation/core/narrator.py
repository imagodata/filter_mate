"""
Narrator — TTS Audio Generation
=================================
Generates narration audio files for each video sequence using either
edge-tts (free, Microsoft voices) or ElevenLabs (paid, higher quality).

Usage:
    from core.narrator import Narrator
    narrator = Narrator(config["narration"])
    path = narrator.generate_narration("Votre texte ici", "output/narration/seq00.mp3")
    duration = narrator.get_narration_duration(path)
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Narrator:
    """
    Generates TTS narration audio.

    Parameters
    ----------
    config : dict
        The 'narration' section from config.yaml.
    """

    def __init__(self, config: dict) -> None:
        self.engine: str = config.get("engine", "edge-tts")
        self.voice: str = config.get("voice", "fr-FR-HenriNeural")
        self.output_dir = Path(config.get("output_dir", "output/narration"))
        self.speed: str = config.get("speed", "+0%")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_narration(
        self,
        text: str,
        output_path: str | Path,
        voice: Optional[str] = None,
    ) -> Path:
        """
        Generate TTS audio for the given text.

        Parameters
        ----------
        text : str
            Text to synthesize.
        output_path : str | Path
            Output audio file path (.mp3 or .wav).
        voice : str, optional
            Override voice name.

        Returns
        -------
        Path
            Path to the generated audio file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        voice = voice or self.voice

        if self.engine == "edge-tts":
            return self._generate_edge_tts(text, output_path, voice)
        elif self.engine == "elevenlabs":
            return self._generate_elevenlabs(text, output_path, voice)
        else:
            raise ValueError(f"Unknown TTS engine: {self.engine}. Use 'edge-tts' or 'elevenlabs'.")

    def generate_all_narrations(
        self,
        script_dict: dict[str, str],
        output_dir: Optional[str | Path] = None,
    ) -> dict[str, Path]:
        """
        Batch-generate narration audio for all sequences.

        Parameters
        ----------
        script_dict : dict
            Mapping of sequence_id → narration text.
            e.g. {"seq00": "Vous avez 1 million de bâtiments...", ...}
        output_dir : str | Path, optional
            Override for output directory.

        Returns
        -------
        dict
            Mapping of sequence_id → Path to audio file.
        """
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Path] = {}
        for seq_id, text in script_dict.items():
            output_path = out_dir / f"{seq_id}_narration.mp3"
            logger.info("Generating narration for %s…", seq_id)
            try:
                results[seq_id] = self.generate_narration(text, output_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to generate narration for %s: %s", seq_id, exc)
        return results

    def get_narration_duration(self, audio_path: str | Path) -> float:
        """
        Return the duration of an audio file in seconds.

        Tries mutagen first, falls back to ffprobe.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            logger.warning("Audio file not found: %s", audio_path)
            return 0.0

        # Try mutagen
        try:
            from mutagen.mp3 import MP3  # type: ignore
            from mutagen.wave import WAVE  # type: ignore

            if audio_path.suffix.lower() == ".mp3":
                audio = MP3(audio_path)
            elif audio_path.suffix.lower() in (".wav",):
                audio = WAVE(audio_path)
            else:
                raise ValueError(f"Unsupported format: {audio_path.suffix}")
            return float(audio.info.length)
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.debug("mutagen failed: %s", exc)

        # Fallback: ffprobe
        return self._ffprobe_duration(audio_path)

    def list_voices(self) -> list[dict]:
        """List available edge-tts voices (requires edge-tts installed)."""
        if self.engine != "edge-tts":
            raise RuntimeError("list_voices() only supports edge-tts engine.")
        try:
            import edge_tts  # type: ignore

            voices = asyncio.run(edge_tts.list_voices())
            return voices
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")

    # ------------------------------------------------------------------
    # Engine implementations
    # ------------------------------------------------------------------

    def _generate_edge_tts(self, text: str, output_path: Path, voice: str) -> Path:
        """Generate audio using Microsoft edge-tts."""
        try:
            import edge_tts  # type: ignore
        except ImportError:
            raise ImportError(
                "edge-tts not installed. Run: pip install edge-tts"
            )

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=self.speed)
            await communicate.save(str(output_path))

        asyncio.run(_run())
        logger.info("edge-tts generated: %s (%.1fs)", output_path.name,
                    self.get_narration_duration(output_path))
        return output_path

    def _generate_elevenlabs(self, text: str, output_path: Path, voice: str) -> Path:
        """Generate audio using ElevenLabs API (requires ELEVENLABS_API_KEY env var)."""
        import os

        try:
            from elevenlabs import generate, save  # type: ignore
        except ImportError:
            raise ImportError(
                "elevenlabs package not installed. Run: pip install elevenlabs"
            )

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ELEVENLABS_API_KEY environment variable not set."
            )

        audio = generate(text=text, voice=voice, api_key=api_key)
        save(audio, str(output_path))
        logger.info("ElevenLabs generated: %s", output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Duration helpers
    # ------------------------------------------------------------------

    def _ffprobe_duration(self, audio_path: Path) -> float:
        """Extract duration via ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            import json
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if "duration" in stream:
                    return float(stream["duration"])
        except Exception as exc:  # noqa: BLE001
            logger.error("ffprobe failed: %s", exc)
        return 0.0


# ---------------------------------------------------------------------------
# Narration texts for each sequence (extracted from VIDEO_SCRIPT.md)
# ---------------------------------------------------------------------------
NARRATION_TEXTS: dict[str, str] = {
    "seq00": (
        "Vous avez 1 million de bâtiments dans votre PostGIS ? "
        "Vous cherchez juste ceux à 200 mètres d'une route spécifique ? "
        "Et vous voulez ça en moins de 2 secondes ? "
        "C'est exactement ce que fait FilterMate."
    ),
    "seq01": (
        "En SIG, le filtrage est une tâche centrale. "
        "Mais QGIS native a ses limites : expressions complexes, aucun historique, "
        "aucun système de favoris, performance dégradée sur les grosses sources. "
        "FilterMate résout tout ça. C'est un plugin open source, "
        "entièrement intégré à QGIS 3 et 4, avec une architecture multi-backend "
        "qui choisit automatiquement la meilleure stratégie selon votre données source."
    ),
    "seq02": (
        "Installation en 3 clics depuis le dépôt officiel QGIS. "
        "Pour les bases PostgreSQL, un simple pip install psycopg2-binary suffit. "
        "FilterMate fonctionne sur Windows, Linux et macOS."
    ),
    "seq03": (
        "L'interface se présente sous forme d'un panneau ancré dans QGIS, "
        "organisé en 3 onglets principaux : Filtrage, Exploration des données, et Export. "
        "Support du thème sombre automatique, 22 langues disponibles."
    ),
    "seq04_part1": (
        "Voilà un jeu de données BDTopo — 1 million de bâtiments dans PostgreSQL. "
        "Je sélectionne ma couche source : les routes. "
        "Ma couche cible : les bâtiments."
    ),
    "seq04_part2": (
        "Je choisis le prédicat géométrique touches, "
        "j'ajoute un buffer de 50 mètres... et j'applique. "
        "FilterMate détecte automatiquement que c'est une couche PostgreSQL, "
        "crée une vue matérialisée optimisée et renvoie le résultat : "
        "1 milliseconde. Exactement."
    ),
    "seq04_part3": (
        "Je peux annuler avec l'undo — 100 états conservés. "
        "Ou rappeler un filtre favori enregistré précédemment. "
        "Tout ça sans jamais écrire une seule ligne de SQL."
    ),
    "seq05": (
        "L'onglet Exploration vous permet de parcourir vos entités une à une, "
        "avec centrage automatique sur la carte. "
        "Pour les couches raster, 5 outils interactifs sont disponibles : "
        "sélection par clic, rectangle, synchronisation histogramme, "
        "affichage multi-bandes, et réinitialisation de plage."
    ),
    "seq06": (
        "L'export GeoPackage est l'une des fonctionnalités les plus puissantes. "
        "FilterMate ne se contente pas d'exporter vos données — "
        "il embarque votre projet QGIS complet dans le fichier. "
        "Hiérarchie des groupes, styles des couches, système de coordonnées — tout est préservé. "
        "À l'ouverture, QGIS reconstitue automatiquement votre arborescence. "
        "Idéal pour partager un livrable complet en un seul fichier."
    ),
    "seq07": (
        "Derrière l'interface simple, FilterMate embarque 4 backends optimisés. "
        "Il choisit automatiquement le meilleur selon le type de votre source de données. "
        "Pour PostgreSQL : vues matérialisées et requêtes parallèles. "
        "Pour Spatialite : index R-tree. "
        "Et pour tout le reste : le backend OGR universel."
    ),
    "seq08": (
        "FilterMate est construit sur une architecture hexagonale — "
        "aussi appelée Ports & Adapters. "
        "Le domaine métier pur est au centre, totalement indépendant de QGIS, "
        "de la base de données ou de l'interface graphique. "
        "Cela rend le code testable à 75%, maintenable, "
        "et extensible pour de futurs backends."
    ),
    "seq09": (
        "FilterMate va plus loin : filtrage chaîné avec buffers dynamiques, "
        "détection automatique de la clé primaire PostgreSQL "
        "pour les tables BDTopo et OSM, "
        "100 états undo/redo, et un système de favoris avec contexte spatial. "
        "396 tests automatisés. 22 langues. Compatible QGIS 3 et 4."
    ),
    "seq10": (
        "FilterMate est disponible gratuitement sur le dépôt officiel QGIS. "
        "Le code source est sur GitHub, la documentation sur le site dédié. "
        "Installez-le, essayez-le, et si ça vous est utile — "
        "laissez une étoile sur GitHub. À bientôt !"
    ),
}
