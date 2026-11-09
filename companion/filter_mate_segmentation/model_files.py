# -*- coding: utf-8 -*-
"""The files of the segmentation model: where they come from, where they go, whether they are intact.

SAM 2.1 hiera tiny, quantized ONNX export of a pinned revision. Nothing is
downloaded unless the user asks for it, and every file is checked against its
SHA-256 before it replaces anything.
"""
import hashlib
import os
import urllib.request
from typing import Callable, Dict, Optional

REPOSITORY = 'onnx-community/sam2.1-hiera-tiny-ONNX'
REVISION = '814a066640debee5a91e70aa401fb8e17e030503'
BASE_URL = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/onnx/'
FILES: Dict[str, str] = {
    'vision_encoder_quantized.onnx': '8800fdd04b9045cb6060ba8962b83c78ce9bb0976da8f030afa073467a888524',
    'vision_encoder_quantized.onnx_data': 'ea1f677596dc82cef0dc317d78135d892f4b26e20a4439f899aa58d84965b324',
    'prompt_encoder_mask_decoder_quantized.onnx': 'a5f31dba5a7f03203dc3a130fdd7766f0fea952eb4aac1f55458549170eb51ff',
    'prompt_encoder_mask_decoder_quantized.onnx_data': 'fdb3179a32388267a944a416c0f992c77a138b69a4bfd94f0bbf7089430d7489',
}
SIZES: Dict[str, int] = {
    'vision_encoder_quantized.onnx': 441167,
    'vision_encoder_quantized.onnx_data': 52573088,
    'prompt_encoder_mask_decoder_quantized.onnx': 290416,
    'prompt_encoder_mask_decoder_quantized.onnx_data': 8662016,
}
CHUNK = 1 << 20


class ChecksumError(ValueError):
    """A downloaded file is not the one expected."""


class Canceled(RuntimeError):
    """The download was canceled."""


def total_size() -> int:
    return sum(SIZES.values())


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


def download_file(url: str, path: str, expected: str, is_canceled: Callable[[], bool], on_bytes: Callable[[int], None]) -> None:
    """Fetch ``url`` over HTTPS into ``path``: replaced only once its SHA-256 matches.

    Raises:
        ValueError: For a URL that is not HTTPS.
        ChecksumError: For a file that is not the expected one.
        Canceled: When ``is_canceled`` turned true.
    """
    if not url.startswith('https://'):
        raise ValueError('the model is only downloaded over HTTPS')
    partial = path + '.part'
    try:
        with urllib.request.urlopen(url, timeout=60) as reply, open(partial, 'wb') as output:  # nosec B310 - HTTPS checked above
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


def download(directory: str, is_canceled: Callable[[], bool], progress: Optional[Callable[[float], None]] = None) -> None:
    """Fetch the missing files of the model into ``directory``."""
    os.makedirs(directory, exist_ok=True)
    total = float(total_size())
    done = [0]

    def on_bytes(count: int) -> None:
        done[0] += count
        if progress is not None:
            progress(min(100.0, 100.0 * done[0] / total))

    for name, expected in FILES.items():
        path = os.path.join(directory, name)
        if os.path.isfile(path) and os.path.getsize(path) == SIZES[name]:
            on_bytes(SIZES[name])
            continue
        download_file(BASE_URL + name, path, expected, is_canceled, on_bytes)
