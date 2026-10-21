"""Internal task diagnostics are classified before REST serializes a report."""
from types import SimpleNamespace
import json

import pytest

from filtermate_api import qgis_accessor
from fastapi.encoders import jsonable_encoder


@pytest.mark.parametrize('surface', ['cross', 'operation'])
def test_internal_source_and_target_errors_are_private(surface):
    report = SimpleNamespace(error='/private/profile/cache/capture.tif failed',
                             failed={'target': 'SELECT * FROM private_table failed'},
                             details={'internal_error': True, 'internal_failures': ['target']},
                             done_names=[], skipped={}, outputs={})
    mapper = (qgis_accessor.QGISFilterMateAccessor._cross_result if surface == 'cross'
              else qgis_accessor.QGISFilterMateAccessor._operation_result)
    result = mapper(report)
    assert result.error == qgis_accessor.INTERNAL_ERROR
    assert result.failed == {'target': qgis_accessor.INTERNAL_ERROR}
    serialized = json.dumps(jsonable_encoder(result))
    assert '/private/' not in serialized and 'private_table' not in serialized


def test_validation_messages_are_still_actionable():
    report = SimpleNamespace(error=None, failed={'target': 'layer changed while the filter was running'},
                             details={}, done_names=[], skipped={}, outputs={})
    result = qgis_accessor.QGISFilterMateAccessor._operation_result(report)
    assert result.failed == report.failed
