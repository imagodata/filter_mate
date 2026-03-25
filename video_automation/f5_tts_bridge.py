"""
F5-TTS bridge script — runs inside the f5-tts conda env.

Called as:
    python f5_tts_bridge.py --ref_audio REF.wav --ref_text "..." \
        --gen_text "..." --output_file OUT.wav [--speed 1.0] [--model F5TTS_v1_Base] \
        [--remove_silence]

This avoids importing the full infer_cli module (which has heavy
module-level imports that can crash on some Windows setups) and uses
the Python API directly.
"""

import os
import sys
import types

# ---------------------------------------------------------------------------
# Pre-import mocks for modules that are NOT needed for F5-TTS inference
# but whose C-extensions crash on some Windows 11 setups (DLL policy / GIL).
# ---------------------------------------------------------------------------

def _make_mock(name, attrs=()):
    """Create a stub module with no-op callables and a valid __spec__."""
    mod = types.ModuleType(name)
    # torch._dynamo.trace_rules checks __spec__ via importlib.util.find_spec
    from importlib.machinery import ModuleSpec
    mod.__spec__ = ModuleSpec(name, None)
    for a in attrs:
        setattr(mod, a, lambda *_a, **_kw: None)
    return mod

# matplotlib — used only for spectrogram visualization
_noop_attrs = ["figure", "show", "savefig", "plot", "subplot", "close",
               "clf", "title", "xlabel", "ylabel", "use"]
_mpl = _make_mock("matplotlib", _noop_attrs)
_mpl.__path__ = []  # make it look like a package
sys.modules["matplotlib"] = _mpl
sys.modules["matplotlib.pylab"] = _make_mock("matplotlib.pylab", _noop_attrs)
sys.modules["matplotlib.pyplot"] = _make_mock("matplotlib.pyplot", _noop_attrs)

# sklearn / scipy.sparse — pulled in by transformers but not used for TTS inference.
# On Windows, scipy/sklearn compiled DLLs can be incompatible with numpy versions.
for _mod_name in (
    "sklearn", "sklearn.base", "sklearn.utils", "sklearn.utils._chunking",
    "sklearn.utils._param_validation", "sklearn.utils.validation",
    "sklearn.utils._array_api", "sklearn.utils.fixes",
    "sklearn.utils._metadata_requests", "sklearn.utils._estimator_html_repr",
    "sklearn.metrics", "sklearn.metrics._ranking",
):
    sys.modules[_mod_name] = _make_mock(_mod_name)

# Also mock sklearn.metrics.roc_curve since transformers imports it directly
_mock_metrics = sys.modules["sklearn.metrics"]
_mock_metrics.roc_curve = lambda *a, **kw: ([], [], [])

# ---------------------------------------------------------------------------

# Patch torchaudio to use soundfile backend instead of torchcodec
# (torchcodec requires ffmpeg DLLs which are problematic on Windows)
import torchaudio
import soundfile as sf
import torch

def _load_soundfile(filepath, **kwargs):
    """Load audio using soundfile as fallback for torchaudio.load."""
    data, samplerate = sf.read(filepath, dtype="float32")
    # soundfile returns (samples, channels), torch wants (channels, samples)
    tensor = torch.from_numpy(data)
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    else:
        tensor = tensor.T
    return tensor, samplerate

torchaudio.load = _load_soundfile

import argparse


def main():
    parser = argparse.ArgumentParser(description="F5-TTS bridge for narration generation")
    parser.add_argument("--ref_audio", required=True, help="Path to reference audio WAV")
    parser.add_argument("--ref_text", default="", help="Transcription of reference audio")
    parser.add_argument("--gen_text", default="", help="Text to synthesize")
    parser.add_argument("--gen_text_file", default="", help="UTF-8 text file with text to synthesize (overrides --gen_text)")
    parser.add_argument("--ref_text_file", default="", help="UTF-8 text file with ref transcription (overrides --ref_text)")
    parser.add_argument("--output_file", required=True, help="Output WAV path")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
    parser.add_argument("--model", default="F5TTS_v1_Base", help="Model type")
    parser.add_argument("--remove_silence", action="store_true", help="Remove silence")
    args = parser.parse_args()

    # Read text from files if provided (avoids Windows CLI encoding issues)
    gen_text = args.gen_text
    if args.gen_text_file and os.path.exists(args.gen_text_file):
        with open(args.gen_text_file, encoding="utf-8") as f:
            gen_text = f.read().strip()

    ref_text = args.ref_text
    if args.ref_text_file and os.path.exists(args.ref_text_file):
        with open(args.ref_text_file, encoding="utf-8") as f:
            ref_text = f.read().strip()

    if not gen_text:
        print("ERROR: no gen_text provided (use --gen_text or --gen_text_file)", file=sys.stderr)
        sys.exit(1)

    from f5_tts.api import F5TTS

    print(f"Loading F5-TTS model: {args.model}", flush=True)
    tts = F5TTS(model=args.model)

    print(f"Generating: {os.path.basename(args.output_file)}", flush=True)
    wav, sr, spec = tts.infer(
        ref_file=args.ref_audio,
        ref_text=ref_text,
        gen_text=gen_text,
        file_wave=args.output_file,
        speed=args.speed,
    )

    if args.remove_silence and os.path.exists(args.output_file):
        try:
            from f5_tts.infer.utils_infer import remove_silence_for_generated_wav
            remove_silence_for_generated_wav(args.output_file)
            print("Silence removed.", flush=True)
        except Exception as e:
            print(f"Warning: could not remove silence: {e}", file=sys.stderr)

    if os.path.exists(args.output_file):
        size = os.path.getsize(args.output_file)
        print(f"OK: {args.output_file} ({size} bytes)", flush=True)
    else:
        print("ERROR: output file not created", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
