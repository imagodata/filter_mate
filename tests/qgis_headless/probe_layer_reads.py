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


def _fm_install_layer_reads_probe():
    """Wrap the accessors and the exit of the bench. Everything lives in this function: the bench is run in the
    globals of this script and may define any name of its own (run_gui_smoke.py has a ``PROBE``)."""
    from qgis.core import QgsMapLayer, QgsRasterLayer, QgsVectorLayer
    from qgis.PyQt.QtCore import QCoreApplication, QThread
    threading, collections, sys, os, json, reference, extra = (
        _threading, _collections, _sys, _os, _json, _REFERENCE, _EXTRA)

    main_ident = threading.get_ident()
    main_qthread = QCoreApplication.instance().thread()
    lock = threading.Lock()
    state = {'off_main': collections.Counter(), 'cross': collections.Counter(), 'callers': collections.Counter(),
             'main_on_foreign': collections.Counter(), 'main_callers': collections.Counter(), 'printed': {},
             'step': '(start)'}

    def stack(depth=8):
        frame = sys._getframe(3)
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

    def note(name, layer):
        """A call made off the main thread."""
        try:
            cross = layer.thread() != QThread.currentThread()
        except RuntimeError:  # deleted
            cross = None
        frames = stack()
        with lock:
            state['off_main'][name] += 1
            if cross is not False:
                state['cross'][name] += 1
            key = f"{name} | cross={cross} | " + ' < '.join(frames[:5])
            state['callers'][key] += 1
            if name == 'providerType' and cross is not False:
                seen = state['printed'].get(key, 0)
                state['printed'][key] = seen + 1
                if seen < 2:
                    print(f"   [probe] providerType off its thread (step {state['step']}): " + ' < '.join(frames),
                          flush=True)

    def note_main(name, layer):
        """The main thread reads a layer that lives in another thread. No accessor of the layer here: it would
        add a report of its own."""
        frames = stack()
        with lock:
            state['main_on_foreign'][name] += 1
            key = f"{name} | {type(layer).__name__} | " + ' < '.join(frames[:6])
            state['main_callers'][key] += 1
            seen = state['printed'].get(key, 0)
            state['printed'][key] = seen + 1
            if seen < 2:
                print(f"   [probe] the MAIN thread reads a layer of another thread: {name} (step {state['step']}): "
                      + ' < '.join(frames), flush=True)

    def wrap(name, original):
        def wrapped(self, *args, **kwargs):
            if threading.get_ident() != main_ident:
                note(name, self)
            else:
                try:
                    foreign = self.thread() != main_qthread
                except RuntimeError:
                    foreign = False
                if foreign:
                    note_main(name, self)
            return original(self, *args, **kwargs)
        wrapped.__name__ = name
        return wrapped

    classes = [QgsMapLayer, QgsVectorLayer, QgsRasterLayer]
    try:
        from qgis.core import QgsPointCloudLayer
        classes.append(QgsPointCloudLayer)
    except ImportError:
        pass
    # every original first: a class inherits the accessors its parent defines
    originals = [(cls, name, getattr(cls, name)) for cls in classes for name in reference + extra
                 if hasattr(cls, name)]
    for cls, name, original in originals:
        setattr(cls, name, wrap(name, original))

    real_exit = os._exit

    def leave(code=0):
        with lock:
            report = {
                'reference': list(reference), 'off_main': dict(state['off_main']), 'cross': dict(state['cross']),
                'off_main_reference_total': sum(state['off_main'][name] for name in reference),
                'cross_reference_total': sum(state['cross'][name] for name in reference),
                'callers': state['callers'].most_common(),
                'main_on_foreign': dict(state['main_on_foreign']),
                'main_callers': state['main_callers'].most_common(),
            }
        print('PROBE_JSON ' + json.dumps(report), flush=True)
        real_exit(code)

    os._exit = leave  # the benches leave through os._exit
    return state


_fm_layer_reads_state = _fm_install_layer_reads_probe()
_fm_layer_reads_bench = _os.environ.get('FM_PROBE_BENCH') or _os.path.join(
    _os.environ.get('FM_REPO') or '/src', 'tests', 'qgis_headless', 'run_lifecycle_check.py')
with open(_fm_layer_reads_bench, encoding='utf-8') as _fm_layer_reads_stream:
    exec(compile(_fm_layer_reads_stream.read(), _fm_layer_reads_bench, 'exec'), globals())  # nosec B102 - a bench of this repository

_fm_layer_reads_run_step = globals().get('run_step')
if _fm_layer_reads_run_step is not None and 'STEPS' in globals():
    def run_step(index=0):  # noqa: F811 - the bench looks its run_step up in the globals at each step
        try:
            _fm_layer_reads_state['step'] = STEPS[index].__name__  # noqa: F821 - defined by the bench
        except Exception:  # nosec B110 - the step name is only a label of the printed stacks
            pass
        return _fm_layer_reads_run_step(index)
