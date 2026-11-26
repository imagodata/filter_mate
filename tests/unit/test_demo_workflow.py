"""Capture failures must block rendering; data inspection must not mutate its input."""
import ast
import bisect
import importlib.util
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def definitions(path, names, namespace=None):
    source = ROOT / 'scripts' / path
    tree = ast.parse(source.read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    scope = namespace if namespace is not None else {}
    exec(compile(ast.Module(selected, []), str(source), 'exec'), scope)
    return scope


@pytest.mark.parametrize('kind', ['exception', 'timeout'])
def test_failed_capture_never_advances_to_the_result(kind):
    calls, failures = [], []

    def step():
        calls.append('step')
        if kind == 'exception':
            raise ValueError('failed filter')
        return True

    step.max_tries = 2
    import traceback
    scope = definitions('site_videos.py', {'run_steps'}, {
        'STEPS': [(0, step), (0, lambda: calls.append('false success'))], 'RUN': {},
        'QTimer': SimpleNamespace(singleShot=lambda delay, callback: callback()),
        'log': lambda text: None, 'capture_failed': failures.append, 'traceback': traceback})
    scope['run_steps']()
    assert len(failures) == 1
    assert 'false success' not in calls


def test_missing_frame_and_failed_status_block_edit(tmp_path):
    (tmp_path / 'frames').mkdir()
    (tmp_path / 'frames/000000.jpg').write_bytes(b'frame')
    (tmp_path / 'capture.log').write_text('stopped: 2 frames', encoding='utf-8')
    meta = {'frames': [0.1, 0.2], 'status': 'complete'}
    path = tmp_path / 'meta.json'
    path.write_text(json.dumps(meta), encoding='utf-8')
    checker = module('demo_take_check')
    assert 'missing frame 1' in checker.check(tmp_path)
    (tmp_path / 'frames/000001.jpg').write_bytes(b'frame')
    assert checker.check(tmp_path) == []
    meta['status'] = 'failed'
    path.write_text(json.dumps(meta), encoding='utf-8')
    assert checker.check(tmp_path)


def test_gpkg_export_is_not_reported_as_an_embedded_project(tmp_path):
    path = tmp_path / 'test.gpkg'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE gpkg_contents(table_name, data_type, srs_id)')
        db.execute('CREATE TABLE "Buildings altitude"(id)')
        db.execute('INSERT INTO "Buildings altitude" VALUES (1)')
        db.execute("INSERT INTO gpkg_contents VALUES ('Buildings altitude', 'features', 4326)")
    before = path.read_bytes()
    result = module('demo_preflight').gpkg_inventory(path)
    assert result['counts'] == {'Buildings altitude': 1}
    assert result['embedded_projects'] == []
    assert before == path.read_bytes()


def test_missing_geopackage_is_not_created_by_inspection(tmp_path):
    path = tmp_path / 'missing.gpkg'
    with pytest.raises(sqlite3.OperationalError):
        module('demo_preflight').gpkg_inventory(path)
    assert not path.exists()


def test_voice_lines_do_not_overlap_after_accelerated_waits():
    scope = definitions('site_video_render.py', {'Clock'}, {'bisect': bisect})
    clock_class = scope['Clock']
    scope = definitions('fm5_clip_render.py', {'hold_for_voice'}, {
        'base': SimpleNamespace(Clock=clock_class), 'FREEZE': 0.001, 'bisect': bisect})
    events = [{'kind': 'say', 't': 0.2, 'key': 'a'}, {'kind': 'speed', 't': 1.0, 'factor': 8},
              {'kind': 'say', 't': 2.0, 'key': 'b'}, {'kind': 'say', 't': 3.0, 'key': 'c'}]
    result = scope['hold_for_voice'](events, {'a': 4, 'b': 3, 'c': 2}, 'ln')
    clock = clock_class(result, 4.0)
    assert clock.out(2.0) - clock.out(0.2) >= 4.34
    assert clock.out(3.0) - clock.out(2.0) >= 3.34


def test_scene_construction_has_no_missing_function_references():
    """A missing callback fails while --code loads, before run_steps can record the failure."""
    tree = ast.parse((ROOT / 'scripts/site_videos.py').read_text(encoding='utf-8'))
    known = set(dir(__builtins__)) | {'__file__'}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            known.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            known.update(n.asname or n.name.split('.')[0] for n in node.names)
        elif isinstance(node, ast.Assign):
            known.update(n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name))

    class ImmediateNames(ast.NodeVisitor):
        def __init__(self):
            self.names = set()

        def visit_Lambda(self, node):
            return  # its body is evaluated during the take

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                self.names.add(node.id)

    scenes = {'LN_FILM', 'SARLAT_OVERVIEW', 'REPORT', 'URUMEA', 'CLIPS'}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) in scenes for t in node.targets):
            visitor = ImmediateNames()
            visitor.visit(node.value)
            assert not visitor.names - known, visitor.names - known
