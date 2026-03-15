"""
OBS Auto-Configuration Script
================================
Creates the required OBS scenes and sources for FilterMate video production.
Configures recording settings (MKV, x264, 1080p30).

Usage:
    python scripts/setup_obs.py [--config ../config.yaml] [--dry-run]

Requirements:
  - OBS Studio running with WebSocket Server enabled
  - obsws-python installed

Scenes created:
  1. QGIS Fullscreen       — Display capture, no FilterMate panel
  2. QGIS + FilterMate     — Display capture, FilterMate visible
  3. Diagram Overlay        — Browser source for Mermaid HTML diagrams
  4. Intro                  — Title card / animated intro
  5. Outro                  — End card with links

Sources created in each scene:
  - Display Capture (monitor 0) — for all QGIS scenes
  - Browser Source              — for diagram overlay (points to localhost HTML)
  - Text (GDI+/FreeType)        — for intro/outro text
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"

# ── Scene definitions ──────────────────────────────────────────────────────

SCENES_TO_CREATE = [
    "QGIS Fullscreen",
    "QGIS + FilterMate",
    "Diagram Overlay",
    "Intro",
    "Outro",
]


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_obs(config: dict, dry_run: bool = False) -> None:
    """Connect to OBS and create the required scenes/sources."""
    obs_cfg = config.get("obs", {})

    if dry_run:
        logger.info("[DRY RUN] Would connect to OBS at %s:%s", obs_cfg.get("host"), obs_cfg.get("port"))
        logger.info("[DRY RUN] Would create scenes: %s", SCENES_TO_CREATE)
        logger.info("[DRY RUN] Would configure recording: MKV, x264, 1080p30")
        return

    try:
        import obsws_python as obs  # type: ignore
    except ImportError:
        logger.error("obsws-python not installed. Run: pip install obsws-python")
        sys.exit(1)

    logger.info("Connecting to OBS at %s:%s…", obs_cfg.get("host"), obs_cfg.get("port"))
    client = obs.ReqClient(
        host=obs_cfg.get("host", "localhost"),
        port=obs_cfg.get("port", 4455),
        password=obs_cfg.get("password", ""),
        timeout=10,
    )

    # ── Get existing scenes ────────────────────────────────────────────────
    try:
        existing = client.get_scene_list()
        existing_names = {s["sceneName"] for s in existing.scenes}
        logger.info("Existing scenes: %s", sorted(existing_names))
    except Exception as exc:
        logger.warning("Could not list existing scenes: %s", exc)
        existing_names = set()

    # ── Create missing scenes ──────────────────────────────────────────────
    for scene_name in SCENES_TO_CREATE:
        if scene_name in existing_names:
            logger.info("Scene already exists: %s", scene_name)
            continue
        try:
            client.create_scene(scene_name)
            logger.info("Created scene: %s", scene_name)
        except Exception as exc:
            logger.warning("Could not create scene '%s': %s", scene_name, exc)

    time.sleep(0.5)  # Let OBS settle

    # ── Add Display Capture to QGIS scenes ────────────────────────────────
    qgis_scenes = ["QGIS Fullscreen", "QGIS + FilterMate"]
    for scene_name in qgis_scenes:
        _add_source(client, scene_name, "Display Capture", "monitor_capture",
                    settings={"monitor": 0, "capture_cursor": True})

    # ── Add Browser Source for Diagram Overlay ─────────────────────────────
    diagram_dir = Path(config.get("diagrams", {}).get("output_dir", "output/diagrams")).resolve()
    # OBS Browser Source URL — points to a local HTML file served via file://
    # We use the first diagram as default; the real setup switches files per-sequence
    default_diagram = diagram_dir / "01_positioning.html"
    browser_url = default_diagram.as_uri()
    _add_source(client, "Diagram Overlay", "FilterMate Diagram", "browser_source",
                settings={
                    "url": browser_url,
                    "width": 1920,
                    "height": 1080,
                    "fps": 30,
                    "css": "body { margin: 0; overflow: hidden; }",
                    "shutdown": True,
                    "restart_when_active": True,
                })

    # ── Add Text sources for Intro/Outro ──────────────────────────────────
    _add_source(client, "Intro", "Intro Title", "text_gdiplus_v3",
                settings={
                    "text": "FilterMate\nFiltrage vectoriel pour QGIS",
                    "font": {"face": "Segoe UI", "size": 72, "bold": True},
                    "color": 0xFF4CAF50,
                    "align": "center",
                    "valign": "center",
                })
    _add_source(client, "Outro", "Outro Text", "text_gdiplus_v3",
                settings={
                    "text": (
                        "FilterMate est disponible gratuitement\n"
                        "github.com/imagodata/filter_mate\n"
                        "plugins.qgis.org/plugins/filter_mate"
                    ),
                    "font": {"face": "Segoe UI", "size": 48, "bold": False},
                    "color": 0xFFE0E0E0,
                    "align": "center",
                    "valign": "center",
                })

    # ── Configure recording settings ───────────────────────────────────────
    output_dir = obs_cfg.get("output_dir", "C:/Users/Simon/Videos/FilterMate")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    try:
        client.set_record_directory(output_dir)
        logger.info("Recording output directory: %s", output_dir)
    except Exception as exc:
        logger.warning("Could not set recording directory: %s", exc)

    logger.info("OBS setup complete!")
    logger.info(
        "TIP: Configure recording format to MKV in OBS Settings → Output → Recording."
    )
    logger.info(
        "TIP: Set encoder to x264, bitrate 15000–25000 kbps, resolution 1920x1080, 30fps."
    )


def _add_source(
    client,
    scene_name: str,
    source_name: str,
    source_kind: str,
    settings: dict | None = None,
) -> None:
    """Add a source to a scene if it doesn't already exist."""
    try:
        client.create_input(scene_name, source_name, source_kind, settings or {}, True)
        logger.info("Added source '%s' (%s) to scene '%s'", source_name, source_kind, scene_name)
    except Exception as exc:
        # Source may already exist
        logger.debug("Could not add source '%s' to '%s': %s", source_name, scene_name, exc)


def main():
    parser = argparse.ArgumentParser(description="Configure OBS for FilterMate video production.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    args = parser.parse_args()

    if not args.config.exists():
        logger.error("Config not found: %s", args.config)
        sys.exit(1)

    config = load_config(args.config)
    setup_obs(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
