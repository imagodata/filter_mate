"""
Generic CLI Framework
======================
Provides a reusable Click-based CLI for any video automation project
built with the video_toolkit.

Import this module in your project's run.py and call ``make_cli()``
to get a pre-wired Click group that you can extend with project-specific
commands.

Usage in your project's run.py::

    from toolkit.cli import make_cli

    # Load your sequences
    from my_app.sequences import SEQUENCES

    # Create the CLI
    cli = make_cli(
        project_name="My App Tutorial",
        config_path=Path("config.yaml"),
        sequences=SEQUENCES,
        automator_factory=lambda cfg: MyAppAutomator(cfg),
    )

    if __name__ == "__main__":
        cli()
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import click
import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load and return config.yaml as a dict."""
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    logger.debug("Config loaded from %s", config_path)
    return cfg


def make_cli(
    project_name: str,
    config_path: Path,
    sequences: list,
    automator_factory: Callable,
    extra_video_maps: Optional[dict[str, list]] = None,
    default_output_name: str = "tutorial_final.mp4",
) -> click.Group:
    """
    Build a complete Click CLI for a video automation project.

    Parameters
    ----------
    project_name : str
        Display name for the project (shown in help text and logs).
    config_path : Path
        Default path to config.yaml.
    sequences : list
        Default list of sequence classes to run.
    automator_factory : callable
        Factory function ``(config) -> AppAutomator`` for your app.
    extra_video_maps : dict, optional
        Additional video scripts: ``{"v01": [Seq1, Seq2, ...], ...}``.
    default_output_name : str
        Filename for the assembled final video.

    Returns
    -------
    click.Group
        Configured Click CLI group.
    """
    # Windows: reconfigure stdout/stderr to UTF-8
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass

    def _load_sequences(video: Optional[str]) -> list:
        if video and extra_video_maps and video in extra_video_maps:
            return extra_video_maps[video]
        return sequences

    @click.group(invoke_without_command=True)
    @click.option("--config", type=click.Path(exists=True, dir_okay=False),
                  default=str(config_path), help="Path to config.yaml", show_default=True)
    @click.option("--all", "run_all", is_flag=True,
                  help="Run complete video production pipeline")
    @click.option("--video", type=str, default=None, metavar="VXX",
                  help="Video script to use (e.g. 'v01')")
    @click.option("--sequence", "-s", type=int, default=None, metavar="N",
                  help="Run only sequence N")
    @click.option("--from", "start_from", type=int, default=None, metavar="N",
                  help="Resume pipeline from sequence N")
    @click.option("--diagrams", is_flag=True, help="Generate Mermaid diagram HTML/PNG files")
    @click.option("--narration", is_flag=True, help="Generate TTS narration audio files")
    @click.option("--calibrate", is_flag=True, help="Run interactive UI calibration")
    @click.option("--setup-obs", "setup_obs", is_flag=True, help="Auto-configure OBS")
    @click.option("--assemble", is_flag=True, help="Assemble final video from recorded clips")
    @click.option("--capture", is_flag=True,
                  help="Use headless frame capture instead of OBS (Docker/Xvfb mode)")
    @click.option("--capture-fps", "capture_fps", type=int, default=None,
                  help="Override capture FPS")
    @click.option("--dry-run", "dry_run", is_flag=True,
                  help="Preview without executing any actions")
    @click.option("--list", "list_seqs", is_flag=True,
                  help="List all sequences with details")
    @click.option("--verbose", "-v", is_flag=True,
                  help="Enable verbose (DEBUG) logging")
    @click.pass_context
    def cli(ctx, config, video, run_all, sequence, start_from, diagrams, narration,
            calibrate, setup_obs, assemble, capture, capture_fps, dry_run,
            list_seqs, verbose):
        f"""{project_name} — Video Automation CLI"""
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        cfg = load_config(Path(config))
        if capture_fps is not None:
            cfg.setdefault("capture", {})["fps"] = capture_fps

        ctx.ensure_object(dict)
        ctx.obj.update({
            "config": cfg, "dry_run": dry_run,
            "video": video, "capture": capture,
        })

        if list_seqs:
            _cmd_list(cfg, video, _load_sequences, project_name, extra_video_maps)
            return
        if calibrate:
            _cmd_calibrate(cfg, dry_run, config_path)
            return
        if setup_obs:
            _cmd_setup_obs(cfg, dry_run)
            return
        if diagrams:
            ctx.obj["diagrams_func"](cfg, dry_run) if ctx.obj.get("diagrams_func") else \
                click.echo("No diagrams_func registered. Override this command in your run.py.")
            return
        if narration:
            ctx.obj["narration_func"](cfg, dry_run, video) if ctx.obj.get("narration_func") else \
                click.echo("No narration_func registered. Override this command in your run.py.")
            return
        if assemble:
            _cmd_assemble(cfg, dry_run, video=video, output_name=default_output_name)
            return
        if sequence is not None:
            _cmd_run_sequence(
                cfg, sequence, dry_run, video=video, use_capture=capture,
                load_sequences=_load_sequences, automator_factory=automator_factory,
            )
            return
        if run_all:
            _cmd_run_all(
                cfg, dry_run, video=video, use_capture=capture, start_from=start_from,
                load_sequences=_load_sequences, automator_factory=automator_factory,
                output_name=default_output_name,
            )
            return

        click.echo(ctx.get_help())

    return cli


