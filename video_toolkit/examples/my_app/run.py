#!/usr/bin/env python3
"""
My App Tutorial — Video Automation Orchestrator
================================================
Run the complete video production pipeline for the "My App" tutorial.

Usage (Desktop/OBS mode):
    python run.py --all                   # Run complete pipeline
    python run.py --all --from 1          # Resume from sequence 1
    python run.py --sequence 0            # Run only sequence 0
    python run.py --setup-obs             # Auto-configure OBS

Usage (Docker/headless frame capture):
    python run.py --capture --all         # Headless frame capture mode

Utility commands:
    python run.py --diagrams              # Generate diagram HTML/PNG
    python run.py --narration             # Generate TTS audio files
    python run.py --calibrate             # Interactive UI calibration
    python run.py --assemble              # Assemble final video from clips
    python run.py --dry-run               # Preview without executing
    python run.py --list                  # List all sequences
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add the video_toolkit to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Windows: reconfigure stdout/stderr to UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import click

# ── Project imports ────────────────────────────────────────────────────────

from automator import NotepadAutomator
from sequences import SEQUENCES
from diagrams import DIAGRAMS

from toolkit.cli import make_cli, load_config
from toolkit.diagram_generator import DiagramGenerator
from toolkit.narrator import Narrator

# ── Logging setup ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run")

CONFIG_PATH = Path(__file__).parent / "config.yaml"


# ── App automator factory ─────────────────────────────────────────────────

def make_automator(config: dict) -> NotepadAutomator:
    """Factory function that creates the app automator from config."""
    return NotepadAutomator(config)


# ── Build the CLI ─────────────────────────────────────────────────────────

cli = make_cli(
    project_name="My App Tutorial",
    config_path=CONFIG_PATH,
    sequences=SEQUENCES,
    automator_factory=make_automator,
    default_output_name="my_app_tutorial_final.mp4",
)


# ── Override --diagrams and --narration commands ──────────────────────────
# The generic CLI calls ctx.obj["diagrams_func"] and ctx.obj["narration_func"]
# if registered. Override these to use your project's DIAGRAMS dict.

@cli.command("diagrams-gen")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def cmd_diagrams(ctx, dry_run):
    """Generate Mermaid diagram HTML/PNG files."""
    cfg = ctx.obj["config"]
    gen = DiagramGenerator(cfg.get("diagrams", {}))
    out_dir = Path(cfg.get("diagrams", {}).get("output_dir", "output/diagrams"))

    if dry_run:
        click.echo(f"[DRY-RUN] Would generate {len(DIAGRAMS)} diagrams in {out_dir}")
        return

    click.echo(f"\nGenerating {len(DIAGRAMS)} diagrams...")
    html_paths = gen.generate_all_diagrams(DIAGRAMS, out_dir)
    click.echo(f"  ok HTML files in {out_dir}")

    click.echo("Rendering to PNG (requires Playwright)...")
    png_paths = gen.render_all_to_png(html_paths, out_dir)
    click.echo(f"  ok {len(png_paths)} PNG files" if png_paths else
               "  !! No PNG files (install: pip install playwright && playwright install chromium)")
    click.echo(f"\nDone! {len(html_paths)} diagrams.\n")


@cli.command("narration-gen")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def cmd_narration(ctx, dry_run):
    """Generate TTS narration audio for all sequences."""
    cfg = ctx.obj["config"]
    narrator = Narrator(cfg.get("narration", {}))
    out_dir = Path(cfg.get("narration", {}).get("output_dir", "output/narration"))

    # Collect narration texts from all sequences
    script_dict = {}
    for SeqClass in SEQUENCES:
        seq = SeqClass()
        if seq.narration_text:
            script_dict[seq.sequence_id] = seq.narration_text

    if dry_run:
        click.echo(f"[DRY-RUN] Would generate {len(script_dict)} narration files in {out_dir}")
        return

    click.echo(f"\nGenerating narration for {len(script_dict)} sequences...")
    results = narrator.generate_all_narrations(script_dict, out_dir)
    click.echo(f"\nDone! {len(results)} audio files in {out_dir}\n")

    total = 0.0
    for seq_id, path in results.items():
        dur = narrator.get_narration_duration(path)
        total += dur
        click.echo(f"  {seq_id:20s} {dur:5.1f}s  -> {path.name}")
    mins, secs = divmod(int(total), 60)
    click.echo(f"\n  Total narration: {mins}m {secs:02d}s\n")


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        cli(standalone_mode=False)
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        sys.exit(1)
