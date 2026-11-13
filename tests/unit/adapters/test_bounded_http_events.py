# -*- coding: utf-8 -*-
"""The end of a server-sent event read by ``adapters/agent/bounded_http.py``, whatever the chunks of the answer.

2026-11-13: only the chunk just received was looked at, so a blank line cut between two chunks ended no event, and
an MCP connector waited for another event or for its timeout. The module is loaded alone (it imports only QGIS,
mocked by the root conftest, and QtNetwork, mocked here).
"""
import importlib.util
import pathlib
import sys
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

_PATH = pathlib.Path(__file__).resolve().parents[3] / "adapters" / "agent" / "bounded_http.py"


@pytest.fixture(scope="module")
def bounded_http():
    stubbed = "qgis.PyQt.QtNetwork" not in sys.modules
    if stubbed:
        sys.modules["qgis.PyQt.QtNetwork"] = MagicMock()
    try:
        spec = importlib.util.spec_from_file_location("fm_bounded_http_events_test", _PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module  # dataclasses look their module up there
        spec.loader.exec_module(module)
        return module
    finally:
        if stubbed:
            sys.modules.pop("qgis.PyQt.QtNetwork", None)


def _ends(module, chunks):
    """Whether each chunk ends an event, the chunks given one after the other as Qt gives them."""
    tail, ended = b"", []
    for chunk in chunks:
        done, tail = module.ends_an_event(tail, chunk)
        ended.append(done)
    return ended


EVENT = b'event: message\ndata: {"jsonrpc": "2.0", "id": 1, "result": {}}\n\n'
EVENT_CRLF = EVENT.replace(b"\n", b"\r\n")


@pytest.mark.parametrize("answer", [EVENT, EVENT_CRLF])
def test_an_event_ends_wherever_the_chunks_cut_it(bounded_http, answer):
    # The blank line is at the end only: the second chunk always completes it. The first one never does, but for
    # a CRLF blank line cut before its LF: the CR is already an end of line, whatever follows it.
    for cut in range(1, len(answer)):
        first, second = _ends(bounded_http, [answer[:cut], answer[cut:]])
        assert second is True and first is answer[:cut].endswith(b"\r\n\r"), cut


def test_a_separator_given_byte_by_byte_ends_the_event(bounded_http):
    ended = _ends(bounded_http, [bytes([byte]) for byte in EVENT_CRLF])
    assert ended[-1] and not any(ended[:-2])  # seen from the CR of the blank line, and with its LF


def test_no_blank_line_ends_no_event(bounded_http):
    assert _ends(bounded_http, [b"event: message\n", b"data: {", b'"id": 1}\n']) == [False, False, False]
    # a line feed at the end of one chunk and the next starting with text: one line, not a blank one
    assert _ends(bounded_http, [b"data: a\n", b"data: b"]) == [False, False]


@pytest.mark.parametrize("blank", [b"\n\r\n", b"\r\n\n", b"\r\r", b"\r\n\r", b"\n\r"])
def test_a_blank_line_of_mixed_line_ends_ends_the_event(bounded_http, blank):
    """A line of an event stream ends with CRLF, LF or CR: only "\\n\\n" and "\\r\\n\\r\\n" were seen, and a
    server mixing them (LF after its data, CRLF for the blank line) left the request waiting for its timeout."""
    answer = b'data: {"id": 1}' + blank
    assert _ends(bounded_http, [answer]) == [True]
    for cut in range(1, len(answer)):
        assert _ends(bounded_http, [answer[:cut], answer[cut:]])[-1] is True, cut


def test_one_line_end_is_not_a_blank_line(bounded_http):
    """CRLF is one end of line, not two: it must not be read as CR then LF."""
    assert _ends(bounded_http, [b"data: a\r\ndata: b\r\n"]) == [False]
    assert _ends(bounded_http, [b"data: a\r", b"\ndata: b\r", b"\n"]) == [False, False, False]
    assert _ends(bounded_http, [b"data: a\rdata: b\r"]) == [False]