# ---------------------------------------------------------------------------
# Command implementations (used internally by make_cli)
# ---------------------------------------------------------------------------

def _cmd_list(config, video, load_sequences, project_name, extra_video_maps=None):
    seqs = load_sequences(video)
    label = f"Video {video.upper()}" if video else "Default"
    click.echo(f"\n  {project_name} — Sequences ({label})\n  " + "─" * 55)
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
    if extra_video_maps:
        click.echo(f"  Available video scripts: {', '.join(extra_video_maps.keys())}\n")


def _cmd_calibrate(config, dry_run, config_path):
    if dry_run:
        click.echo("[DRY-RUN] Would launch calibrate.py")
        return
    import subprocess
    calibrate_script = Path(__file__).parent.parent / "scripts" / "calibrate.py"
    result = subprocess.run(
        [sys.executable, str(calibrate_script), "--config", str(config_path)]
    )
    if result.returncode != 0:
        sys.exit(result.returncode)


def _cmd_setup_obs(config, dry_run):
    scripts_dir = Path(__file__).parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from setup_obs import setup_obs  # type: ignore
    setup_obs(config, dry_run=dry_run)


def _cmd_assemble(
    config, dry_run, clips=None, video=None, timeline_results=None, output_name="tutorial_final.mp4"
):
    from toolkit.video_assembler import VideoAssembler

    out_cfg = config.get("output", {})
    assembler = VideoAssembler(out_cfg)
    final_dir = Path(out_cfg.get("final_dir", "output/final"))

    if clips is None:
        obs_output = Path(config.get("obs", {}).get("output_dir", "output/recordings"))
        clips = sorted(str(p) for p in obs_output.glob("*.mkv"))
        if not clips:
            click.echo(f"No MKV clips found in {obs_output}. Record first with --all.")
            return

    if video:
        base = output_name.rsplit(".", 1)
        output_name = f"{base[0]}_{video}.{base[1]}" if len(base) == 2 else f"{output_name}_{video}"

    has_timecodes = (
        timeline_results and any(tr is not None for _, tr in timeline_results)
    )

    if dry_run:
        mode = "timecode-based" if has_timecodes else "legacy concat"
        click.echo(f"[DRY-RUN] Would assemble {len(clips)} clips ({mode})")
        click.echo(f"          Output: {final_dir / output_name}")
        return

    if has_timecodes:
        click.echo(f"\nAssembling {len(clips)} clips with timecode-based narration...")
        final_path = assembler.create_final_video_with_timecodes(
            clips=clips,
            timeline_results=[tr for _, tr in timeline_results],
            output_path=final_dir / output_name,
        )
    else:
        narr_dir = Path(config.get("narration", {}).get("output_dir", "output/narration"))
        if video:
            narr_dir = narr_dir / video
        narration_files = sorted(narr_dir.glob("*_narration.mp3"))
        click.echo(f"\nAssembling {len(clips)} clips + {len(narration_files)} narrations...")
        final_path = assembler.create_final_video(
            clips=clips,
            narrations=list(narration_files),
            output_path=final_dir / output_name,
        )

    click.echo(f"\n  ok Final video: {final_path}\n")


