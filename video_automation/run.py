#!/usr/bin/env python3
"""
FilterMate Video Automation — Main Orchestrator
================================================
Controls the full video production pipeline: diagrams, narration,
QGIS automation via PyAutoGUI, recording (OBS or headless frame capture),
and FFmpeg assembly.

Usage (Desktop/OBS mode):
    python run.py --all                    # Run complete pipeline with OBS
    python run.py --sequence 4             # Run only sequence 4
    python run.py --setup-obs              # Auto-configure OBS

Usage (Docker/headless frame capture):
    python run.py --capture --all          # Frame capture mode (Xvfb)
    python run.py --capture --all --capture-fps 15  # Custom FPS
    python run.py --capture --sequence 6 --video v01

Common:
    python run.py --diagrams               # Generate only diagrams
    python run.py --narration              # Generate only narration audio
    python run.py --calibrate              # Interactive UI calibration
    python run.py --assemble               # Assemble final video from clips
    python run.py --dry-run                # Preview without executing
    python run.py --list                   # List all sequences
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Windows: reconfigure stdout/stderr to UTF-8 to avoid UnicodeEncodeError
# when printing special characters (checkmarks, arrows, etc.) to cmd.exe.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

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
@click.option("--video", type=str, default=None, metavar="VXX",
              help="Video script to use (e.g. 'v01'). Defaults to original sequences.")
@click.option("--sequence", "-s", type=int, default=None, metavar="N",
              help="Run only sequence N (0–10 for original, 0–13 for v01)")
@click.option("--diagrams", is_flag=True, help="Generate Mermaid diagram HTML/PNG files")
@click.option("--narration", is_flag=True, help="Generate TTS narration audio files")
@click.option("--calibrate", is_flag=True, help="Run interactive UI calibration")
@click.option("--setup-obs", "setup_obs", is_flag=True, help="Auto-configure OBS scenes/sources")
@click.option("--assemble", is_flag=True, help="Assemble final video from recorded clips")
@click.option("--capture", is_flag=True, help="Use headless frame capture instead of OBS (Docker/Xvfb mode)")
@click.option("--capture-fps", "capture_fps", type=int, default=None, metavar="N",
              help="Override capture FPS (default: from config)")
@click.option("--dry-run", "dry_run", is_flag=True, help="Preview without executing any actions")
@click.option("--list", "list_seqs", is_flag=True, help="List all sequences with details")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose (DEBUG) logging")
@click.pass_context
def cli(ctx, config, video, run_all, sequence, diagrams, narration, calibrate,
        setup_obs, assemble, capture, capture_fps, dry_run, list_seqs, verbose):
    """FilterMate Video Automation — orchestrates QGIS + OBS/FrameCapture + FFmpeg."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    cfg = load_config(Path(config))

    # Override capture FPS if provided via CLI
    if capture_fps is not None:
        cfg.setdefault("capture", {})["fps"] = capture_fps

    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg
    ctx.obj["dry_run"] = dry_run
    ctx.obj["video"] = video
    ctx.obj["capture"] = capture

    # Dispatch based on flags
    if list_seqs:
        cmd_list(cfg, video=video)
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
        cmd_narration(cfg, dry_run, video=video)
        return

    if assemble:
        cmd_assemble(cfg, dry_run, video=video)
        return

    if sequence is not None:
        cmd_run_sequence(cfg, sequence, dry_run, video=video, use_capture=capture)
        return

    if run_all:
        cmd_run_all(cfg, dry_run, video=video, use_capture=capture)
        return

    # No flag given — show help
    click.echo(ctx.get_help())


# ── Sub-command implementations ────────────────────────────────────────────

def _load_sequences(video: str | None = None) -> list:
    """Load the right sequence list depending on --video flag."""
    if video == "v01":
        from sequences.v01 import V01_SEQUENCES
        return V01_SEQUENCES
    from sequences import SEQUENCES
    return SEQUENCES


def cmd_list(config: dict, video: str | None = None) -> None:
    """Print a table of all sequences."""
    seqs = _load_sequences(video)
    label = f"Video {video.upper()}" if video else "Original"

    click.echo(f"\n  FilterMate Video Sequences ({label})\n  " + "─" * 55)
    click.echo(f"  {'#':<4} {'Name':<40} {'Duration':>8}s")
    click.echo("  " + "─" * 55)
    total = 0.0
    for i, SeqClass in enumerate(seqs):
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
    result = subprocess.run([sys.executable, str(calibrate_script), "--config", str(CONFIG_PATH)])
    if result.returncode != 0:
        click.echo(f"  [WARN] calibrate.py exited with code {result.returncode}")
        sys.exit(result.returncode)


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


