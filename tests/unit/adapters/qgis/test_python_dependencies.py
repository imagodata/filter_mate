# -*- coding: utf-8 -*-
"""The Python packages FilterMate installs for itself once the user agreed."""
import importlib.util
import pathlib
import sys
import types

import pytest

pytestmark = pytest.mark.unit


def _fakes():
    if "fm_coverage_fakes" not in sys.modules:
        spec = importlib.util.spec_from_file_location("fm_coverage_fakes", pathlib.Path(__file__).with_name("coverage_fakes.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["fm_coverage_fakes"] = module
        spec.loader.exec_module(module)
    return sys.modules["fm_coverage_fakes"]


fk = _fakes()
deps = fk.load("adapters.qgis.python_dependencies")
fk.load("sam_model")  # loaded here, while qgis.core is the shared fake: a fixture replaces it later
fk.load("segmentation")
ROOT = pathlib.Path(__file__).resolve().parents[4]


@pytest.fixture(autouse=True)
def no_task(monkeypatch):
    monkeypatch.setattr(deps, '_task', None)
    monkeypatch.setattr(deps, '_failed', False)
    monkeypatch.setattr(deps, '_listeners', [])


class TestDeclared:
    def test_the_real_metadata_declares_the_runtime(self):
        assert deps.declared_packages(str(ROOT / 'metadata.txt')) == ['onnxruntime']

    def test_the_default_path_is_the_metadata_of_the_plugin(self):
        assert deps.declared_packages() == ['onnxruntime']

    def test_several_and_none(self, tmp_path):
        path = tmp_path / 'metadata.txt'
        path.write_text('[general]\nname=x\npython_dependencies= a, b ,\n', encoding='utf-8')
        assert deps.declared_packages(str(path)) == ['a', 'b']
        path.write_text('[general]\nname=x\n# python_dependencies=a\n', encoding='utf-8')
        assert deps.declared_packages(str(path)) == []

    def test_it_is_not_declared_as_a_qgis_plugin(self):
        lines = (ROOT / 'metadata.txt').read_text(encoding='utf-8').splitlines()
        assert not [line for line in lines if line.startswith('plugin_dependencies=')]


class TestActivate:
    def test_after_the_packages_of_qgis_and_only_once(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, 'path', ['/qgis/site-packages'])
        folder = str(tmp_path / 'py312')
        deps.activate(folder)
        deps.activate(folder)
        assert sys.path == ['/qgis/site-packages', folder] and pathlib.Path(folder).is_dir()

    def test_a_package_installed_there_is_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, 'path', list(sys.path))
        assert deps.missing_packages(['fm_probe_pkg']) == ['fm_probe_pkg']
        deps.activate(str(tmp_path))
        (tmp_path / 'fm_probe_pkg.py').write_text('', encoding='utf-8')
        importlib.invalidate_caches()
        assert deps.missing_packages(['fm_probe_pkg']) == []


class TestActivateInstalled:
    def test_an_earlier_install_is_importable_and_nothing_starts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, 'path', ['/qgis/site-packages'])
        monkeypatch.setattr(deps, 'target_directory', lambda: str(tmp_path))
        deps.activate_installed()
        assert sys.path == ['/qgis/site-packages', str(tmp_path)] and not deps.installing()

    def test_no_folder_is_created_for_who_never_installed(self, tmp_path, monkeypatch):
        folder = tmp_path / 'py312'
        monkeypatch.setattr(sys, 'path', ['/qgis/site-packages'])
        monkeypatch.setattr(deps, 'target_directory', lambda: str(folder))
        deps.activate_installed()
        assert sys.path == ['/qgis/site-packages'] and not folder.exists()

    def test_nothing_raises_at_launch(self, monkeypatch):
        def fail():
            raise OSError('no profile')

        monkeypatch.setattr(deps, 'target_directory', fail)
        deps.activate_installed()


class TestCommand:
    def test_into_the_folder_without_compiling(self):
        command = deps.pip_command('/q/python', '/profile/py312', ['onnxruntime'])
        assert command[:6] == ['/q/python', '-m', 'pip', 'install', '--target', '/profile/py312']
        assert '--only-binary=:all:' in command and command[-1] == 'onnxruntime'


def _task_for(code, callback=None, proxy=None):
    return deps.PipInstallTask([sys.executable, '-c', code], ['pkg'], callback or (lambda t, ok: None), proxy)


