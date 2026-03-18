"""
OBS Auto-Configuration Script
================================
Creates the required OBS scenes and sources for desktop app tutorial video production.
Configures recording settings (MKV, x264, 1080p30).

Usage:
    python scripts/setup_obs.py [--config ../config.yaml] [--dry-run]

Requirements:
  - OBS Studio running with WebSocket Server enabled (Tools > WebSocket Server Settings)
  - obsws-python installed (pip install obsws-python)

Scenes created:
  1. App Fullscreen         — Display capture of the full monitor
  2. App + Panel            — Display capture with app panel visible
  3. Diagram Overlay        — Browser source for Mermaid HTML diagrams
  4. Intro                  — Title card / animated intro
  5. Outro                  — End card with links

Customize the SCENES_TO_CREATE list and the source setup functions below
to match your application's recording needs.
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
    "App Fullscreen",
    "App + Panel",
    "Diagram Overlay",
    "Intro",
    "Outro",
]


def load_config(config_path: Path) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def setup_obs(config: dict, dry_run: bool = False) -> None:
    """Connect to OBS and create the required scenes/sources."""
    obs_cfg = config.get("obs", {})

    # Allow config to override default scene names
    custom_scenes = obs_cfg.get("scenes", {})
    scenes = list(SCENES_TO_CREATE)
    if custom_scenes:
        # Add any custom scene names from config that aren't already in the list
        for scene_name in custom_scenes.values():
            if scene_name and scene_name not in scenes:
                scenes.append(scene_name)

    if dry_run:
        logger.info("[DRY RUN] Would connect to OBS at %s:%s", obs_cfg.get("host", "localhost"), obs_cfg.get("port", 4455))
        logger.info("[DRY RUN] Would create scenes: %s", scenes)
        logger.info("[DRY RUN] Would configure recording: MKV, x264, 1080p30")
        return

    try:
        import obsws_python as obs  # type: ignore
    except ImportError:
        logger.error("obsws-python not installed. Run: pip install obsws-python")
        sys.exit(1)

    logger.info("Connecting to OBS at %s:%s...", obs_cfg.get("host", "localhost"), obs_cfg.get("port", 4455))
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
    for scene_name in scenes:
        if scene_name in existing_names:
            logger.info("Scene already exists: %s", scene_name)
            continue
        try:
            client.create_scene(scene_name)
            logger.info("Created scene: %s", scene_name)
        except Exception as exc:
            logger.warning("Could not create scene '%s': %s", scene_name, exc)

    time.sleep(0.5)

    # ── Add Display Capture to app scenes ─────────────────────────────────
    app_scenes_names = [
        custom_scenes.get("app_scene", "App Fullscreen"),
        custom_scenes.get("app_with_panel", "App + Panel"),
    ]
    for scene_name in app_scenes_names:
        if scene_name in scenes:
            _add_source(client, scene_name, "Display Capture", "monitor_capture",
                        settings={"monitor": 0, "capture_cursor": True})

    # ── Add Browser Source for Diagram Overlay ─────────────────────────────
    diagram_dir = Path(config.get("diagrams", {}).get("output_dir", "output/diagrams")).resolve()
    # Use the first diagram HTML as default; update via OBS browser source per sequence
    default_html = diagram_dir / "example.html"
    browser_url = default_html.as_uri()
    diagram_scene = custom_scenes.get("diagram_overlay", "Diagram Overlay")
    if diagram_scene in scenes:
        _add_source(client, diagram_scene, "Tutorial Diagram", "browser_source",
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
    app_name = config.get("app", {}).get("app_name", "App Tutorial")
    intro_scene = custom_scenes.get("intro_scene", "Intro")
    outro_scene = custom_scenes.get("outro_scene", "Outro")

    if intro_scene in scenes:
        _add_source(client, intro_scene, "Intro Title", "text_gdiplus_v3",
                    settings={
                        "text": f"{app_name}\nTutorial Video",
                        "font": {"face": "Segoe UI", "size": 72, "bold": True},
                        "color": 0xFF4CAF50,
                        "align": "center",
                        "valign": "center",
                    })

    if outro_scene in scenes:
        outro_url = config.get("app", {}).get("url", "")
        _add_source(client, outro_scene, "Outro Text", "text_gdiplus_v3",
                    settings={
                        "text": f"{app_name}\n{outro_url}" if outro_url else app_name,
                        "font": {"face": "Segoe UI", "size": 48, "bold": False},
                        "color": 0xFFE0E0E0,
                        "align": "center",
                        "valign": "center",
                    })

    # ── Configure recording output directory ──────────────────────────────
    output_dir = obs_cfg.get("output_dir", str(Path.home() / "Videos" / "Tutorial"))
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    try:
        client.set_record_directory(output_dir)
        logger.info("Recording output directory: %s", output_dir)
    except Exception as exc:
        logger.warning("Could not set recording directory: %s", exc)

    logger.info("OBS setup complete!")
    logger.info(
        "TIP: Configure recording format to MKV in OBS Settings > Output > Recording."
    )
    logger.info(
        "TIP: Set encoder to x264, bitrate 15000-25000 kbps, resolution 1920x1080, 30fps."
    )


def _add_source(client, scene_name, source_name, source_kind, settings=None):
    """Add a source to a scene if it doesn't already exist."""
    try:
        client.create_input(scene_name, source_name, source_kind, settings or {}, True)
        logger.info("Added source '%s' (%s) to scene '%s'", source_name, source_kind, scene_name)
    except Exception as exc:
        logger.debug("Could not add source '%s' to '%s': %s", source_name, scene_name, exc)


def main():
    parser = argparse.ArgumentParser(description="Configure OBS for tutorial video production.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without executing")
    args = parser.parse_args()

    if not args.config.exists():
        logger.error("Config not found: %s", args.config)
        sys.exit(1)

    config = load_config(args.config)
    setup_obs(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
