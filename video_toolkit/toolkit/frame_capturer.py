"""
Frame Capturer — Headless Screen Capture for Docker/Xvfb
=========================================================
Replaces OBS for headless video production. Captures the Xvfb virtual
display at configurable FPS, saves numbered PNG frames, and assembles
them into video via FFmpeg.

Implements the same interface as OBSController so sequences work with
both backends transparently.

Usage:
    capturer = FrameCapturer(config)
    with capturer:
        capturer.start_recording()
        # ... automation happens ...
        output_path = capturer.stop_recording()

    # Or standalone assembly:
    capturer.assemble_frames("/path/to/frames", "output.mp4", fps=30)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FrameCapturer:
    """
    Captures the virtual display as numbered PNG frames and assembles
    them into video with FFmpeg.

    Implements the same interface as OBSController so sequences can
    use either backend transparently.

    Parameters
    ----------
    config : dict
        The 'capture' section from config.yaml.
    """

    def __init__(self, config: dict) -> None:
        self.fps: int = config.get("fps", 10)
        self.output_dir: str = config.get("output_dir", "output/captures")
        self.resolution: str = config.get("resolution", "1920x1080")
        self.display: str = config.get("display", os.environ.get("DISPLAY", ":99"))
        self.quality: int = config.get("quality", 23)  # CRF for FFmpeg
        self.codec: str = config.get("codec", "libx264")
        self.format: str = config.get("format", "mp4")
        self.capture_method: str = config.get("method", "import")  # import | scrot | ffmpeg

        # Internal state
        self._recording = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._frame_dir: Optional[Path] = None
        self._frame_count = 0
        self._start_time: float = 0.0
        self._current_scene: str = "default"
        self._recording_files: list[str] = []

        # Scenes config (compatibility with OBS interface)
        self.scenes: dict = config.get("scenes", {})

    # ------------------------------------------------------------------
    # Context manager (matches OBSController)
    # ------------------------------------------------------------------

    def __enter__(self) -> "FrameCapturer":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Connection (no-op for frame capture, but matches OBS API)
    # ------------------------------------------------------------------

    def connect(self, retries: int = 3, delay: float = 2.0) -> None:
        """Verify capture prerequisites are available."""
        if not os.environ.get("DISPLAY"):
            os.environ["DISPLAY"] = self.display
            logger.warning("DISPLAY not set, using %s", self.display)

        method = self.capture_method
        if method in ("import", "xdotool"):
            if not shutil.which("import"):
                raise RuntimeError(
                    "ImageMagick 'import' not found. Install: apt install imagemagick"
                )
        elif method == "scrot":
            if not shutil.which("scrot"):
                raise RuntimeError("scrot not found. Install: apt install scrot")

        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not found. Install: apt install ffmpeg")

        logger.info(
            "FrameCapturer ready (method=%s, fps=%d, display=%s)",
            method, self.fps, self.display,
        )

    def disconnect(self) -> None:
        """Stop any active recording."""
        if self._recording:
            self.stop_recording()
        logger.info("FrameCapturer disconnected.")

    # ------------------------------------------------------------------
    # Recording (matches OBSController API)
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        """Start capturing frames in a background thread."""
        if self._recording:
            logger.warning("Already recording. Call stop_recording() first.")
            return

        self._frame_dir = Path(self.output_dir) / f"frames_{int(time.time())}"
        self._frame_dir.mkdir(parents=True, exist_ok=True)
        self._frame_count = 0
        self._start_time = time.time()

        self._stop_event.clear()
        self._pause_event.clear()
        self._recording = True
        self._paused = False

        self._thread = threading.Thread(
            target=self._capture_loop,
            name="frame-capturer",
            daemon=True,
        )
        self._thread.start()
        logger.info("Recording started -> %s (fps=%d)", self._frame_dir, self.fps)

    def stop_recording(self) -> Optional[str]:
        """
        Stop capturing frames and assemble them into a video file.

        Returns
        -------
        str or None
            Path to the assembled video file.
        """
        if not self._recording:
            logger.warning("Not recording.")
            return None

        self._stop_event.set()
        self._recording = False

        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

        elapsed = time.time() - self._start_time
        logger.info(
            "Recording stopped. %d frames in %.1fs (%.1f effective fps)",
            self._frame_count, elapsed,
            self._frame_count / elapsed if elapsed > 0 else 0,
        )

        if self._frame_count > 0 and self._frame_dir is not None:
            output_path = self._assemble_current_recording()
            if output_path:
                self._recording_files.append(output_path)
            return output_path

        return None

    def pause_recording(self) -> None:
        """Pause frame capture (frames stop being taken)."""
        self._pause_event.set()
        self._paused = True
        logger.info("Recording paused.")

    def resume_recording(self) -> None:
        """Resume frame capture."""
        self._pause_event.clear()
        self._paused = False
        logger.info("Recording resumed.")

    def get_recording_status(self) -> dict:
        """Return current recording status (matches OBS API)."""
        elapsed = time.time() - self._start_time if self._recording else 0
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return {
            "active": self._recording,
            "paused": self._paused,
            "timecode": timecode,
            "bytes": self._frame_count * 500_000,  # rough estimate
            "frames": self._frame_count,
        }

    def wait_for_recording_start(self, timeout: float = 10.0, poll: float = 0.5) -> None:
        """Block until recording is confirmed active."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._recording and self._frame_count > 0:
                logger.info("Recording confirmed active (%d frames).", self._frame_count)
                return
            time.sleep(poll)
        if self._recording:
            logger.info("Recording active (0 frames captured yet).")
        else:
            raise TimeoutError(f"Recording did not start within {timeout}s.")

    # ------------------------------------------------------------------
    # Scene management (no-ops for compatibility with OBS API)
    # ------------------------------------------------------------------

    def switch_scene(self, scene_name: str) -> None:
        """Track current scene (logging only — no OBS scenes in capture mode)."""
        self._current_scene = scene_name
        logger.info("[capture] Scene marker: %s", scene_name)

    def get_current_scene(self) -> str:
        return self._current_scene

    def list_scenes(self) -> list[str]:
        return list(self.scenes.values()) if self.scenes else ["default"]

    # ------------------------------------------------------------------
    # Source visibility (no-op compatibility)
    # ------------------------------------------------------------------

    def set_source_visibility(
        self, scene_name: str, source_name: str, visible: bool
    ) -> None:
        logger.debug(
            "[capture] Source visibility (no-op): %s/%s = %s",
            scene_name, source_name, visible,
        )

    # ------------------------------------------------------------------
    # Screenshot (single frame capture)
    # ------------------------------------------------------------------

    def take_screenshot(
        self,
        source_name: Optional[str] = None,
        file_path: Optional[str] = None,
        width: int = 1920,
        height: int = 1080,
        quality: int = -1,
    ) -> str:
        """Capture a single screenshot of the virtual display."""
        if file_path is None:
            ts = int(time.time())
            file_path = str(Path(self.output_dir) / f"screenshot_{ts}.png")
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        self._capture_frame(file_path)
        logger.info("Screenshot saved: %s", file_path)
        return file_path

    # ------------------------------------------------------------------
    # Diagram overlay (compatibility with OBS API)
    # ------------------------------------------------------------------

    def show_diagram_overlay(self, visible: bool = True) -> None:
        """Log diagram overlay state (in capture mode, diagrams composited in post)."""
        if visible:
            self.switch_scene(self.scenes.get("diagram_overlay", "Diagram Overlay"))
        else:
            self.switch_scene(self.scenes.get("app_scene", "App Fullscreen"))

    def transition_to_app(self) -> None:
        self.switch_scene(self.scenes.get("app_scene", "App Fullscreen"))

    def transition_to_intro(self) -> None:
        self.switch_scene(self.scenes.get("intro_scene", "Intro"))

    def transition_to_outro(self) -> None:
        self.switch_scene(self.scenes.get("outro_scene", "Outro"))

    # ------------------------------------------------------------------
    # Frame capture loop (background thread)
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Background thread: capture frames at self.fps rate."""
        interval = 1.0 / self.fps
        logger.debug("Capture loop started (interval=%.3fs)", interval)

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.1)
                continue

            frame_start = time.time()
            frame_path = self._frame_dir / f"frame_{self._frame_count:06d}.png"
            try:
                self._capture_frame(str(frame_path))
                self._frame_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Frame capture failed: %s", exc)

            elapsed = time.time() - frame_start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                self._stop_event.wait(sleep_time)

        logger.debug("Capture loop ended. Total frames: %d", self._frame_count)

    def _capture_frame(self, output_path: str) -> None:
        """Capture a single frame of the virtual display."""
        method = self.capture_method

        if method in ("import", "xdotool"):
            subprocess.run(
                [
                    "import",
                    "-display", self.display,
                    "-window", "root",
                    "-silent",
                    output_path,
                ],
                check=True,
                capture_output=True,
                timeout=5,
            )
        elif method == "scrot":
            subprocess.run(
                ["scrot", "-o", "-z", output_path],
                check=True,
                capture_output=True,
                timeout=5,
                env={**os.environ, "DISPLAY": self.display},
            )
        elif method == "ffmpeg":
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "x11grab",
                    "-video_size", self.resolution,
                    "-i", self.display,
                    "-frames:v", "1",
                    "-loglevel", "error",
                    output_path,
                ],
                check=True,
                capture_output=True,
                timeout=5,
            )
        else:
            raise ValueError(f"Unknown capture method: {method!r}. Use 'import', 'scrot', or 'ffmpeg'.")

    # ------------------------------------------------------------------
    # FFmpeg assembly
    # ------------------------------------------------------------------

    def _assemble_current_recording(self) -> Optional[str]:
        """Assemble frames from current recording into a video file."""
        if self._frame_dir is None or self._frame_count == 0:
            return None

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self._frame_dir.name.replace("frames_", "")
        output_path = str(output_dir / f"capture_{timestamp}.{self.format}")

        return self.assemble_frames(str(self._frame_dir), output_path, fps=self.fps)

    def assemble_frames(
        self,
        frames_dir: str,
        output_path: str,
        fps: Optional[int] = None,
    ) -> Optional[str]:
        """
        Assemble numbered PNG frames into a video file using FFmpeg.

        Parameters
        ----------
        frames_dir : str
            Directory containing frame_NNNNNN.png files.
        output_path : str
            Output video file path.
        fps : int, optional
            Frame rate (defaults to self.fps).

        Returns
        -------
        str or None
            Path to assembled video, or None on failure.
        """
        if fps is None:
            fps = self.fps

        frames_pattern = str(Path(frames_dir) / "frame_%06d.png")
        frame_count = len(list(Path(frames_dir).glob("frame_*.png")))

        if frame_count == 0:
            logger.warning("No frames found in %s", frames_dir)
            return None

        logger.info(
            "Assembling %d frames -> %s (fps=%d, codec=%s, crf=%d)",
            frame_count, output_path, fps, self.codec, self.quality,
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", frames_pattern,
            "-c:v", self.codec,
            "-crf", str(self.quality),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
            duration = frame_count / fps
            file_size = Path(output_path).stat().st_size / (1024 * 1024)
            logger.info(
                "Video assembled: %s (%.1fs, %.1f MB)",
                output_path, duration, file_size,
            )
            return output_path
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg assembly failed: %s\n%s", exc, exc.stderr)
            return None
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg assembly timed out (300s)")
            return None

    def assemble_with_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> Optional[str]:
        """
        Mux a video file with an audio track.

        Parameters
        ----------
        video_path : str
            Input video (no audio).
        audio_path : str
            Audio file (mp3/wav).
        output_path : str
            Output video with audio.
        """
        logger.info("Muxing audio: %s + %s -> %s", video_path, audio_path, output_path)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
            logger.info("Muxed video saved: %s", output_path)
            return output_path
        except subprocess.CalledProcessError as exc:
            logger.error("Audio mux failed: %s\n%s", exc, exc.stderr)
            return None

    def cleanup_frames(self, frames_dir: Optional[str] = None) -> None:
        """Remove frame directory after successful assembly."""
        target = frames_dir or (str(self._frame_dir) if self._frame_dir else None)
        if target and Path(target).exists():
            shutil.rmtree(target)
            logger.info("Cleaned up frames: %s", target)
