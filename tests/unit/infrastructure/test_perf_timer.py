# -*- coding: utf-8 -*-
"""Named wall-clock spans logged at INFO (audit of 2026-09-12)."""

import logging

import pytest

from infrastructure import perf_timer


@pytest.fixture(autouse=True)
def _clean_marks():
    with perf_timer._lock:
        perf_timer._marks.clear()
    yield
    with perf_timer._lock:
        perf_timer._marks.clear()


@pytest.mark.unit
class TestPerfMarks:

    def test_start_end_logs_once_at_info(self, caplog):
        with caplog.at_level(logging.INFO, logger='FilterMate.Perf'):
            perf_timer.perf_mark_start('project_open')
            elapsed = perf_timer.perf_mark_end('project_open', '3 layers')

        assert elapsed is not None and elapsed >= 0
        messages = [r.getMessage() for r in caplog.records if r.name == 'FilterMate.Perf']
        assert len(messages) == 1
        assert messages[0].startswith('⏱ project_open: ')
        assert messages[0].endswith(' ms (3 layers)')

    def test_end_without_start_is_silent(self, caplog):
        with caplog.at_level(logging.DEBUG, logger='FilterMate.Perf'):
            assert perf_timer.perf_mark_end('never_started') is None
        assert not [r for r in caplog.records if r.name == 'FilterMate.Perf']

    def test_restart_resets_origin(self):
        perf_timer.perf_mark_start('x')
        first = perf_timer.perf_elapsed_ms('x')
        perf_timer.perf_mark_start('x')
        second = perf_timer.perf_elapsed_ms('x')
        assert first is not None and second is not None
        assert second <= first + 1.0  # restarted, not accumulated

    def test_elapsed_and_cancel(self):
        assert perf_timer.perf_elapsed_ms('y') is None
        perf_timer.perf_mark_start('y')
        assert perf_timer.perf_elapsed_ms('y') is not None
        perf_timer.perf_mark_cancel('y')
        assert perf_timer.perf_elapsed_ms('y') is None
        assert perf_timer.perf_mark_end('y') is None

    def test_span_context_manager(self, caplog):
        with caplog.at_level(logging.INFO, logger='FilterMate.Perf'):
            with perf_timer.perf_span('layer_change', 'batiment') as span:
                pass
        assert span.elapsed_ms is not None
        assert any('⏱ layer_change:' in r.getMessage() for r in caplog.records)

    def test_span_cancelled_on_exception(self, caplog):
        with caplog.at_level(logging.INFO, logger='FilterMate.Perf'):
            with pytest.raises(RuntimeError):
                with perf_timer.perf_span('boom'):
                    raise RuntimeError("x")
        assert not any('⏱ boom' in r.getMessage() for r in caplog.records)
        assert perf_timer.perf_elapsed_ms('boom') is None
