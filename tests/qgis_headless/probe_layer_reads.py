# -*- coding: utf-8 -*-
"""
Probe: which accessors of a layer are called from a thread the layer does not live in (2026-11-20).

QGIS 4.3 reports them one by one ("providerType ... is run from a different thread than the object lives
in"); in a build with the debug messages a report made on the main thread is a critical message of the bar,
which is how ``run_lifecycle_check.py`` failed on ``qgis/qgis:latest``. This script wraps the accessors of the
layer classes, runs a bench (``FM_PROBE_BENCH``, ``run_lifecycle_check.py`` by default) in the same QGIS and
prints, when the bench exits, one line ``PROBE_JSON {...}``:

- ``off_main`` / ``cross``: calls made off the main thread, per accessor, all of them and those on a layer that
  lives in another thread (a layer the worker made itself lives in the worker's thread: not counted in ``cross``);
- ``main_on_foreign``: calls made on the main thread on a layer that lives in a worker's thread (a layer a task
  made and handed to ``finished()``);
- ``callers``: the Python frames of each call, with their count.

It also prints the first two stacks of each caller of ``providerType`` as they happen. Same command as the
bench it runs, with this file as ``--code``:

    FM_FIXTURES=/tmp/fm dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' qgis --nologo \\
        --noversioncheck --lang en --profiles-path /tmp/profiles --code tests/qgis_headless/probe_layer_reads.py

``python3 tests/qgis_headless/probe_layer_reads.py --report <log> [accessor ...]`` reads the line back: the
totals, then the callers of the accessors named (all of them without a name).
"""
import collections as _collections
import json as _json
import os as _os
import sys as _sys
import threading as _threading

_REFERENCE = ('id', 'name', 'providerType', 'source', 'isValid', 'featureCount', 'fields', 'subsetString', 'crs',
              'dataProvider', 'isSpatial', 'geometryType')
_EXTRA = ('wkbType', 'extent', 'getFeatures', 'sourceCrs', 'storageType', 'primaryKeyAttributes', 'customProperty',
          'setCustomProperty', 'setSubsetString', 'selectedFeatureCount', 'selectedFeatureIds', 'type',
          'dataSourceUri', 'publicSource', 'hasFeatures', 'getFeature', 'sourceName', 'removeSelection',
          'selectByIds', 'selectByExpression', 'reload', 'triggerRepaint', 'updateExtents', 'hasSpatialIndex',
          'bandCount', 'renderer', 'sourceExtent', 'isEditable', 'displayExpression', 'attributeList')


def _report(path, wanted):
    with open(path, encoding='utf-8', errors='replace') as stream:
        line = next((text for text in stream if text.startswith('PROBE_JSON ')), None)
    if line is None:
        print('no PROBE_JSON line in', path)
        return 1
    data = _json.loads(line[len('PROBE_JSON '):])
    reference = data['reference']
    print(f"off the main thread, the {len(reference)} reference accessors: {data['off_main_reference_total']} calls, "
          f"{data['cross_reference_total']} on a layer of another thread")
    print('  all   :', ', '.join(f"{name} {data['off_main'].get(name, 0)}" for name in reference))
    print('  cross :', ', '.join(f"{name} {data['cross'].get(name, 0)}" for name in reference))
    extra = sorted(((name, count) for name, count in data['off_main'].items() if name not in reference),
                   key=lambda item: -item[1])
    print('  others:', ', '.join(f"{name} {count} (cross {data['cross'].get(name, 0)})" for name, count in extra))
    print('main thread on a layer of another thread:', data.get('main_on_foreign') or 'none')
    for key, count in data.get('main_callers', []):
        print(f"  {count:5d}  {key}")
    for key, count in data['callers']:
        if not wanted or key.split(' | ', 1)[0] in wanted:
            print(f"{count:5d}  {key}")
    return 0


if __name__ == '__main__' and '--report' in _sys.argv:
    _arguments = _sys.argv[_sys.argv.index('--report') + 1:]
    _sys.exit(_report(_arguments[0], _arguments[1:]))

from qgis.core import QgsMapLayer as _QgsMapLayer, QgsRasterLayer as _QgsRasterLayer, \
    QgsVectorLayer as _QgsVectorLayer  # noqa: E402 - only in QGIS
from qgis.PyQt.QtCore import QCoreApplication as _QCoreApplication, QThread as _QThread  # noqa: E402

_MAIN_IDENT = _threading.get_ident()
_MAIN_QTHREAD = _QCoreApplication.instance().thread()
PROBE = {'lock': _threading.Lock(), 'off_main': _collections.Counter(), 'cross': _collections.Counter(),
         'callers': _collections.Counter(), 'step': '(start)', 'printed': {},
         'main_on_foreign': _collections.Counter(), 'main_callers': _collections.Counter()}


