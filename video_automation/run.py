#!/usr/bin/env python3
"""
FilterMate Video Automation — Main Orchestrator
================================================
Controls the full video production pipeline: diagrams, narration,
QGIS automation via PyAutoGUI, OBS recording, and FFmpeg assembly.

Usage:
    python run.py --all                    # Run complete video production
    python run.py --sequence 4             # Run only sequence 4
    python run.py --diagrams               # Generate only diagrams
    python run.py --narration              # Generate only narration audio
    python run.py --calibrate              # Interactive UI calibration
    python run.py --setup-obs              # Auto-configure OBS
    python run.py --assemble               # Assemble final video from recorded clips
    python run.py --dry-run                # Preview without executing
    python run.py --list                   # List all sequences
    python run.py --help                   # Full help
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import click
import yaml

# ── Logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run")

CONFIG_PATH = Path(__file__).parent / "config.yaml"


# ── Config loader ──────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    """Load and return config.yaml as a dict."""
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    logger.debug("Config loaded from %s", config_path)
    return cfg


# ── CLI entry point ────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--config", type=click.Path(exists=True, dir_okay=False), default=str(CONFIG_PATH),
              help="Path to config.yaml", show_default=True)
@click.option("--all", "run_all", is_flag=True, help="Run complete video production pipeline")
@click.option("--sequence", "-s", type=int, default=None, metavar="N",
              help="Run only sequence N (0–10)")
@click.option("--diagrams", is_flag=True, help="Generate Mermaid diagram HTML/PNG files")
@click.option("--narration", is_flag=True, help="Generate TTS narration audio files")
@click.option("--calibrate", is_flag=True, help="Run interactive UI calibration")
@click.option("--setup-obs", "setup_obs", is_flag=True, help="Auto-configure OBS scenes/sources")
@click.option("--assemble", is_flag=True, help="Assemble final video from recorded clips")
@click.option("--dry-run", "dry_run", is_flag=True, help="Preview without executing any actions")
@click.option("--list", "list_seqs", is_flag=True, help="List all sequences with details")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose (DEBUG) logging")
@click.pass_context
def cli(ctx, config, run_all, sequence, diagrams, narration, calibrate,
        setup_obs, assemble, dry_run, list_seqs, verbose):
    """FilterMate Video Automation — orchestrates QGIS + OBS + FFmpeg."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    cfg = load_config(Path(config))
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg
    ctx.obj["dry_run"] = dry_run

    # Dispatch based on flags
    if list_seqs:
        cmd_list(cfg)
        return

    if calibrate:
        cmd_calibrate(cfg, dry_run)
        return

    if setup_obs:
        cmd_setup_obs(cfg, dry_run)
        return

    if diagrams:
        cmd_diagrams(cfg, dry_run)
        return

    if narration:
        cmd_narration(cfg, dry_run)
        return

    if assemble:
        cmd_assemble(cfg, dry_run)
        return

    if sequence is not None:
        cmd_run_sequence(cfg, sequence, dry_run)
        return

    if run_all:
        cmd_run_all(cfg, dry_run)
        return

    # No flag given — show help
    click.echo(ctx.get_help())


# ── Sub-command implementations ────────────────────────────────────────────

def cmd_list(config: dict) -> None:
    """Print a table of all sequences."""
    from sequences import SEQUENCES  # type: ignore

    click.echo("\n  FilterMate Video Sequences\n  " + "─" * 55)
    click.echo(f"  {'#':<4} {'Name':<40} {'Duration':>8}s")
    click.echo("  " + "─" * 55)
    total = 0.0
    for i, SeqClass in enumerate(SEQUENCES):
        seq = SeqClass()
        click.echo(f"  {i:<4} {seq.name:<40} {seq.duration_estimate:>8.0f}")
        total += seq.duration_estimate
    click.echo("  " + "─" * 55)
    mins, secs = divmod(int(total), 60)
    click.echo(f"  {'TOTAL':<44} {mins}m {secs:02d}s\n")


def cmd_calibrate(config: dict, dry_run: bool) -> None:
    """Run interactive calibration."""
    if dry_run:
        click.echo("[DRY-RUN] Would launch calibrate.py")
        return
    import subprocess
    calibrate_script = Path(__file__).parent / "scripts" / "calibrate.py"
    subprocess.run([sys.executable, str(calibrate_script), "--config", str(CONFIG_PATH)], check=True)


