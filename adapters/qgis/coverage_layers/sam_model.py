# -*- coding: utf-8 -*-
"""The segmentation model of FilterMate: its files and the provider that runs them.

SAM 2.1 hiera tiny (Meta, Apache 2.0), quantized ONNX export of a pinned
revision, run by onnxruntime on the CPU. FilterMate ships neither the model nor
the runtime: onnxruntime is installed once the user agrees (``python_dependencies``),
and the model is downloaded only when the user asks for it, every file checked
against its SHA-256 before it replaces anything. No QGIS import here: pure Python and numpy.
"""
import hashlib
import importlib.util
import os
import sys
import tempfile
import threading
import urllib.request
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import numpy as np

REPOSITORY = 'onnx-community/sam2.1-hiera-tiny-ONNX'
REVISION = '814a066640debee5a91e70aa401fb8e17e030503'  # pragma: allowlist secret
BASE_URL = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/onnx/'
MODEL_FOLDER = 'sam2.1-hiera-tiny-q'
# SHA-256 of each file of the pinned revision (integrity, not secrets).
FILES: Dict[str, str] = {
    'vision_encoder_quantized.onnx': '8800fdd04b9045cb6060ba8962b83c78ce9bb0976da8f030afa073467a888524',  # pragma: allowlist secret
    'vision_encoder_quantized.onnx_data': 'ea1f677596dc82cef0dc317d78135d892f4b26e20a4439f899aa58d84965b324',  # pragma: allowlist secret
    'prompt_encoder_mask_decoder_quantized.onnx': 'a5f31dba5a7f03203dc3a130fdd7766f0fea952eb4aac1f55458549170eb51ff',  # pragma: allowlist secret
    'prompt_encoder_mask_decoder_quantized.onnx_data': 'fdb3179a32388267a944a416c0f992c77a138b69a4bfd94f0bbf7089430d7489',  # pragma: allowlist secret
}
SIZES: Dict[str, int] = {
    'vision_encoder_quantized.onnx': 441167,
    'vision_encoder_quantized.onnx_data': 52573088,
    'prompt_encoder_mask_decoder_quantized.onnx': 290416,
    'prompt_encoder_mask_decoder_quantized.onnx_data': 8662016,
}
CHUNK = 1 << 20
USER_AGENT = 'FilterMate-QGIS-plugin'
RUNTIME_MODULE = 'onnxruntime'
RUNTIME_MEGABYTES = 100  # about, on disk with its dependencies (105 MB measured under Windows, 2026-11-09)

INPUT_SIZE = 1024
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
# Measured on an ortho window (2026-11-09): 1.1 s at 4 threads, 1.8 s at 24. More threads is slower.
MAX_THREADS = 4


class ChecksumError(ValueError):
    """A downloaded file is not the one expected."""


class Canceled(RuntimeError):
    """The download was canceled."""


class ModelLoadError(RuntimeError):
    """onnxruntime refused the model files: downloading them again can repair them."""


# === The runtime ===

def runtime_available() -> bool:
    """onnxruntime can be found by this Python.

    Asked at each raster, on the main thread: the package is only located, importing its native
    library is left to the first encoding, in a worker thread (see :meth:`SamOnnxProvider._open`).
    """
    try:
        return importlib.util.find_spec(RUNTIME_MODULE) is not None
    except (ImportError, ValueError):
        return False


def python_executable() -> str:
    """The Python of QGIS: ``sys.executable`` when it is one, else the interpreter of its prefix.

    QGIS embeds Python, so ``sys.executable`` is often the QGIS binary itself; the Windows
    installer has ``<prefix>/python.exe`` and the macOS bundle ``<prefix>/bin/python3``.
    """
    candidates = [sys.executable] if os.path.basename(sys.executable or '').lower().startswith('python') else []
    for prefix in (sys.prefix, sys.base_prefix):
        candidates += [os.path.join(prefix, 'python.exe'), os.path.join(prefix, 'bin', 'python3'), os.path.join(prefix, 'bin', 'python')]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return 'python'


def install_command() -> str:
    """The pip command to run by hand when the install from the panel failed."""
    python = python_executable()
    quoted = f'"{python}"' if ' ' in python else python
    return f'{quoted} -m pip install {RUNTIME_MODULE}'


# === The files ===

def total_size() -> int:
    return sum(SIZES.values())


def total_megabytes() -> int:
    return int(round(total_size() / 1e6))


def is_installed(directory: str) -> bool:
    """All the files are there, with the expected size (their content was checked when they were written)."""
    for name, size in SIZES.items():
        path = os.path.join(directory, name)
        if not os.path.isfile(path) or os.path.getsize(path) != size:
            return False
    return True


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            digest.update(chunk)
    return digest.hexdigest()


def open_url(url: str, proxy: Optional[str] = None, timeout: float = 60.0) -> Any:
    """The reply to a GET of an HTTPS ``url`` (a context manager with ``read``).

    Args:
        proxy: ``http://[user:password@]host:port``, the proxy QGIS uses; None keeps the one of the system.

    Raises:
        ValueError: For a URL that is not HTTPS.
    """
    if not url.startswith('https://'):
        raise ValueError('the model is only downloaded over HTTPS')
    handlers = [urllib.request.ProxyHandler({'http': proxy, 'https': proxy})] if proxy else []
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    return opener.open(request, timeout=timeout)  # nosec B310 - HTTPS checked above


