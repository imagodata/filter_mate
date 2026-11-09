# -*- coding: utf-8 -*-
"""The segmentation model of FilterMate: integrity of its files, the numpy upsampling, the real model when present."""
import hashlib
import importlib.util
import io
import os
import pathlib

import pytest

np = pytest.importorskip("numpy")

pytestmark = pytest.mark.unit
PATH = pathlib.Path(__file__).resolve().parents[4] / "adapters" / "qgis" / "coverage_layers" / "sam_model.py"


def _load():
    """The module alone: it imports no QGIS, so the fakes are not needed."""
    spec = importlib.util.spec_from_file_location("fm_sam_model_alone", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sam_model = _load()


class _Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class TestDownload:
    def fetch(self, tmp_path, monkeypatch, body, expected, canceled=False):
        monkeypatch.setattr(sam_model, 'open_url', lambda url, proxy: _Reply(body))
        path = tmp_path / 'model.onnx'
        path.write_bytes(b'previous')
        try:
            sam_model.download_file('https://example.org/model', str(path), expected, lambda: canceled, lambda _n: None)
        finally:
            assert not list(tmp_path.glob('*.part'))
        return path

    def test_a_good_file_replaces_the_old_one(self, tmp_path, monkeypatch):
        body = b'weights'
        assert self.fetch(tmp_path, monkeypatch, body, hashlib.sha256(body).hexdigest()).read_bytes() == body

    def test_a_bad_checksum_leaves_the_old_file(self, tmp_path, monkeypatch):
        with pytest.raises(sam_model.ChecksumError):
            self.fetch(tmp_path, monkeypatch, b'tampered', 'not the digest')
        assert (tmp_path / 'model.onnx').read_bytes() == b'previous'

    def test_cancel_leaves_the_old_file(self, tmp_path, monkeypatch):
        with pytest.raises(sam_model.Canceled):
            self.fetch(tmp_path, monkeypatch, b'weights', 'x', canceled=True)
        assert (tmp_path / 'model.onnx').read_bytes() == b'previous'

    def test_only_https(self, tmp_path):
        with pytest.raises(ValueError):
            sam_model.download_file('http://example.org/m', str(tmp_path / 'm'), 'x', lambda: False, lambda _n: None)

    def test_the_url_is_pinned_to_a_revision(self):
        assert sam_model.REVISION in sam_model.BASE_URL
        assert set(sam_model.FILES) == set(sam_model.SIZES)
        assert sam_model.total_megabytes() == 62

    def test_download_skips_complete_files_and_reports_progress(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sam_model, 'FILES', {'a.onnx': hashlib.sha256(b'abc').hexdigest(), 'b.onnx': 'db'})
        monkeypatch.setattr(sam_model, 'SIZES', {'a.onnx': 3, 'b.onnx': 1})
        (tmp_path / 'a.onnx').write_bytes(b'abc')
        fetched, progress = [], []

        def fake_download_file(url, path, expected, is_canceled, on_bytes, proxy):
            fetched.append((url, os.path.basename(path), expected))
            on_bytes(1)

        monkeypatch.setattr(sam_model, 'download_file', fake_download_file)
        sam_model.download(str(tmp_path), lambda: False, progress.append)
        assert fetched == [(sam_model.BASE_URL + 'b.onnx', 'b.onnx', 'db')]
        assert progress == [75.0, 100.0]

    def test_a_damaged_file_of_the_right_size_is_fetched_again(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sam_model, 'FILES', {'a.onnx': hashlib.sha256(b'abc').hexdigest()})
        monkeypatch.setattr(sam_model, 'SIZES', {'a.onnx': 3})
        (tmp_path / 'a.onnx').write_bytes(b'xyz')
        fetched = []
        monkeypatch.setattr(sam_model, 'download_file', lambda url, path, *args: fetched.append(os.path.basename(path)))
        sam_model.download(str(tmp_path), lambda: False)
        assert fetched == ['a.onnx']

    def test_two_downloads_do_not_share_their_temporary_file(self, tmp_path, monkeypatch):
        body = b'weights'
        digest = hashlib.sha256(body).hexdigest()
        path = tmp_path / 'model.onnx'
        inner = []

        def reply(url, proxy):
            if not inner:  # a second download starts while the first one is open
                inner.append(True)
                sam_model.download_file('https://example.org/m', str(path), digest, lambda: False, lambda _n: None)
            return _Reply(body)

        monkeypatch.setattr(sam_model, 'open_url', reply)
        sam_model.download_file('https://example.org/m', str(path), digest, lambda: False, lambda _n: None)
        assert path.read_bytes() == body and not list(tmp_path.glob('*.part'))

    def test_the_proxy_of_qgis_is_used(self, monkeypatch):
        handlers, opened = [], []

        class Opener:
            def open(self, request, timeout):
                opened.append((request.full_url, request.get_header('User-agent'), timeout))
                return 'reply'

        def build_opener(*args):
            handlers.extend(args)
            return Opener()

        monkeypatch.setattr(sam_model.urllib.request, 'build_opener', build_opener)
        assert sam_model.open_url('https://example.org/m', 'http://proxy:3128') == 'reply'
        assert handlers[0].proxies['https'] == 'http://proxy:3128'
        assert opened == [('https://example.org/m', sam_model.USER_AGENT, 60.0)]


class TestIsInstalled:
    def test_missing_or_truncated_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sam_model, 'SIZES', {'a.onnx': 3})
        assert not sam_model.is_installed(str(tmp_path))
        (tmp_path / 'a.onnx').write_bytes(b'ab')
        assert not sam_model.is_installed(str(tmp_path))
        (tmp_path / 'a.onnx').write_bytes(b'abc')
        assert sam_model.is_installed(str(tmp_path))

    def test_a_missing_folder_is_not_installed(self, tmp_path):
        assert not sam_model.is_installed(str(tmp_path / 'nowhere'))