def cmd_narration(config: dict, dry_run: bool, video: str | None = None) -> None:
    """Generate TTS narration audio for all sequences."""
    from core.narrator import Narrator, get_narration_texts

    narrator = Narrator(config.get("narration", {}))
    narration_texts = get_narration_texts(video)
    label = video.upper() if video else "original"
    out_dir = Path(config.get("narration", {}).get("output_dir", "output/narration"))
    if video:
        out_dir = out_dir / video

    if dry_run:
        click.echo(f"[DRY-RUN] Would generate {len(narration_texts)} narration files ({label}) in {out_dir}")
        for seq_id, text in narration_texts.items():
            click.echo(f"          {seq_id}: {text[:60]}…")
        return

    click.echo(f"\nGenerating narration for {len(narration_texts)} sequences ({label})…")
    results = narrator.generate_all_narrations(narration_texts, out_dir)
    click.echo(f"\nDone! {len(results)} audio files in {out_dir}\n")

    # Show durations
    total = 0.0
    for seq_id, path in results.items():
        dur = narrator.get_narration_duration(path)
        total += dur
        click.echo(f"  {seq_id:20s} {dur:5.1f}s  → {path.name}")
    mins, secs = divmod(int(total), 60)
    click.echo(f"\n  Total narration: {mins}m {secs:02d}s\n")


def cmd_run_sequence(
    config: dict,
    seq_num: int,
    dry_run: bool,
    video: str | None = None,
    use_capture: bool = False,
) -> None:
    """Run a single sequence."""
    seqs = _load_sequences(video)

    if seq_num < 0 or seq_num >= len(seqs):
        click.echo(f"Error: sequence {seq_num} out of range (0–{len(seqs) - 1})")
        sys.exit(1)

    SeqClass = seqs[seq_num]
    seq = SeqClass()

    if dry_run:
        backend = "FrameCapture" if use_capture else "OBS"
        click.echo(f"[DRY-RUN] Would run: {seq.name} (backend: {backend})")
        click.echo(f"          Estimated duration: {seq.duration_estimate:.0f}s")
        click.echo(f"          Scene: {seq.obs_scene}")
        click.echo(f"          Diagrams: {seq.diagram_ids}")
        return

    click.echo(f"\nRunning sequence {seq_num}: {seq.name}\n")
    recorder, qgis = _init_controllers(config, use_capture=use_capture)
    with recorder:
        recorder.start_recording()
        recorder.wait_for_recording_start()
        try:
            seq.run(recorder, qgis, config)
        finally:
            output_path = recorder.stop_recording()
            click.echo(f"\n  Recording saved: {output_path}")


def cmd_run_all(
    config: dict,
    dry_run: bool,
    video: str | None = None,
    use_capture: bool = False,
) -> None:
    """Run the complete video production pipeline."""
    SEQUENCES = _load_sequences(video)
    backend = "FrameCapture" if use_capture else "OBS"

    click.echo("\n" + "=" * 65)
    click.echo(f"  FilterMate — Complete Video Production ({backend})")
    click.echo("=" * 65)

    if dry_run:
        click.echo(f"\n[DRY-RUN] Would run these sequences (backend: {backend}):\n")
        for i, SeqClass in enumerate(SEQUENCES):
            seq = SeqClass()
            click.echo(f"  [{i}] {seq.name:<40} {seq.duration_estimate:.0f}s")
        return

    # Check prerequisites
    _check_prerequisites(config, use_capture=use_capture)

    recorder, qgis = _init_controllers(config, use_capture=use_capture)

    recording_files: list[str] = []
    with recorder:
        for i, SeqClass in enumerate(SEQUENCES):
            seq = SeqClass()
            click.echo(f"\n[{i}/{len(SEQUENCES)-1}] {seq.name}")

            recorder.start_recording()
            recorder.wait_for_recording_start()
            try:
                seq.run(recorder, qgis, config)
            except KeyboardInterrupt:
                click.echo("\n  Interrupted by user.")
                output_path = recorder.stop_recording()
                if output_path:
                    recording_files.append(output_path)
                break
            except Exception as exc:
                logger.error("Sequence %d failed: %s", i, exc)
                click.echo(f"  x Sequence {i} failed: {exc}")
            finally:
                output_path = recorder.stop_recording()
                if output_path:
                    recording_files.append(output_path)
                    click.echo(f"  ok Saved: {output_path}")
                # OBS needs time to finalize the file before starting a new recording
                time.sleep(3)

    click.echo(f"\nRecorded {len(recording_files)} clips.")

    if recording_files:
        click.echo("\nProceeding to assembly...")
        cmd_assemble(config, dry_run=False, clips=recording_files, video=video)