def download_file(url: str, path: str, expected: str, is_canceled: Callable[[], bool], on_bytes: Callable[[int], None],
                  proxy: Optional[str] = None) -> None:
    """Fetch ``url`` into a file of its own, which replaces ``path`` once its SHA-256 matches.

    Raises:
        ValueError: For a URL that is not HTTPS.
        ChecksumError: For a file that is not the expected one.
        Canceled: When ``is_canceled`` turned true.
    """
    handle, partial = tempfile.mkstemp(prefix=os.path.basename(path) + '.', suffix='.part', dir=os.path.dirname(path) or '.')
    try:
        with os.fdopen(handle, 'wb') as output, open_url(url, proxy) as reply:
            while True:
                if is_canceled():
                    raise Canceled()
                chunk = reply.read(CHUNK)
                if not chunk:
                    break
                output.write(chunk)
                on_bytes(len(chunk))
        if sha256_of(partial) != expected:
            raise ChecksumError(f'{os.path.basename(path)} is not the expected file')
        os.replace(partial, path)
    finally:
        if os.path.exists(partial):
            os.remove(partial)


def download(directory: str, is_canceled: Callable[[], bool], progress: Optional[Callable[[float], None]] = None,
             proxy: Optional[str] = None) -> None:
    """Fetch into ``directory`` the files of the model that are missing or damaged."""
    os.makedirs(directory, exist_ok=True)
    total = float(total_size())
    done = [0]

    def on_bytes(count: int) -> None:
        done[0] += count
        if progress is not None:
            progress(min(100.0, 100.0 * done[0] / total))

    for name, expected in FILES.items():
        path = os.path.join(directory, name)
        if os.path.isfile(path) and os.path.getsize(path) == SIZES[name] and sha256_of(path) == expected:
            on_bytes(SIZES[name])
            continue
        download_file(BASE_URL + name, path, expected, is_canceled, on_bytes, proxy)


# === The provider ===

def upsample(logits: Any, size: int) -> Any:
    """Bilinear enlargement of a square grid (pixel centres aligned, edges clamped), numpy only."""
    grid = np.asarray(logits, dtype=np.float32)
    source = grid.shape[0]
    positions = (np.arange(size, dtype=np.float32) + 0.5) * source / size - 0.5
    low = np.clip(np.floor(positions).astype(int), 0, source - 1)
    high = np.clip(low + 1, 0, source - 1)
    weight = np.clip(positions - low, 0.0, 1.0)
    rows = grid[low] * (1.0 - weight)[:, None] + grid[high] * weight[:, None]
    return rows[:, low] * (1.0 - weight)[None, :] + rows[:, high] * weight[None, :]


class SamOnnxProvider:
    """Encoder and decoder of a quantized SAM 2.1 export (see ``core/ports/segmentation_port.py``)."""

    input_size = INPUT_SIZE

    def __init__(self, directory: str, threads: Optional[int] = None) -> None:
        """Nothing is loaded here: the models open at the first :meth:`embed`, in the worker thread."""
        self._directory = directory
        self._threads = threads or min(MAX_THREADS, os.cpu_count() or 1)
        self._lock = threading.Lock()
        self._encoder: Any = None
        self._decoder: Any = None

    def _open(self) -> None:
        """Open the two models, once (tried again at the next call after a failure).

        Raises:
            RuntimeError: When onnxruntime cannot be imported (its native library does not load).
            ModelLoadError: When onnxruntime refuses the files.
        """
        with self._lock:
            if self._encoder is not None:
                return
            try:
                import onnxruntime
            except Exception as exc:  # ImportError, or the OSError of a library that does not load
                raise RuntimeError(f'onnxruntime is installed but cannot be loaded: {exc}') from exc
            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = self._threads
            options.inter_op_num_threads = 1
            providers = ['CPUExecutionProvider']
            try:
                decoder = onnxruntime.InferenceSession(
                    os.path.join(self._directory, 'prompt_encoder_mask_decoder_quantized.onnx'), options, providers=providers)
                self._encoder = onnxruntime.InferenceSession(
                    os.path.join(self._directory, 'vision_encoder_quantized.onnx'), options, providers=providers)
            except Exception as exc:  # onnxruntime has its own exception types
                raise ModelLoadError(f'the model files cannot be read: {exc}') from exc
            self._decoder = decoder

    def embed(self, rgb: Any) -> Any:
        self._open()
        pixels = (np.asarray(rgb, dtype=np.float32) / 255.0 - MEAN) / STD
        outputs = self._encoder.run(None, {'pixel_values': pixels.transpose(2, 0, 1)[None]})
        return {f'image_embeddings.{index}': value for index, value in enumerate(outputs)}

    def predict(self, embedding: Any, points: Sequence[Tuple[float, float]], labels: Sequence[int],
                box: Optional[Tuple[float, float, float, float]]) -> Tuple[Any, float]:
        coordinates = [[float(x), float(y)] for x, y in points]
        kinds = [int(label) for label in labels]
        feeds = dict(embedding)
        feeds['input_points'] = (np.array([[coordinates]], dtype=np.float32) if coordinates
                                 else np.zeros((1, 1, 0, 2), dtype=np.float32))
        feeds['input_labels'] = (np.array([[kinds]], dtype=np.int64) if kinds
                                 else np.zeros((1, 1, 0), dtype=np.int64))
        feeds['input_boxes'] = (np.array([[box]], dtype=np.float32) if box is not None
                                else np.zeros((1, 0, 4), dtype=np.float32))
        scores, masks = self._decoder.run(['iou_scores', 'pred_masks'], feeds)
        best = int(np.argmax(scores[0, 0]))
        return upsample(masks[0, 0, best], self.input_size) > 0, float(scores[0, 0, best])