def cmd_setup_obs(config: dict, dry_run: bool) -> None:
    """Configure OBS scenes and sources."""
    sys.path.insert(0, str(Path(__file__).parent / "scripts"))
    from setup_obs import setup_obs  # type: ignore
    setup_obs(config, dry_run=dry_run)


def cmd_diagrams(config: dict, dry_run: bool) -> None:
    """Generate all Mermaid diagram HTML files (and optionally PNG)."""
    from core.diagram_generator import DiagramGenerator
    from diagrams.mermaid_definitions import DIAGRAMS

    gen = DiagramGenerator(config.get("diagrams", {}))
    out_dir = Path(config.get("diagrams", {}).get("output_dir", "output/diagrams"))

    if dry_run:
        click.echo(f"[DRY-RUN] Would generate {len(DIAGRAMS)} diagrams in {out_dir}")
        for diag_id, info in DIAGRAMS.items():
            click.echo(f"          {diag_id}: {info['title']}")
        return

    click.echo(f"\nGenerating {len(DIAGRAMS)} diagrams…")
    html_paths = gen.generate_all_diagrams(DIAGRAMS, out_dir)
    click.echo(f"  ✓ HTML files in {out_dir}")

    # Attempt PNG rendering
    click.echo("Rendering to PNG (requires Playwright)…")
    png_paths = gen.render_all_to_png(html_paths, out_dir)
    if png_paths:
        click.echo(f"  ✓ PNG files in {out_dir}")
    else:
        click.echo("  ⚠ No PNG files (install Playwright: pip install playwright && playwright install chromium)")

    click.echo(f"\nDone! {len(html_paths)} HTML, {len(png_paths)} PNG diagrams generated.\n")


def cmd_narration(config: dict, dry_run: bool) -> None:
    """Generate TTS narration audio for all sequences."""
    from core.narrator import Narrator, NARRATION_TEXTS

    narrator = Narrator(config.get("narration", {}))
    out_dir = Path(config.get("narration", {}).get("output_dir", "output/narration"))

    if dry_run:
        click.echo(f"[DRY-RUN] Would generate {len(NARRATION_TEXTS)} narration files in {out_dir}")
        for seq_id, text in NARRATION_TEXTS.items():
            click.echo(f"          {seq_id}: {text[:60]}…")
        return

    click.echo(f"\nGenerating narration for {len(NARRATION_TEXTS)} sequences…")
    results = narrator.generate_all_narrations(NARRATION_TEXTS, out_dir)
    click.echo(f"\nDone! {len(results)} audio files in {out_dir}\n")

    # Show durations
    total = 0.0
    for seq_id, path in results.items():
        dur = narrator.get_narration_duration(path)
        total += dur
        click.echo(f"  {seq_id:20s} {dur:5.1f}s  → {path.name}")
    mins, secs = divmod(int(total), 60)
    click.echo(f"\n  Total narration: {mins}m {secs:02d}s\n")


def cmd_run_sequence(config: dict, seq_num: int, dry_run: bool) -> None:
    """Run a single sequence."""
    from sequences import SEQUENCES

    if seq_num < 0 or seq_num >= len(SEQUENCES):
        click.echo(f"Error: sequence {seq_num} out of range (0–{len(SEQUENCES) - 1})")
        sys.exit(1)

    SeqClass = SEQUENCES[seq_num]
    seq = SeqClass()

    if dry_run:
        click.echo(f"[DRY-RUN] Would run: {seq.name}")
        click.echo(f"          Estimated duration: {seq.duration_estimate:.0f}s")
        click.echo(f"          OBS scene: {seq.obs_scene}")
        click.echo(f"          Diagrams: {seq.diagram_ids}")
        return

    click.echo(f"\nRunning sequence {seq_num}: {seq.name}\n")
    obs, qgis = _init_controllers(config)
    with obs:
        obs.start_recording()
        obs.wait_for_recording_start()
        try:
            seq.run(obs, qgis, config)
        finally:
            output_path = obs.stop_recording()
            click.echo(f"\n  Recording saved: {output_path}")