class TestRuntime:
    def test_follows_find_spec(self, monkeypatch):
        monkeypatch.setattr(sam_model.importlib.util, 'find_spec', lambda name: object() if name == 'onnxruntime' else None)
        assert sam_model.runtime_available()
        monkeypatch.setattr(sam_model.importlib.util, 'find_spec', lambda name: None)
        assert not sam_model.runtime_available()

    def test_a_broken_lookup_is_no_runtime(self, monkeypatch):
        def fail(name):
            raise ValueError('bad spec')

        monkeypatch.setattr(sam_model.importlib.util, 'find_spec', fail)
        assert not sam_model.runtime_available()


class TestUpsample:
    def test_a_constant_stays_constant(self):
        assert (sam_model.upsample(np.full((4, 4), 2.5), 16) == pytest.approx(2.5))

    def test_size(self):
        assert sam_model.upsample(np.zeros((256, 256)), 1024).shape == (1024, 1024)

    def test_matches_the_resampling_of_the_benchmark(self):
        pil = pytest.importorskip("PIL.Image")
        grid = np.random.default_rng(0).random((16, 16), dtype=np.float32)
        expected = np.asarray(pil.fromarray(grid, mode='F').resize((64, 64), pil.BILINEAR))
        assert np.abs(sam_model.upsample(grid, 64) - expected).max() < 0.02


class TestInstallCommand:
    def test_the_python_of_the_prefix_when_qgis_embeds_it(self, tmp_path, monkeypatch):
        folder = tmp_path / 'QGIS 4'
        folder.mkdir()
        (folder / 'python.exe').write_bytes(b'')
        monkeypatch.setattr(sam_model.sys, 'executable', str(tmp_path / 'qgis-bin.exe'))
        monkeypatch.setattr(sam_model.sys, 'prefix', str(folder))
        monkeypatch.setattr(sam_model.sys, 'base_prefix', str(folder))
        assert sam_model.install_command() == f'"{folder / "python.exe"}" -m pip install onnxruntime'

    def test_nothing_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sam_model.sys, 'executable', '')
        monkeypatch.setattr(sam_model.sys, 'prefix', str(tmp_path))
        monkeypatch.setattr(sam_model.sys, 'base_prefix', str(tmp_path))
        assert sam_model.install_command() == 'python -m pip install onnxruntime'


class TestProvider:
    def test_damaged_files_are_told_as_such(self, tmp_path):
        pytest.importorskip('onnxruntime')
        (tmp_path / 'prompt_encoder_mask_decoder_quantized.onnx').write_bytes(b'garbage')
        with pytest.raises(sam_model.ModelLoadError):
            sam_model.SamOnnxProvider(str(tmp_path)).embed(np.zeros((4, 4, 3), dtype=np.uint8))

    def test_nothing_opens_before_the_first_embedding(self):
        provider = sam_model.SamOnnxProvider('/nowhere', threads=2)
        assert provider.input_size == 1024 and provider._encoder is None and provider._threads == 2


@pytest.mark.skipif(not os.environ.get('FM_SAM_MODELS'), reason='set FM_SAM_MODELS to the folder of the ONNX files')
class TestRealModel:
    def test_a_bright_square_is_found(self):
        pytest.importorskip('onnxruntime')
        provider = sam_model.SamOnnxProvider(os.environ['FM_SAM_MODELS'])
        rgb = np.full((1024, 1024, 3), 40, dtype=np.uint8)
        rgb[400:640, 300:700] = (235, 220, 200)
        embedding = provider.embed(rgb)
        truth = rgb[:, :, 0] > 100
        for points, labels, box in (([(500.0, 520.0)], [1], None), ([], [], (300.0, 400.0, 700.0, 640.0))):
            mask, score = provider.predict(embedding, points, labels, box)
            assert mask.shape == (1024, 1024) and mask.dtype == bool and 0.0 <= score <= 1.5
            assert np.count_nonzero(mask & truth) / np.count_nonzero(mask | truth) > 0.9