class TestTask:
    def test_success(self):
        assert _task_for('pass').run() is True

    def test_the_output_of_a_failure_is_kept(self):
        task = _task_for('import sys; print("no matching distribution"); sys.exit(1)')
        assert task.run() is False and 'no matching distribution' in task.error

    def test_a_missing_python_is_told(self):
        task = deps.PipInstallTask(['/no/such/python'], ['pkg'], lambda t, ok: None)
        assert task.run() is False and task.error

    def test_cancel_stops_pip(self, monkeypatch):
        task = _task_for('import time; time.sleep(30)')
        monkeypatch.setattr(deps, 'POLL_SECONDS', 0.01)
        task.cancel()
        assert task.run() is False and task.error == ''

    def test_the_proxy_goes_through_the_environment(self, tmp_path):
        out = tmp_path / 'proxy.txt'
        code = f"import os; open({str(out)!r}, 'w').write(os.environ['HTTPS_PROXY'])"
        task = _task_for(code, proxy='http://u:p@proxy:3128')
        assert task.run() is True and out.read_text() == 'http://u:p@proxy:3128'
        assert 'proxy:3128' not in ' '.join(task.command)

    def test_finished_clears_the_state_and_tells_the_listeners(self, monkeypatch):
        heard, called = [], []
        task = _task_for('pass', lambda t, ok: called.append(ok))
        monkeypatch.setattr(deps, '_task', task)
        assert deps.installing()
        deps.notify_when_done(lambda: heard.append(deps.installing()))
        task.finished(True)
        assert called == [True] and heard == [False] and not deps.installing()

    def test_a_failing_callback_does_not_stop_the_listeners(self, monkeypatch):
        heard = []

        def fail(_task, _ok):
            raise AttributeError('_torn_down')

        task = _task_for('pass', fail)
        monkeypatch.setattr(deps, '_task', task)
        deps.notify_when_done(lambda: heard.append(True))
        task.finished(True)
        assert heard == [True] and not deps.installing()

    def test_no_listener_without_an_install(self):
        deps.notify_when_done(lambda: None)
        assert deps._listeners == []


class TestInstallMissing:
    @pytest.fixture
    def launch(self, monkeypatch, tmp_path):
        python = tmp_path / 'python'
        python.write_bytes(b'')
        added = []
        monkeypatch.setattr(deps, 'target_directory', lambda: str(tmp_path / 'py312'))
        monkeypatch.setattr(deps, 'declared_packages', lambda: ['onnxruntime'])
        monkeypatch.setattr(sys, 'path', list(sys.path))
        monkeypatch.setitem(sys.modules, 'qgis.core', types.SimpleNamespace(
            QgsApplication=types.SimpleNamespace(taskManager=lambda: types.SimpleNamespace(addTask=added.append))))
        sam_model = fk.load("sam_model")
        segmentation = fk.load("segmentation")
        monkeypatch.setattr(sam_model, 'python_executable', lambda: str(python))
        monkeypatch.setattr(segmentation, 'qgis_proxy_url', lambda: None)
        return added

    def test_a_present_package_starts_nothing(self, launch, monkeypatch):
        monkeypatch.setattr(deps, 'is_available', lambda name: True)
        deps.install_missing()
        assert launch == [] and not deps.installing()

    def test_a_missing_package_starts_one_task(self, launch, monkeypatch):
        monkeypatch.setattr(deps, 'is_available', lambda name: False)
        deps.install_missing()
        deps.install_missing()
        assert len(launch) == 1 and deps.installing() and launch[0].command[-1] == 'onnxruntime'

    def test_a_failure_is_remembered_and_a_retry_clears_it(self, launch, monkeypatch):
        monkeypatch.setattr(deps, 'is_available', lambda name: False)
        deps.install_missing()
        launch[0].error = 'no network'
        launch[0].finished(False)
        assert deps.install_failed()
        deps.install_missing()
        assert not deps.install_failed() and len(launch) == 2

    def test_a_cancel_is_no_failure(self, launch, monkeypatch):
        monkeypatch.setattr(deps, 'is_available', lambda name: False)
        deps.install_missing()
        launch[0].finished(False)
        assert not deps.install_failed()

    def test_success_is_told(self, launch, monkeypatch):
        monkeypatch.setattr(deps, 'is_available', lambda name: False)
        told = []
        deps.install_missing(told.append)
        launch[0].finished(True)
        assert told == [['onnxruntime']]

    def test_without_a_python_nothing_starts(self, launch, monkeypatch):
        sam_model = fk.load("sam_model")
        monkeypatch.setattr(deps, 'is_available', lambda name: False)
        monkeypatch.setattr(sam_model, 'python_executable', lambda: 'python')
        deps.install_missing()
        assert launch == [] and not deps.installing() and deps.install_failed()

    def test_nothing_raises(self, monkeypatch):
        def fail():
            raise OSError('read only')

        monkeypatch.setattr(deps, 'target_directory', fail)
        deps.install_missing()
        assert deps.install_failed()

    def test_unload_cancels_and_hears_nothing(self, launch, monkeypatch):
        monkeypatch.setattr(deps, 'is_available', lambda name: False)
        told = []
        deps.install_missing(told.append)
        task = launch[0]
        deps.cancel()
        assert task.isCanceled() and not deps.installing() and task.callback is None