def cmd_run_all(config: dict, dry_run: bool) -> None:
    """Run the complete video production pipeline."""
    from sequences import SEQUENCES

    click.echo("\n" + "=" * 65)
    click.echo("  FilterMate — Complete Video Production")
    click.echo("=" * 65)

    if dry_run:
        click.echo("\n[DRY-RUN] Would run these sequences:\n")
        for i, SeqClass in enumerate(SEQUENCES):
            seq = SeqClass()
            click.echo(f"  [{i}] {seq.name:<40} {seq.duration_estimate:.0f}s")
        return

    # Check prerequisites
    _check_prerequisites(config)

    obs, qgis = _init_controllers(config)

    recording_files: list[str] = []
    with obs:
        for i, SeqClass in enumerate(SEQUENCES):
            seq = SeqClass()
            click.echo(f"\n[{i}/{len(SEQUENCES)-1}] {seq.name}")

            obs.start_recording()
            obs.wait_for_recording_start()
            try:
                seq.run(obs, qgis, config)
            except KeyboardInterrupt:
                click.echo("\n  ⚠ Interrupted by user.")
                output_path = obs.stop_recording()
                if output_path:
                    recording_files.append(output_path)
                break
            except Exception as exc:
                logger.error("Sequence %d failed: %s", i, exc)
                click.echo(f"  ✗ Sequence {i} failed: {exc}")
            finally:
                output_path = obs.stop_recording()
                if output_path:
                    recording_files.append(output_path)
                    click.echo(f"  ✓ Saved: {output_path}")

    click.echo(f"\nRecorded {len(recording_files)} clips.")

    if recording_files:
        click.echo("\nProceeding to assembly…")
        cmd_assemble(config, dry_run=False, clips=recording_files)


def cmd_assemble(
    config: dict,
    dry_run: bool,
    clips: list[str] | None = None,
) -> None:
    """Assemble final video from recorded clips + narration + diagrams."""
    from core.video_assembler import VideoAssembler
    from core.narrator import NARRATION_TEXTS

    out_cfg = config.get("output", {})
    assembler = VideoAssembler(out_cfg)
    final_dir = Path(out_cfg.get("final_dir", "output/final"))
    narr_dir = Path(config.get("narration", {}).get("output_dir", "output/narration"))

    # Find recorded clips if not provided
    if clips is None:
        obs_output = Path(config.get("obs", {}).get("output_dir", "C:/Users/Simon/Videos/FilterMate"))
        clips = sorted(str(p) for p in obs_output.glob("*.mkv"))
        if not clips:
            click.echo(f"No MKV clips found in {obs_output}. Record first with --all or --sequence N.")
            return

    # Find narration files
    narration_files = sorted(narr_dir.glob("seq*_narration.mp3"))

    if dry_run:
        click.echo(f"[DRY-RUN] Would assemble {len(clips)} clips + {len(narration_files)} narrations")
        click.echo(f"          Output: {final_dir / 'filtermate_final.mp4'}")
        return

    click.echo(f"\nAssembling {len(clips)} clips…")
    final_path = assembler.create_final_video(
        clips=clips,
        narrations=list(narration_files),
        output_path=final_dir / "filtermate_final.mp4",
    )
    click.echo(f"\n  ✓ Final video: {final_path}\n")


# ── Helpers ────────────────────────────────────────────────────────────────

def _init_controllers(config: dict):
    """Instantiate OBS and QGIS controllers."""
    from core.obs_controller import OBSController
    from core.qgis_automator import QGISAutomator

    obs = OBSController(config.get("obs", {}))
    qgis = QGISAutomator(config)
    return obs, qgis


def _check_prerequisites(config: dict) -> None:
    """Warn if common prerequisites are missing."""
    import shutil

    click.echo("\nChecking prerequisites…")
    checks = [
        ("ffmpeg", "FFmpeg"),
        ("python", "Python"),
    ]
    for cmd, label in checks:
        if shutil.which(cmd):
            click.echo(f"  ✓ {label}")
        else:
            click.echo(f"  ⚠ {label} not found on PATH")

    try:
        import pyautogui  # type: ignore
        click.echo("  ✓ pyautogui")
    except ImportError:
        click.echo("  ✗ pyautogui not installed (pip install pyautogui)")

    try:
        import obsws_python  # type: ignore
        click.echo("  ✓ obsws-python")
    except ImportError:
        click.echo("  ✗ obsws-python not installed (pip install obsws-python)")

    click.echo()


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli(standalone_mode=False)
