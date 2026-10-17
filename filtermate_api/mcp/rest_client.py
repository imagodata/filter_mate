"""Blocking HTTP client of the FilterMate REST API (standard library only).

Every failure becomes a :class:`FilterMateAPIError` whose message is written
for the language model reading it: what happened, whether anything changed in
QGIS, and what to do next.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import quote

API_KEY_HEADER = "X-API-Key"
# A layer list of a big project stays far below this; it only bounds a rogue answer.
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024

_START_HINT = (
    "Start the FilterMate REST API in QGIS (it is not started by the plugin itself): in the Python console, "
    "build a QGISFilterMateAccessor from the FilterMate plugin and serve create_app(...) with uvicorn, "
    "with the same API key as FILTERMATE_API_KEY. See docs/AUTOMATION.md, section 'MCP server'."
)


class FilterMateAPIError(RuntimeError):
    """A call to the FilterMate REST API failed; ``str(exc)`` explains it to the assistant."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects: the API key header must not follow one to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


class FilterMateClient:
    """Calls the REST API with the ``X-API-Key`` header.

    Args:
        base_url: API root, e.g. ``http://127.0.0.1:8000`` (no trailing slash needed).
        api_key: Value of the ``X-API-Key`` header.
        timeout: Seconds to wait for an answer (above the API's 30 s main thread wait).
        use_proxy: Honour ``HTTP(S)_PROXY`` variables. Off for loopback URLs: a local
            call must not leave the machine through a proxy.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 45.0, use_proxy: bool = False):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        handlers = [_NoRedirect()]
        if not use_proxy:
            handlers.append(urllib.request.ProxyHandler({}))
        self._opener = urllib.request.build_opener(*handlers)

    @property
    def base_url(self) -> str:
        """API root this client calls."""
        return self._base_url

    def get(self, path: str) -> Any:
        """GET ``path`` and return the decoded JSON answer."""
        return self.request("GET", path)

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        """POST ``body`` as JSON to ``path`` and return the decoded JSON answer."""
        return self.request("POST", path, body if body is not None else {})

    def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        """Send one request.

        Raises:
            FilterMateAPIError: unreachable API, timeout, or an HTTP error status.
        """
        url = self._base_url + path
        headers = {API_KEY_HEADER: self._api_key, "Accept": "application/json"}
        data = None
        if body is None and method != "GET":
            body = {}  # a JSON object, like every other write: some routes take no body, none minds one
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            try:
                raw = exc.read(_MAX_RESPONSE_BYTES)
            finally:
                exc.close()
            raise self._http_error(method, path, exc.code, exc.headers, raw) from None
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                raise self._timeout_error(method, path) from None
            raise FilterMateAPIError(
                f"Cannot reach the FilterMate REST API at {self._base_url} ({reason}). {_START_HINT}") from None
        except TimeoutError:
            raise self._timeout_error(method, path) from None
        except OSError as exc:
            raise FilterMateAPIError(
                f"Connection to the FilterMate REST API at {self._base_url} failed ({exc}). {_START_HINT}") from None
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise FilterMateAPIError("The FilterMate REST API answer is too large to be read.")
        try:
            return json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            raise FilterMateAPIError(
                f"{self._base_url} did not answer JSON: this is not the FilterMate REST API "
                "(check --url and the port).") from None

    # -- error translation ---------------------------------------------------

    def _timeout_error(self, method: str, path: str) -> FilterMateAPIError:
        writes = method != "GET"
        return FilterMateAPIError(
            f"The FilterMate REST API did not answer {method} {path} within {self._timeout:.0f} s. "
            + ("QGIS may still be working on it: read filter_state before retrying, "
               "so that the change is not applied twice." if writes
               else "QGIS is probably busy on a long task; retry in a moment."))

    def _http_error(self, method: str, path: str, status: int, headers, raw: bytes) -> FilterMateAPIError:
        detail = _detail(raw)
        if status in (401, 403):
            if status == 401:
                why = "The FilterMate REST API rejected the API key (HTTP 401)."
            else:
                why = "The FilterMate REST API refused the request (HTTP 403)."
            return FilterMateAPIError(
                f"{why} Check that the key in the environment variable of the MCP server is the one "
                f"configured for the API in QGIS. Server said: {detail}", status)
        if status == 503:
            retry = headers.get("Retry-After") if headers is not None else None
            when = f" Retry in about {retry} s." if retry else " Retry in a moment."
            return FilterMateAPIError(
                f"QGIS is busy (a FilterMate operation or a long task is running); nothing was changed.{when} "
                f"Server said: {detail}", status)
        if status == 422:
            return FilterMateAPIError(f"The request was rejected as invalid (HTTP 422): {detail}", status)
        if status == 404:
            return FilterMateAPIError(f"Not found (HTTP 404): {detail}. Use list_layers / list_favorites "
                                      "to see what exists.", status)
        if status == 409:
            return FilterMateAPIError(f"Nothing to do (HTTP 409): {detail}", status)
        return FilterMateAPIError(f"{method} {path} failed (HTTP {status}): {detail}", status)


def _detail(raw: bytes) -> str:
    """Readable text of an error body (FastAPI ``{"detail": ...}`` or anything else)."""
    text = raw.decode("utf-8", errors="replace").strip()
    try:
        payload = json.loads(text)
    except ValueError:
        return text[:500] or "(no details)"
    detail = payload.get("detail") if isinstance(payload, dict) else payload
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                where = ".".join(str(p) for p in item.get("loc", []) if p != "body")
                msg = item.get("msg", "invalid")
                parts.append(f"{where}: {msg}" if where else str(msg))
            else:
                parts.append(str(item))
        return "; ".join(parts) or "(no details)"
    return json.dumps(detail)[:500] if detail is not None else "(no details)"


def quote_segment(value: str) -> str:
    """Percent-encode one URL path segment (a favorite id may hold any character)."""
    return quote(value, safe="")
