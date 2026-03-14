"""
Video Assembler
===============
Post-production pipeline: combines OBS recordings, diagram overlays,
and narration audio into the final video using FFmpeg.

Requires FFmpeg on PATH.

Usage:
    from core.video_assembler import VideoAssembler
    va = VideoAssembler(config["output"])
    va.remux_mkv_to_mp4("raw_recording.mkv")
    va.create_final_video(clips, narrations, diagrams, "output/final/filtermate.mp4")
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _check_ffmpeg() -> None:
    """Raise RuntimeError if FFmpeg is not available on PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg not found on PATH. "
            "Install from https://ffmpeg.org/download.html and add to PATH."
        )


def _run_ffmpeg(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run an FFmpeg command and return the result."""
    cmd = ["ffmpeg", "-y", *args]
    logger.debug("FFmpeg command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        logger.error("FFmpeg stderr:\n%s", result.stderr[-3000:])
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


class VideoAssembler:
    """
    Handles all FFmpeg-based post-production operations.

    Parameters
    ----------
    config : dict
        The 'output' section from config.yaml.
    """

    def __init__(self, config: dict) -> None:
        self.final_dir = Path(config.get("final_dir", "output/final"))
        self.resolution: str = config.get("resolution", "1920x1080")
        self.fps: int = config.get("fps", 30)
        self.codec: str = config.get("codec", "libx264")
        self.quality: str = str(config.get("quality", "23"))
        self.final_dir.mkdir(parents=True, exist_ok=True)
        _check_ffmpeg()

    # ------------------------------------------------------------------
    # Remux
    # ------------------------------------------------------------------

    def remux_mkv_to_mp4(self, mkv_path: str | Path, output_path: Optional[str | Path] = None) -> Path:
        """
        Losslessly remux an MKV to MP4 (no re-encoding).

        Parameters
        ----------
        mkv_path : str | Path
            Input MKV file.
        output_path : str | Path, optional
            Output MP4 path. Defaults to same location with .mp4 extension.

        Returns
        -------
        Path
            Path to the MP4 file.
        """
        mkv_path = Path(mkv_path)
        if output_path is None:
            output_path = mkv_path.with_suffix(".mp4")
        output_path = Path(output_path)

        _run_ffmpeg(
            "-i", str(mkv_path),
            "-c", "copy",
            str(output_path),
        )
        logger.info("Remuxed %s → %s", mkv_path.name, output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Narration
    # ------------------------------------------------------------------

    def add_narration(
        self,
        video_path: str | Path,
        narration_path: str | Path,
        output_path: str | Path,
        narration_volume: float = 1.0,
        original_volume: float = 0.3,
    ) -> Path:
        """
        Mix narration audio into the video, reducing original audio level.

        Parameters
        ----------
        video_path : str | Path
            Input video file.
        narration_path : str | Path
            Narration audio file (MP3 or WAV).
        output_path : str | Path
            Output video file.
        narration_volume : float
            Volume multiplier for narration (0.0–2.0).
        original_volume : float
            Volume multiplier for original video audio (0 = mute original).

        Returns
        -------
        Path
            Path to the output file.
        """
        video_path = Path(video_path)
        narration_path = Path(narration_path)
        output_path = Path(output_path)

        filter_complex = (
            f"[0:a]volume={original_volume}[orig];"
            f"[1:a]volume={narration_volume}[narr];"
            "[orig][narr]amix=inputs=2:duration=first:dropout_transition=3[aout]"
        )

        _run_ffmpeg(
            "-i", str(video_path),
            "-i", str(narration_path),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        )
        logger.info("Added narration to %s → %s", video_path.name, output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Diagram overlay
    # ------------------------------------------------------------------

    def combine_recording_with_diagrams(
        self,
        recording_path: str | Path,
        diagram_paths: list[str | Path],
        timestamps: list[float],
        output_path: str | Path,
        diagram_duration: float = 5.0,
        fade_duration: float = 0.5,
    ) -> Path:
        """
        Overlay diagram images onto the recording at specified timestamps.

        Each diagram is faded in and out as a picture-in-picture overlay.

        Parameters
        ----------
        recording_path : str | Path
            Main recording video.
        diagram_paths : list
            List of PNG image paths (one per timestamp).
        timestamps : list[float]
            Start times (seconds) for each diagram overlay.
        output_path : str | Path
            Output video file.
        diagram_duration : float
            How long each diagram stays on screen.
        fade_duration : float
            Fade in/out duration.

        Returns
        -------
        Path
        """
        recording_path = Path(recording_path)
        output_path = Path(output_path)

        if len(diagram_paths) != len(timestamps):
            raise ValueError("diagram_paths and timestamps must have the same length.")

        if not diagram_paths:
            logger.info("No diagrams to overlay; copying source.")
            shutil.copy2(recording_path, output_path)
            return output_path

        # Build FFmpeg filter_complex for each overlay
        inputs = ["-i", str(recording_path)]
        for dp in diagram_paths:
            inputs += ["-i", str(dp)]

        # Chain overlays
        filter_parts: list[str] = []
        prev_label = "0:v"
        for idx, (dp, ts) in enumerate(zip(diagram_paths, timestamps), start=1):
            fade_in = (
                f"[{idx}:v]"
                f"fade=t=in:st=0:d={fade_duration},"
                f"fade=t=out:st={diagram_duration - fade_duration}:d={fade_duration}[diag{idx}]"
            )
            overlay = (
                f"[{prev_label}][diag{idx}]"
                f"overlay=x=(W-w)/2:y=(H-h)/2:enable='between(t,{ts},{ts + diagram_duration})'[v{idx}]"
            )
            filter_parts.append(fade_in)
            filter_parts.append(overlay)
            prev_label = f"v{idx}"

        filter_complex = ";".join(filter_parts)

        _run_ffmpeg(
            *inputs,
            "-filter_complex", filter_complex,
            "-map", f"[{prev_label}]",
            "-map", "0:a?",
            "-c:v", self.codec,
            "-crf", self.quality,
            "-c:a", "copy",
            str(output_path),
        )
        logger.info("Combined recording with %d diagrams → %s", len(diagram_paths), output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Intro / Outro
    # ------------------------------------------------------------------

    def add_intro_outro(
        self,
        video_path: str | Path,
        intro_path: Optional[str | Path],
        outro_path: Optional[str | Path],
        output_path: str | Path,
    ) -> Path:
        """
        Concatenate intro + main video + outro using FFmpeg concat demuxer.

        Parameters
        ----------
        video_path : str | Path
            Main video clip.
        intro_path : str | Path, optional
            Intro clip.
        outro_path : str | Path, optional
            Outro clip.
        output_path : str | Path
            Final output.

        Returns
        -------
        Path
        """
        output_path = Path(output_path)
        clips: list[Path] = []
        if intro_path and Path(intro_path).exists():
            clips.append(Path(intro_path))
        clips.append(Path(video_path))
        if outro_path and Path(outro_path).exists():
            clips.append(Path(outro_path))

        if len(clips) == 1:
            shutil.copy2(clips[0], output_path)
            return output_path

        # Create a temporary concat list file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            for clip in clips:
                tmp.write(f"file '{clip.resolve()}'\n")
            concat_file = tmp.name

        _run_ffmpeg(
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            str(output_path),
        )
        Path(concat_file).unlink(missing_ok=True)
        logger.info("Concatenated %d clips → %s", len(clips), output_path.name)
        return output_path

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def create_final_video(
        self,
        clips: list[str | Path],
        narrations: list[str | Path],
        diagrams: Optional[dict] = None,
        output_path: Optional[str | Path] = None,
    ) -> Path:
        """
        Full post-production pipeline:
        1. Concatenate all sequence clips.
        2. Mix narration audio.
        3. Encode final video.

        Parameters
        ----------
        clips : list
            Ordered list of video clip files (one per sequence).
        narrations : list
            Ordered list of narration audio files (matched to clips).
        diagrams : dict, optional
            Mapping of {timestamp: png_path} for diagram overlays (optional).
        output_path : str | Path, optional
            Final output path.

        Returns
        -------
        Path
        """
        if output_path is None:
            output_path = self.final_dir / "filtermate_final.mp4"
        output_path = Path(output_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Step 1: Concatenate all clips
            logger.info("Step 1/3: Concatenating %d clips…", len(clips))
            concat_path = tmp / "concatenated.mp4"
            if len(clips) == 1:
                shutil.copy2(clips[0], concat_path)
            else:
                self._concat_clips(clips, concat_path)

            # Step 2: Add narrations
            logger.info("Step 2/3: Mixing %d narration tracks…", len(narrations))
            if narrations:
                # Concatenate all narration audio first
                narr_concat = tmp / "narration_concat.mp3"
                self._concat_audio(narrations, narr_concat)
                narrated_path = tmp / "with_narration.mp4"
                self.add_narration(concat_path, narr_concat, narrated_path)
            else:
                narrated_path = concat_path

            # Step 3: Final encode
            logger.info("Step 3/3: Final encoding → %s", output_path.name)
            _run_ffmpeg(
                "-i", str(narrated_path),
                "-c:v", self.codec,
                "-crf", self.quality,
                "-preset", "slow",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-vf", f"scale={self.resolution.replace('x', ':')}",
                "-r", str(self.fps),
                str(output_path),
            )

        logger.info("Final video created: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _concat_clips(self, clips: list[str | Path], output_path: Path) -> None:
        """Concatenate video clips via FFmpeg concat demuxer."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            for clip in clips:
                tmp.write(f"file '{Path(clip).resolve()}'\n")
            concat_file = tmp.name
        _run_ffmpeg(
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            str(output_path),
        )
        Path(concat_file).unlink(missing_ok=True)

    def _concat_audio(self, audio_files: list[str | Path], output_path: Path) -> None:
        """Concatenate audio files into a single track."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            for af in audio_files:
                tmp.write(f"file '{Path(af).resolve()}'\n")
            concat_file = tmp.name
        _run_ffmpeg(
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            str(output_path),
        )
        Path(concat_file).unlink(missing_ok=True)
