"""
Narrator — TTS Audio Generation
=================================
Generates narration audio files for each video sequence using either
edge-tts (free, Microsoft voices), ElevenLabs (paid, higher quality),
or F5-TTS (open-source, zero-shot voice cloning).

Usage:
    from core.narrator import Narrator
    narrator = Narrator(config["narration"])
    path = narrator.generate_narration("Votre texte ici", "output/narration/seq00.mp3")
    duration = narrator.get_narration_duration(path)
"""

from __future__ import annotations

import asyncio
import logging
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
        self.voice: str = config.get("voice", "fr-FR-HenriNeural")
        self.output_dir = Path(config.get("output_dir", "output/narration"))
        self.speed: str = config.get("speed", "+0%")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # F5-TTS specific config
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
            raise ValueError(f"Unknown TTS engine: {self.engine}. Use 'edge-tts', 'elevenlabs', or 'f5-tts'.")

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
            Mapping of sequence_id → narration text.
            e.g. {"seq00": "Vous avez 1 million de bâtiments...", ...}
        output_dir : str | Path, optional
            Override for output directory.

        Returns
        -------
        dict
            Mapping of sequence_id → Path to audio file.
        """
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Path] = {}
        for seq_id, text in script_dict.items():
            output_path = out_dir / f"{seq_id}_narration.mp3"
            logger.info("Generating narration for %s…", seq_id)
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

        # Fallback: ffprobe
        return self._ffprobe_duration(audio_path)

    def list_voices(self) -> list[dict]:
        """List available edge-tts voices (requires edge-tts installed)."""
        if self.engine != "edge-tts":
            raise RuntimeError("list_voices() only supports edge-tts engine.")
        try:
            import edge_tts  # type: ignore

            voices = asyncio.run(edge_tts.list_voices())
            return voices
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")

    # ------------------------------------------------------------------
    # Engine implementations
    # ------------------------------------------------------------------

    def _generate_edge_tts(self, text: str, output_path: Path, voice: str) -> Path:
        """Generate audio using Microsoft edge-tts."""
        try:
            import edge_tts  # type: ignore
        except ImportError:
            raise ImportError(
                "edge-tts not installed. Run: pip install edge-tts"
            )

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=self.speed)
            await communicate.save(str(output_path))

        asyncio.run(_run())
        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error("edge-tts produced empty file: %s", output_path.name)
            raise RuntimeError(f"edge-tts produced empty/missing file: {output_path}")
        logger.info("edge-tts generated: %s (%.1fs)", output_path.name,
                    self.get_narration_duration(output_path))
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
            raise EnvironmentError(
                "ELEVENLABS_API_KEY environment variable not set."
            )

        audio = generate(text=text, voice=voice, api_key=api_key)
        save(audio, str(output_path))
        logger.info("ElevenLabs generated: %s", output_path.name)
        return output_path

    def _generate_f5_tts(self, text: str, output_path: Path) -> Path:
        """Generate audio using F5-TTS CLI via conda subprocess.

        Calls ``conda run -n <env> f5-tts_infer-cli …`` so that f5-tts
        runs in its own Python 3.11 conda environment, avoiding
        incompatibilities with the host Python (e.g. 3.14).
        """
        if not self.f5_ref_audio:
            raise ValueError(
                "f5_ref_audio must be set in narration config when using f5-tts engine. "
                "Provide a ~15s reference audio WAV file for voice cloning."
            )

        ref_audio_path = Path(self.f5_ref_audio).resolve()
        if not ref_audio_path.exists():
            raise FileNotFoundError(f"F5-TTS reference audio not found: {ref_audio_path}")

        # F5-TTS CLI writes to output_dir/output_file (default: infer_cli_out.wav)
        out_dir = output_path.parent.resolve()
        wav_filename = output_path.stem + ".wav"

        cmd = [
            "conda", "run", "--no-banner", "-n", self.f5_conda_env,
            "f5-tts_infer-cli",
            "--model", self.f5_model,
            "--ref_audio", str(ref_audio_path),
            "--ref_text", self.f5_ref_text,
            "--gen_text", text,
            "--output_dir", str(out_dir),
            "--output_file", wav_filename,
            "--speed", str(self.f5_speed),
        ]
        if self.f5_remove_silence:
            cmd.append("--remove_silence")

        logger.info("F5-TTS generating: %s (conda env: %s)", output_path.name, self.f5_conda_env)
        logger.debug("F5-TTS command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min max per segment
            )
        except FileNotFoundError:
            raise RuntimeError(
                "conda not found on PATH. Install Miniconda/Anaconda and create "
                f"the '{self.f5_conda_env}' environment:\n"
                f"  conda create -n {self.f5_conda_env} python=3.11 -y\n"
                f"  conda activate {self.f5_conda_env}\n"
                "  pip install f5-tts torch torchaudio"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"F5-TTS timed out after 300s for: {output_path.name}")

        if result.returncode != 0:
            logger.error("F5-TTS stderr:\n%s", result.stderr)
            raise RuntimeError(
                f"F5-TTS CLI failed (exit {result.returncode}):\n{result.stderr[:500]}"
            )

        wav_output = out_dir / wav_filename
        if not wav_output.exists() or wav_output.stat().st_size == 0:
            raise RuntimeError(f"F5-TTS produced empty/missing file: {wav_output}")

        # Convert to mp3 if the caller requested .mp3
        if output_path.suffix.lower() == ".mp3":
            self._wav_to_mp3(wav_output, output_path)
            wav_output.unlink(missing_ok=True)
        else:
            output_path = wav_output

        logger.info("F5-TTS generated: %s (%.1fs)", output_path.name,
                    self.get_narration_duration(output_path))
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
                "ffmpeg not found. Install ffmpeg to convert F5-TTS WAV output to MP3, "
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
                capture_output=True,
                text=True,
                check=True,
            )
            import json
            data = json.loads(result.stdout)
            for stream in data.get("streams", []):
                if "duration" in stream:
                    return float(stream["duration"])
        except Exception as exc:  # noqa: BLE001
            logger.error("ffprobe failed: %s", exc)
        return 0.0


# ---------------------------------------------------------------------------
# Narration texts — loaded from narrations.yaml
# ---------------------------------------------------------------------------
_NARRATIONS_YAML = Path(__file__).parent.parent / "narrations.yaml"
_narration_cache: dict[str, dict[str, str]] = {}


def _load_narrations_yaml() -> dict[str, dict[str, str]]:
    """Load narrations.yaml and cache the result."""
    if _narration_cache:
        return _narration_cache
    import yaml
    if not _NARRATIONS_YAML.exists():
        logger.warning("narrations.yaml not found at %s", _NARRATIONS_YAML)
        return {"original": {}, "v01": {}}
    with open(_NARRATIONS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _narration_cache.update(data)
    return _narration_cache


def get_narration_texts(video: str | None = None) -> dict[str, str]:
    """Return the narration texts dict for the given video script.

    Parameters
    ----------
    video : str or None
        Video identifier (e.g. "v01"). None returns original texts.
    """
    data = _load_narrations_yaml()
    if video and video in data:
        return data[video]
    return data.get("original", {})
