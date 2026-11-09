# -*- coding: utf-8 -*-
"""The optional segmentation plugin: integrity of the model files, the numpy upsampling, the real model when present."""
import hashlib
import importlib.util
import io
import os
import pathlib

import pytest

np = pytest.importorskip("numpy")

pytestmark = pytest.mark.unit
ROOT = pathlib.Path(__file__).resolve().parents[3] / "companion" / "filter_mate_segmentation"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"fm_companion_{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


model_files = _load("model_files")
sam_provider = _load("sam_provider")


class _Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class TestDownload:
    def fetch(self, tmp_path, monkeypatch, body, expected, canceled=False):
        monkeypatch.setattr(model_files.urllib.request, 'urlopen', lambda url, timeout: _Reply(body))
        path = tmp_path / 'model.onnx'
        path.write_bytes(b'previous')
        try:
            model_files.download_file('https://example.org/model', str(path), expected, lambda: canceled, lambda _n: None)
        finally:
            assert not (tmp_path / 'model.onnx.part').exists()
        return path

    def test_a_good_file_replaces_the_old_one(self, tmp_path, monkeypatch):
        body = b'weights'
        assert self.fetch(tmp_path, monkeypatch, body, hashlib.sha256(body).hexdigest()).read_bytes() == body

    def test_a_bad_checksum_leaves_the_old_file(self, tmp_path, monkeypatch):
        with pytest.raises(model_files.ChecksumError):
            self.fetch(tmp_path, monkeypatch, b'tampered', 'not the digest')
        assert (tmp_path / 'model.onnx').read_bytes() == b'previous'

    def test_cancel_leaves_the_old_file(self, tmp_path, monkeypatch):
        with pytest.raises(model_files.Canceled):
            self.fetch(tmp_path, monkeypatch, b'weights', 'x', canceled=True)
        assert (tmp_path / 'model.onnx').read_bytes() == b'previous'

    def test_only_https(self, tmp_path):
        with pytest.raises(ValueError):
            model_files.download_file('http://example.org/m', str(tmp_path / 'm'), 'x', lambda: False, lambda _n: None)

    def test_the_url_is_pinned_to_a_revision(self):
        assert model_files.REVISION in model_files.BASE_URL
        assert set(model_files.FILES) == set(model_files.SIZES)


class TestIsInstalled:
    def test_missing_or_truncated_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(model_files, 'SIZES', {'a.onnx': 3})
        assert not model_files.is_installed(str(tmp_path))
        (tmp_path / 'a.onnx').write_bytes(b'ab')
        assert not model_files.is_installed(str(tmp_path))
        (tmp_path / 'a.onnx').write_bytes(b'abc')
        assert model_files.is_installed(str(tmp_path))


class TestUpsample:
    def test_a_constant_stays_constant(self):
        assert (sam_provider.upsample(np.full((4, 4), 2.5), 16) == pytest.approx(2.5))

    def test_size(self):
        assert sam_provider.upsample(np.zeros((256, 256)), 1024).shape == (1024, 1024)

    def test_matches_the_resampling_of_the_benchmark(self):
        pil = pytest.importorskip("PIL.Image")
        grid = np.random.default_rng(0).random((16, 16), dtype=np.float32)
        expected = np.asarray(pil.fromarray(grid, mode='F').resize((64, 64), pil.BILINEAR))
        assert np.abs(sam_provider.upsample(grid, 64) - expected).max() < 0.02


@pytest.mark.skipif(not os.environ.get('FM_SAM_MODELS'), reason='set FM_SAM_MODELS to the folder of the ONNX files')
class TestRealModel:
    def test_a_bright_square_is_found(self):
        pytest.importorskip('onnxruntime')
        provider = sam_provider.SamOnnxProvider(os.environ['FM_SAM_MODELS'])
        rgb = np.full((1024, 1024, 3), 40, dtype=np.uint8)
        rgb[400:640, 300:700] = (235, 220, 200)
        embedding = provider.embed(rgb)
        truth = rgb[:, :, 0] > 100
        for points, labels, box in (([(500.0, 520.0)], [1], None), ([], [], (300.0, 400.0, 700.0, 640.0))):
            mask, score = provider.predict(embedding, points, labels, box)
            assert mask.shape == (1024, 1024) and mask.dtype == bool and 0.0 <= score <= 1.5
            assert np.count_nonzero(mask & truth) / np.count_nonzero(mask | truth) > 0.9
