"""Internal HTTP transport for the CinetPay SDK."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .exceptions import NetworkError


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    json_body: Dict[str, Any] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
        ...

    def close(self) -> None:
        ...


class UrllibTransport:
    """Default transport implementation based on urllib."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
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
            return HttpResponse(
                status_code=exc.code,
                json_body=self._decode_json(exc.read()),
                headers=dict(exc.headers.items()),
            )
        except URLError as exc:
            raise NetworkError(f"Unable to reach CinetPay API: {exc.reason}") from exc

    def close(self) -> None:
        return None

    @staticmethod
    def _decode_json(body: bytes) -> Dict[str, Any]:
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
