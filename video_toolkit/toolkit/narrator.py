"""
Narrator — TTS Audio Generation
=================================
Generates narration audio files for each video sequence using either
edge-tts (free, Microsoft voices), ElevenLabs (paid, higher quality),
or F5-TTS (open-source, zero-shot voice cloning).

Usage:
    from toolkit.narrator import Narrator
    narrator = Narrator(config["narration"])
    path = narrator.generate_narration("Welcome to the tutorial!", "output/narration/seq00.mp3")
    duration = narrator.get_narration_duration(path)
"""

from __future__ import annotations

import asyncio
import logging
import os
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
        self.voice: str = config.get("voice", "en-US-GuyNeural")
        self.output_dir = Path(config.get("output_dir", "output/narration"))
        self.speed: str = config.get("speed", "+0%")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # F5-TTS specific config (voice cloning)
        self.f5_ref_audio: Optional[str] = config.get("f5_ref_audio")
        self.f5_ref_text: str = config.get("f5_ref_text", "")
        self.f5_model: str = config.get("f5_model", "F5TTS_v1_Base")
        self.f5_speed: float = config.get("f5_speed", 1.0)
        self.f5_conda_env: str = config.get("f5_conda_env", "f5-tts")
        self.f5_remove_silence: bool = config.get("f5_remove_silence", False)

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
        elif self.engine == "f5-tts":
            return self._generate_f5_tts(text, output_path)
        else:
            raise ValueError(
                f"Unknown TTS engine: {self.engine!r}. "
                "Use 'edge-tts', 'elevenlabs', or 'f5-tts'."
            )

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
            Mapping of sequence_id -> narration text.
            e.g. {"seq00": "Welcome to the tutorial!", ...}
        output_dir : str | Path, optional
            Override for output directory.

        Returns
        -------
        dict
            Mapping of sequence_id -> Path to audio file.
        """
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Path] = {}
        for seq_id, text in script_dict.items():
            output_path = out_dir / f"{seq_id}_narration.mp3"
            logger.info("Generating narration for %s...", seq_id)
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

        return self._ffprobe_duration(audio_path)

    def list_voices(self) -> list[dict]:
        """List available edge-tts voices (requires edge-tts installed)."""
        if self.engine != "edge-tts":
            raise RuntimeError("list_voices() only supports the edge-tts engine.")
        try:
            import edge_tts  # type: ignore
            return asyncio.run(edge_tts.list_voices())
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")

    # ------------------------------------------------------------------
    # Engine implementations
    # ------------------------------------------------------------------

    def _generate_edge_tts(self, text: str, output_path: Path, voice: str) -> Path:
        """Generate audio using Microsoft edge-tts (free)."""
        try:
            import edge_tts  # type: ignore
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=self.speed)
            await communicate.save(str(output_path))

        asyncio.run(_run())
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"edge-tts produced empty/missing file: {output_path}")
        logger.info(
            "edge-tts generated: %s (%.1fs)",
            output_path.name, self.get_narration_duration(output_path),
        )
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
            raise EnvironmentError("ELEVENLABS_API_KEY environment variable not set.")

        audio = generate(text=text, voice=voice, api_key=api_key)
        save(audio, str(output_path))
        logger.info("ElevenLabs generated: %s", output_path.name)
        return output_path

    def _generate_f5_tts(self, text: str, output_path: Path) -> Path:
        """Generate audio using F5-TTS via bridge script in a conda env.

        Calls the ``f5_tts_bridge.py`` script using the Python interpreter
        from the conda environment, avoiding DLL/import conflicts with the
        host Python.

        Requires:
          - A reference audio WAV file (15-30s of the target voice)
          - f5-tts conda environment with f5-tts, torch, torchaudio installed
          - f5_tts_bridge.py in the project root

        See README.md for setup instructions.
        """
        if not self.f5_ref_audio:
            raise ValueError(
                "f5_ref_audio must be set in narration config when using f5-tts engine. "
                "Provide a ~15s reference WAV file for voice cloning."
            )

        ref_audio_path = Path(self.f5_ref_audio).resolve()
        if not ref_audio_path.exists():
            raise FileNotFoundError(f"F5-TTS reference audio not found: {ref_audio_path}")

        # F5-TTS outputs .wav natively
        wav_output = output_path.with_suffix(".wav").resolve()

        # Bridge script path (look next to config/project root)
        bridge_script = output_path.parent.parent.parent / "f5_tts_bridge.py"
        if not bridge_script.exists():
            # Try relative to this toolkit
            bridge_script = Path(__file__).parent.parent / "f5_tts_bridge.py"
        if not bridge_script.exists():
            raise FileNotFoundError(
                f"F5-TTS bridge script not found. Create f5_tts_bridge.py in your project root.\n"
                "See README.md for instructions."
            )

        # Use the conda env's Python directly (avoids 'conda run' issues)
        conda_python = Path.home() / "miniconda3" / "envs" / self.f5_conda_env / "python.exe"
        if not conda_python.exists():
            # Try Linux path
            conda_python = Path.home() / "miniconda3" / "envs" / self.f5_conda_env / "bin" / "python"
        if not conda_python.exists():
            raise RuntimeError(
                f"Conda env Python not found for env '{self.f5_conda_env}'.\n"
                "Create the environment:\n"
                f"  conda create -n {self.f5_conda_env} python=3.11 -y\n"
                f"  conda activate {self.f5_conda_env}\n"
                "  pip install f5-tts torch torchaudio"
            )

        import tempfile
        gen_fd, gen_path = tempfile.mkstemp(suffix="_gen.txt")
        os.close(gen_fd)
        gen_text_file = Path(gen_path)
        ref_fd, ref_path = tempfile.mkstemp(suffix="_ref.txt")
        os.close(ref_fd)
        ref_text_file = Path(ref_path)
        gen_text_file.write_text(text, encoding="utf-8")
        ref_text_file.write_text(self.f5_ref_text, encoding="utf-8")

        cmd = [
            str(conda_python),
            "-X", "utf8",
            str(bridge_script),
            "--model", self.f5_model,
            "--ref_audio", str(ref_audio_path),
            "--ref_text_file", str(ref_text_file),
            "--gen_text_file", str(gen_text_file),
            "--output_file", str(wav_output),
            "--speed", str(self.f5_speed),
        ]
        if self.f5_remove_silence:
            cmd.append("--remove_silence")

        logger.info(
            "F5-TTS generating: %s (conda env: %s)", output_path.name, self.f5_conda_env
        )

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"F5-TTS timed out after 300s for: {output_path.name}")
        finally:
            gen_text_file.unlink(missing_ok=True)
            ref_text_file.unlink(missing_ok=True)

        if result.returncode != 0:
            logger.error("F5-TTS stderr:\n%s", result.stderr)
            raise RuntimeError(
                f"F5-TTS CLI failed (exit {result.returncode}):\n{result.stderr[:500]}"
            )

        if not wav_output.exists() or wav_output.stat().st_size == 0:
            raise RuntimeError(f"F5-TTS produced empty/missing file: {wav_output}")

        if output_path.suffix.lower() == ".mp3":
            self._wav_to_mp3(wav_output, output_path)
            wav_output.unlink(missing_ok=True)
        else:
            output_path = wav_output

        logger.info(
            "F5-TTS generated: %s (%.1fs)",
            output_path.name, self.get_narration_duration(output_path),
        )
        return output_path

    @staticmethod
    def _wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
        """Convert WAV to MP3 using ffmpeg."""
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), "-q:a", "2", str(mp3_path)],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install ffmpeg to convert F5-TTS WAV to MP3, "
                "or set output files to .wav format."
            )

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
                capture_output=True, text=True, check=True,
            )
            import json
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if "duration" in stream:
                    return float(stream["duration"])
        except Exception as exc:  # noqa: BLE001
            logger.error("ffprobe failed: %s", exc)
        return 0.0
