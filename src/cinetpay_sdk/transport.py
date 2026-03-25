"""Internal HTTP transport layer for the CinetPay SDK.

The rest of the SDK talks to a small `Transport` protocol instead of directly
depending on `urllib`. This keeps the client implementation easy to test and
lets applications swap in a custom transport if they need a different HTTP
stack, additional logging, or custom retry behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .exceptions import NetworkError


@dataclass(frozen=True)
class HttpResponse:
    """Normalized HTTP response returned by a transport implementation."""

    status_code: int
    json_body: Dict[str, Any] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)


class Transport(Protocol):
    """Minimal protocol that a client-compatible transport must implement."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
        """Execute one HTTP request and return a normalized response."""
        ...

    def close(self) -> None:
        """Release any transport-level resources."""
        ...


class UrllibTransport:
    """Default transport implementation based on the Python standard library.

    This transport intentionally stays small and dependency-free. Its role is to
    serialize JSON payloads, normalize successful and failing HTTP responses,
    and convert lower-level connectivity errors into `NetworkError`.
    """

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
        """Execute an HTTP request using `urllib`.

        HTTP error responses are returned as normal `HttpResponse` objects rather
        than raising immediately, because API-level failures are part of the
        client's normal control flow and are interpreted one layer above.
        """
        request_headers = dict(headers or {})
        body = None
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        request_headers.setdefault("Accept", "application/json")

        request = Request(url=url, data=body, headers=request_headers, method=method.upper())

        try:
            with urlopen(request, timeout=timeout) as response:
                return HttpResponse(
                    status_code=response.status,
                    json_body=self._decode_json(response.read()),
                    headers=dict(response.headers.items()),
                )
        except HTTPError as exc:
            # Keep HTTP errors in-band so the client can classify them using the
            # API payload, status code, and repository-specific error mapping.
            return HttpResponse(
                status_code=exc.code,
                json_body=self._decode_json(exc.read()),
                headers=dict(exc.headers.items()),
            )
        except URLError as exc:
            raise NetworkError(f"Unable to reach CinetPay API: {exc.reason}") from exc

    def close(self) -> None:
        """Close the transport.

        `urllib` does not hold a persistent client object, so there is nothing
        to release here. The method still exists to satisfy the transport
        protocol and allow alternative implementations to clean up resources.
        """
        return None

    @staticmethod
    def _decode_json(body: bytes) -> Dict[str, Any]:
        """Decode a response body into a dictionary.

        The SDK expects JSON dictionaries from CinetPay. When the upstream body
        is empty or malformed, the transport returns a best-effort dictionary so
        callers still receive the raw content for debugging.
        """
        if not body:
            return {}
        text = body.decode("utf-8")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"raw_body": text}
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}
