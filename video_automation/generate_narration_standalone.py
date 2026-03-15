#!/usr/bin/env python3
"""
Standalone narration generator — creates TTS audio for all 11 video sequences.
Uses edge-tts (free Microsoft Neural TTS voices).
"""
import asyncio
import os
import sys
import json

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "narration")

# Voice configuration
VOICE = "fr-FR-HenriNeural"  # French male voice
RATE = "+0%"
VOLUME = "+0%"

# All narration texts from VIDEO_SCRIPT.md
NARRATIONS = {
    "seq00_intro": (
        "Vous avez 1 million de bâtiments dans votre PostGIS ? "
        "Vous cherchez juste ceux à 200 mètres d'une route spécifique ? "
        "Et vous voulez ça en moins de 2 secondes ? "
        "C'est exactement ce que fait FilterMate."
    ),
    "seq01_problem": (
        "En SIG, le filtrage est une tâche centrale. Mais QGIS native a ses limites : "
        "expressions complexes, aucun historique, aucun système de favoris, "
        "performance dégradée sur les grosses sources. "
        "FilterMate résout tout ça. C'est un plugin open source, entièrement intégré "
        "à QGIS 3 et 4, avec une architecture multi-backend qui choisit automatiquement "
        "la meilleure stratégie selon votre données source."
    ),
    "seq02_install": (
        "Installation en 3 clics depuis le dépôt officiel QGIS. "
        "Pour les bases PostgreSQL, un simple pip install psycopg2-binary suffit. "
        "FilterMate fonctionne sur Windows, Linux et macOS."
    ),
    "seq03_interface": (
        "L'interface se présente sous forme d'un panneau ancré dans QGIS, "
        "organisé en 3 onglets principaux : Filtrage, Exploration des données, et Export. "
        "Support du thème sombre automatique, 22 langues disponibles."
    ),
    "seq04_filtering_part1": (
        "Voilà un jeu de données BDTopo. 1 million de bâtiments dans PostgreSQL. "
        "Je sélectionne ma couche source : les routes. Ma couche cible : les bâtiments."
    ),
    "seq04_filtering_part2": (
        "Je choisis le prédicat géométrique touches, j'ajoute un buffer de 50 mètres... "
        "et j'applique. FilterMate détecte automatiquement que c'est une couche PostgreSQL, "
        "crée une vue matérialisée optimisée et renvoie le résultat : 1 milliseconde. Exactement."
    ),
    "seq04_filtering_part3": (
        "Je peux annuler avec l'undo, 100 états conservés. "
        "Ou rappeler un filtre favori enregistré précédemment. "
        "Tout ça sans jamais écrire une seule ligne de SQL."
    ),
    "seq05_exploration": (
        "L'onglet Exploration vous permet de parcourir vos entités une à une, "
        "avec centrage automatique sur la carte. "
        "Pour les couches raster, 5 outils interactifs sont disponibles : "
        "sélection par clic, rectangle, synchronisation histogramme, "
        "affichage multi-bandes, et réinitialisation de plage."
    ),
    "seq06_export": (
        "L'export GeoPackage est l'une des fonctionnalités les plus puissantes. "
        "FilterMate ne se contente pas d'exporter vos données, "
        "il embarque votre projet QGIS complet dans le fichier. "
        "Hiérarchie des groupes, styles des couches, système de coordonnées, "
        "tout est préservé. "
        "À l'ouverture, QGIS reconstitue automatiquement votre arborescence. "
        "Idéal pour partager un livrable complet en un seul fichier."
    ),
    "seq07_backends": (
        "Derrière l'interface simple, FilterMate embarque 4 backends optimisés. "
        "Il choisit automatiquement le meilleur selon le type de votre source de données. "
        "Pour PostgreSQL : vues matérialisées et requêtes parallèles. "
        "Pour Spatialite : index R-tree. "
        "Et pour tout le reste : le backend OGR universel."
    ),
    "seq08_architecture": (
        "FilterMate est construit sur une architecture hexagonale, "
        "aussi appelée Ports et Adapters. "
        "Le domaine métier pur est au centre, totalement indépendant de QGIS, "
        "de la base de données ou de l'interface graphique. "
        "Cela rend le code testable à 75%, maintenable, et extensible "
        "pour de futurs backends."
    ),
    "seq09_advanced": (
        "FilterMate va plus loin : filtrage chaîné avec buffers dynamiques, "
        "détection automatique de la clé primaire PostgreSQL pour les tables BDTopo et OSM, "
        "100 états undo redo, et un système de favoris avec contexte spatial. "
        "396 tests automatisés. 22 langues. Compatible QGIS 3 et 4."
    ),
    "seq10_conclusion": (
        "FilterMate est disponible gratuitement sur le dépôt officiel QGIS. "
        "Le code source est sur GitHub, la documentation sur le site dédié. "
        "Installez-le, essayez-le, et si ça vous est utile, "
        "laissez une étoile sur GitHub. À bientôt !"
    ),
}


async def generate_one(text: str, output_path: str, voice: str = VOICE) -> float:
    """Generate one narration file and return its duration in seconds."""
    import edge_tts
    
    communicate = edge_tts.Communicate(text, voice, rate=RATE, volume=VOLUME)
    await communicate.save(output_path)
    
    # Get duration using mutagen or fallback estimate
    try:
        from mutagen.mp3 import MP3
        audio = MP3(output_path)
        return audio.info.length
    except ImportError:
        # Rough estimate: ~150 words per minute for French TTS
        word_count = len(text.split())
        return word_count / 2.5  # ~2.5 words per second


async def main():
    try:
        import edge_tts
    except ImportError:
        print("[ERROR] edge-tts not installed. Run: pip install edge-tts")
        sys.exit(1)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"\n{'='*50}")
    print(f"  FilterMate Narration Generator")
    print(f"  Voice: {VOICE}")
    print(f"  {len(NARRATIONS)} narrations to generate")
    print(f"{'='*50}\n")
    
    total_duration = 0.0
    manifest = {}
    
    for name, text in NARRATIONS.items():
        output_path = os.path.join(OUTPUT_DIR, f"{name}.mp3")
        print(f"  [{name}] {text[:60]}...")
        
        try:
            duration = await generate_one(text, output_path)
            total_duration += duration
            manifest[name] = {
                "file": f"{name}.mp3",
                "duration": round(duration, 2),
                "text": text
            }
            print(f"    ✓ {output_path} ({duration:.1f}s)")
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"\n  Done: {len(manifest)} narration files")
    print(f"  Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"  Manifest: {manifest_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
