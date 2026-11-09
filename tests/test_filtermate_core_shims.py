# -*- coding: utf-8 -*-
"""The aliasing shims at the former paths of the moved modules, in a package that holds the core.

In QGIS the plugin package (``filter_mate``) holds ``filtermate_core``: a shim
must alias the vendored module, and an import error of the core must surface
as is instead of loading a second, top-level copy of the core (two
``GeometricFilterPort`` classes, the plugin root on ``sys.path``).
"""
import shutil
import subprocess  # nosec B404 - our own interpreter, our own code
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[1]
_SHIM = _ROOT / 'core' / 'filter' / 'sql_quotes.py'


def _package(tmp_path, core_init):
    pkg = tmp_path / 'fmshimtest'
    for sub in ('', 'core', 'core/filter', 'filtermate_core', 'filtermate_core/filter'):
        (pkg / sub).mkdir(parents=True, exist_ok=True)
        (pkg / sub / '__init__.py').write_text('', encoding='utf-8')
    shutil.copyfile(_SHIM, pkg / 'core' / 'filter' / 'sql_quotes.py')
    (pkg / 'filtermate_core' / '__init__.py').write_text(core_init, encoding='utf-8')
    (pkg / 'filtermate_core' / 'filter' / 'sql_quotes.py').write_text('MARK = "vendored"\n', encoding='utf-8')
    return tmp_path


def _run(parent, code):
    return subprocess.run(  # nosec B603
        [sys.executable, '-I', '-c', textwrap.dedent(code), str(parent)],
        capture_output=True, text=True, timeout=60,
    )


_CHECK = '''
    import sys
    sys.path.insert(0, sys.argv[1])
    try:
        import fmshimtest.core.filter.sql_quotes as shim
    except ImportError as e:
        print('ImportError:', e)
    else:
        import fmshimtest.filtermate_core.filter.sql_quotes as vendored
        print('alias' if shim is vendored else 'other', shim.MARK)
    print('top-level core:', any(k.split('.')[0] == 'filtermate_core' for k in sys.modules))
    print('root on path:', any(p.endswith('fmshimtest') for p in sys.path))
'''


def test_aliases_the_vendored_core(tmp_path):
    proc = _run(_package(tmp_path, ''), _CHECK)
    assert proc.stdout.splitlines() == ['alias vendored', 'top-level core: False', 'root on path: False'], proc.stderr


def test_a_broken_core_surfaces_instead_of_a_second_copy(tmp_path):
    proc = _run(_package(tmp_path, 'raise ImportError("boom in the core")\n'), _CHECK)
    assert proc.stdout.splitlines() == [
        'ImportError: boom in the core', 'top-level core: False', 'root on path: False',
    ], proc.stderr