def cmd_assemble(
    config: dict,
    dry_run: bool,
    clips: list[str] | None = None,
    video: str | None = None,
) -> None:
    """Assemble final video from recorded clips + narration + diagrams."""
    from core.video_assembler import VideoAssembler

    out_cfg = config.get("output", {})
    assembler = VideoAssembler(out_cfg)
    final_dir = Path(out_cfg.get("final_dir", "output/final"))
    narr_dir = Path(config.get("narration", {}).get("output_dir", "output/narration"))
    if video:
        narr_dir = narr_dir / video

    # Find recorded clips if not provided
    if clips is None:
        default_obs_dir = Path.home() / "Videos" / "FilterMate"
        obs_output = Path(config.get("obs", {}).get("output_dir", str(default_obs_dir)))
        clips = sorted(str(p) for p in obs_output.glob("*.mkv"))
        if not clips:
            click.echo(f"No MKV clips found in {obs_output}. Record first with --all or --sequence N.")
            return

    # Find narration files (support both original seq* and v01 patterns)
    narration_files = sorted(narr_dir.glob("*_narration.mp3"))

    output_name = f"filtermate_{video}_final.mp4" if video else "filtermate_final.mp4"

    if dry_run:
        click.echo(f"[DRY-RUN] Would assemble {len(clips)} clips + {len(narration_files)} narrations")
        click.echo(f"          Output: {final_dir / output_name}")
        return

    click.echo(f"\nAssembling {len(clips)} clips…")
    final_path = assembler.create_final_video(
        clips=clips,
        narrations=list(narration_files),
        output_path=final_dir / output_name,
    )
    click.echo(f"\n  ok Final video: {final_path}\n")


# ── Helpers ────────────────────────────────────────────────────────────────

def _init_controllers(config: dict, use_capture: bool = False):
    """
    Instantiate the recording backend and QGIS controller.

    Parameters
    ----------
    use_capture : bool
        If True, use FrameCapturer (headless/Docker). Otherwise use OBSController.
    """
    from core.qgis_automator import QGISAutomator

    if use_capture:
        from core.frame_capturer import FrameCapturer
        recorder = FrameCapturer(config.get("capture", {}))
    else:
        from core.obs_controller import OBSController
        recorder = OBSController(config.get("obs", {}))

    qgis = QGISAutomator(config)
    return recorder, qgis


def _check_prerequisites(config: dict, use_capture: bool = False) -> None:
    """Warn if common prerequisites are missing."""
    import shutil

    backend = "FrameCapture" if use_capture else "OBS"
    click.echo(f"\nChecking prerequisites (backend: {backend})...")

    checks = [
        ("ffmpeg", "FFmpeg"),
        (sys.executable if use_capture else "python", "Python"),
    ]
    for cmd, label in checks:
        if shutil.which(cmd):
            click.echo(f"  ok {label}")
        else:
            click.echo(f"  !! {label} not found on PATH")

    try:
        import pyautogui  # type: ignore
        click.echo("  ok pyautogui")
    except ImportError:
        click.echo("  xx pyautogui not installed (pip install pyautogui)")

    if use_capture:
        # Frame capture prerequisites
        for tool in ["xdotool", "scrot", "import"]:
            if shutil.which(tool):
                click.echo(f"  ok {tool}")
            else:
                click.echo(f"  !! {tool} not found (optional)")

        display = config.get("capture", {}).get("display", ":99")
        import os
        if os.environ.get("DISPLAY"):
            click.echo(f"  ok DISPLAY={os.environ['DISPLAY']}")
        else:
            click.echo(f"  !! DISPLAY not set (expected {display})")
    else:
        try:
            import obsws_python  # type: ignore
            click.echo("  ok obsws-python")
        except ImportError:
            click.echo("  xx obsws-python not installed (pip install obsws-python)")

    click.echo()


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        cli(standalone_mode=False)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Fatal error: %s", exc)
        sys.exit(1)
