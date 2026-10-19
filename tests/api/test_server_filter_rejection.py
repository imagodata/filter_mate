"""Server-filter refusals are 400 with a reason, distinct from missing layers."""
import pytest

pytest.importorskip('fastapi')

from fastapi.testclient import TestClient
from filtermate_api.accessor import FilterRejected, InMemoryAccessor
from filtermate_api.qgis_accessor import QGISFilterMateAccessor
from filtermate_api.server import create_app


def test_rest_returns_the_actual_filter_rejection():
    class RejectingAccessor(InMemoryAccessor):
        def apply_filter(self, layer_name, expression, source):
            raise FilterRejected('Unsupported part: $area. The previous filter is unchanged.')

    client = TestClient(create_app(accessor=RejectingAccessor()), base_url='http://127.0.0.1:8000')
    result = client.post('/filters/apply', json={'layer_name': 'communes', 'expression': '$area > 1e6'})
    assert result.status_code == 400
    assert 'Unsupported part: $area' in result.json()['detail']
    assert 'unchanged' in result.json()['detail']


def test_strict_qgis_call_keeps_the_paired_reason(monkeypatch):
    from filtermate_api import qgis_accessor as module
    monkeypatch.setattr(module, 'run_on_main_thread', lambda fn, *args, **kwargs: fn(*args, **kwargs))
    monkeypatch.setattr(module, '_unless_busy', lambda fn, *args, **kwargs: fn(*args, **kwargs))

    class PublicAPI:
        def apply_filter(self, **kwargs):
            raise AssertionError('The strict API must be selected')

        def apply_filter_strict(self, **kwargs):
            raise ValueError('Unsupported part: left(nom, 3)')

    accessor = QGISFilterMateAccessor(PublicAPI(), None)
    with pytest.raises(FilterRejected, match='Unsupported part: left'):
        accessor.apply_filter('communes', 'left(nom, 3)', 'test')
    assert accessor._last_error == 'Unsupported part: left(nom, 3)'


@pytest.mark.parametrize('direction', ['undo', 'redo'])
def test_rest_history_failure_is_explicit(direction):
    class RejectingAccessor(InMemoryAccessor):
        def undo_filter(self):
            raise FilterRejected('The server rejected the saved filter. History is unchanged.')

        redo_filter = undo_filter

    client = TestClient(create_app(accessor=RejectingAccessor()), base_url='http://127.0.0.1:8000')
    response = client.post('/filters/' + direction)
    assert response.status_code == 400
    assert 'History is unchanged' in response.json()['detail']