def _cmd_run_sequence(config, seq_num, dry_run, video, use_capture, load_sequences, automator_factory):
    seqs = load_sequences(video)
    if seq_num < 0 or seq_num >= len(seqs):
        click.echo(f"Error: sequence {seq_num} out of range (0-{len(seqs) - 1})")
        sys.exit(1)

    seq = seqs[seq_num]()
    backend = "FrameCapture" if use_capture else "OBS"
    if dry_run:
        click.echo(f"[DRY-RUN] Would run: {seq.name} (backend: {backend})")
        click.echo(f"          Estimated duration: {seq.duration_estimate:.0f}s")
        return

    click.echo(f"\nRunning sequence {seq_num}: {seq.name}\n")
    recorder, app = _init_controllers(config, use_capture, automator_factory)
    with recorder:
        recorder.start_recording()
        recorder.wait_for_recording_start()
        try:
            seq.run(recorder, app, config)
        finally:
            output_path = recorder.stop_recording()
            click.echo(f"\n  Recording saved: {output_path}")


def _cmd_run_all(config, dry_run, video, use_capture, start_from, load_sequences,
                 automator_factory, output_name):
    seqs = load_sequences(video)
    backend = "FrameCapture" if use_capture else "OBS"

    click.echo("\n" + "=" * 65)
    click.echo(f"  Video Automation — Complete Pipeline ({backend})")
    click.echo("=" * 65)

    if start_from is not None and (start_from < 0 or start_from >= len(seqs)):
        click.echo(f"Error: --from {start_from} out of range (0-{len(seqs) - 1})")
        sys.exit(1)

    if dry_run:
        click.echo(f"\n[DRY-RUN] Would run these sequences (backend: {backend}):\n")
        for i, SeqClass in enumerate(seqs):
            seq = SeqClass()
            skipped = start_from is not None and i < start_from
            marker = "SKIP" if skipped else " RUN"
            click.echo(f"  [{marker}] [{i}] {seq.name:<40} {seq.duration_estimate:.0f}s")
        return

    recorder, app = _init_controllers(config, use_capture, automator_factory)
    recording_files: list[str] = []
    all_timeline_results: list[tuple[str, object]] = []

    with recorder:
        for i, SeqClass in enumerate(seqs):
            if start_from is not None and i < start_from:
                click.echo(f"\n[{i}/{len(seqs)-1}] {SeqClass().name}  -- SKIP")
                continue

            seq = SeqClass()
            click.echo(f"\n[{i}/{len(seqs)-1}] {seq.name}")

            recorder.start_recording()
            recorder.wait_for_recording_start()
            try:
                seq.run(recorder, app, config)
            except KeyboardInterrupt:
                click.echo("\n  Interrupted by user.")
                output_path = recorder.stop_recording()
                if output_path:
                    recording_files.append(output_path)
                    all_timeline_results.append((output_path, seq.timeline_result))
                break
            except Exception as exc:
                logger.error("Sequence %d failed: %s", i, exc)
                click.echo(f"  x Sequence {i} failed: {exc}")
            finally:
                output_path = recorder.stop_recording()
                if output_path:
                    recording_files.append(output_path)
                    all_timeline_results.append((output_path, seq.timeline_result))
                    click.echo(f"  ok Saved: {output_path}")
                    if seq.timeline_result:
                        click.echo(
                            f"     Timeline: {len(seq.timeline_result.narration_timecodes)} segments"
                        )
                time.sleep(3)  # Let recorder finalize the file

    click.echo(f"\nRecorded {len(recording_files)} clips.")
    if recording_files:
        click.echo("\nProceeding to assembly...")
        _cmd_assemble(
            config, dry_run=False, clips=recording_files, video=video,
            timeline_results=all_timeline_results, output_name=output_name,
        )


def _init_controllers(config, use_capture, automator_factory):
    """Instantiate the recording backend and app automator."""
    if use_capture:
        from toolkit.frame_capturer import FrameCapturer
        recorder = FrameCapturer(config.get("capture", {}))
    else:
        from toolkit.obs_controller import OBSController
        recorder = OBSController(config.get("obs", {}))

    app = automator_factory(config)
    return recorder, app