def _stack(depth=8):
    frame = _sys._getframe(3)
    parts = []
    while frame is not None and len(parts) < depth:
        filename = frame.f_code.co_filename
        if 'probe_layer_reads' in filename or filename.startswith('<'):
            frame = frame.f_back
            continue
        if '/filter_mate/' in filename:
            filename = filename.split('/filter_mate/', 1)[1]
        parts.append(f"{filename}:{frame.f_lineno} {frame.f_code.co_name}")
        frame = frame.f_back
    return parts


def _note(name, layer):
    """A call made off the main thread."""
    try:
        cross = layer.thread() != _QThread.currentThread()
    except RuntimeError:  # deleted
        cross = None
    stack = _stack()
    with PROBE['lock']:
        PROBE['off_main'][name] += 1
        if cross is not False:
            PROBE['cross'][name] += 1
        key = f"{name} | cross={cross} | " + ' < '.join(stack[:5])
        PROBE['callers'][key] += 1
        if name == 'providerType' and cross is not False:
            seen = PROBE['printed'].get(key, 0)
            PROBE['printed'][key] = seen + 1
            if seen < 2:
                print(f"   [probe] providerType off its thread (step {PROBE['step']}): " + ' < '.join(stack),
                      flush=True)


def _note_main(name, layer):
    """The main thread reads a layer that lives in another thread. No accessor of the layer here: it would
    add a report of its own."""
    stack = _stack()
    with PROBE['lock']:
        PROBE['main_on_foreign'][name] += 1
        key = f"{name} | {type(layer).__name__} | " + ' < '.join(stack[:6])
        PROBE['main_callers'][key] += 1
        seen = PROBE['printed'].get(key, 0)
        PROBE['printed'][key] = seen + 1
        if seen < 2:
            print(f"   [probe] the MAIN thread reads a layer of another thread: {name} (step {PROBE['step']}): "
                  + ' < '.join(stack), flush=True)


def _wrap(name, original):
    def wrapped(self, *args, **kwargs):
        if _threading.get_ident() != _MAIN_IDENT:
            _note(name, self)
        else:
            try:
                foreign = self.thread() != _MAIN_QTHREAD
            except RuntimeError:
                foreign = False
            if foreign:
                _note_main(name, self)
        return original(self, *args, **kwargs)
    wrapped.__name__ = name
    return wrapped


_classes = [_QgsMapLayer, _QgsVectorLayer, _QgsRasterLayer]
try:
    from qgis.core import QgsPointCloudLayer as _QgsPointCloudLayer
    _classes.append(_QgsPointCloudLayer)
except ImportError:
    pass
# every original first: a class inherits the accessors its parent defines
_originals = [(cls, name, getattr(cls, name)) for cls in _classes for name in _REFERENCE + _EXTRA
              if hasattr(cls, name)]
for _cls, _name, _original in _originals:
    setattr(_cls, _name, _wrap(_name, _original))

_real_exit = _os._exit


def _exit(code=0):
    with PROBE['lock']:
        report = {
            'reference': list(_REFERENCE), 'off_main': dict(PROBE['off_main']), 'cross': dict(PROBE['cross']),
            'off_main_reference_total': sum(PROBE['off_main'][name] for name in _REFERENCE),
            'cross_reference_total': sum(PROBE['cross'][name] for name in _REFERENCE),
            'callers': PROBE['callers'].most_common(),
            'main_on_foreign': dict(PROBE['main_on_foreign']), 'main_callers': PROBE['main_callers'].most_common(),
        }
    print('PROBE_JSON ' + _json.dumps(report), flush=True)
    _real_exit(code)


_os._exit = _exit  # the benches leave through os._exit
_bench = _os.environ.get('FM_PROBE_BENCH') or _os.path.join(
    _os.environ.get('FM_REPO') or '/src', 'tests', 'qgis_headless', 'run_lifecycle_check.py')
with open(_bench, encoding='utf-8') as _stream:
    exec(compile(_stream.read(), _bench, 'exec'), globals())  # nosec B102 - a bench of this repository

_bench_run_step = globals().get('run_step')
if _bench_run_step is not None and 'STEPS' in globals():
    def run_step(index=0):  # noqa: F811 - the bench looks its run_step up in the globals at each step
        try:
            PROBE['step'] = STEPS[index].__name__  # noqa: F821 - defined by the bench
        except Exception:  # nosec B110 - the step name is only a label of the printed stacks
            pass
        return _bench_run_step(index)
