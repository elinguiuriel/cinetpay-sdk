from __future__ import annotations

import io
import sys
import unittest
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cinetpay_sdk.transport import DEFAULT_USER_AGENT, UrllibTransport


class FakeUrlopenResponse:
    def __init__(self, body: bytes = b'{"code":200,"status":"OK"}') -> None:
        self.status = 200
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        return None


class TransportTests(unittest.TestCase):
    def test_transport_sets_sdk_user_agent_by_default(self):
        captured = {}

        def fake_urlopen(request, timeout=30.0):
            captured["user_agent"] = request.get_header("User-agent")
            captured["timeout"] = timeout
            return FakeUrlopenResponse()

        transport = UrllibTransport()

        with patch("cinetpay_sdk.transport.urlopen", side_effect=fake_urlopen):
            response = transport.request(
                "POST",
                "https://api.cinetpay.net/v1/oauth/login",
                json_data={"hello": "world"},
            )

        self.assertEqual(captured["user_agent"], DEFAULT_USER_AGENT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json_body["status"], "OK")

    def test_transport_preserves_explicit_user_agent(self):
        captured = {}

        def fake_urlopen(request, timeout=30.0):
            captured["user_agent"] = request.get_header("User-agent")
            return FakeUrlopenResponse()

        transport = UrllibTransport()

        with patch("cinetpay_sdk.transport.urlopen", side_effect=fake_urlopen):
            transport.request(
                "GET",
                "https://api.cinetpay.net/v1/balances",
                headers={"User-Agent": "custom-agent/1.0"},
            )

        self.assertEqual(captured["user_agent"], "custom-agent/1.0")

    def test_transport_returns_http_error_response(self):
        headers = Message()
        headers["Content-Type"] = "application/json"
        http_error = HTTPError(
            "https://api.cinetpay.net/v1/payment",
            403,
            "Forbidden",
            headers,
            io.BytesIO(b'{"status":"FORBIDDEN"}'),
        )
        transport = UrllibTransport()

        with patch("cinetpay_sdk.transport.urlopen", side_effect=http_error):
            response = transport.request("GET", "https://api.cinetpay.net/v1/payment")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json_body["status"], "FORBIDDEN")

    def test_transport_wraps_url_errors_as_network_errors(self):
        transport = UrllibTransport()

        with patch("cinetpay_sdk.transport.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(Exception, "Unable to reach CinetPay API: offline"):
                transport.request("GET", "https://api.cinetpay.net/v1/payment")

    def test_transport_decode_json_edge_cases_and_close(self):
        transport = UrllibTransport()

        self.assertEqual(transport._decode_json(b""), {})
        self.assertEqual(transport._decode_json(b"not-json"), {"raw_body": "not-json"})
        self.assertEqual(transport._decode_json(b"[1, 2]"), {"data": [1, 2]})
        self.assertEqual(transport._decode_json(b'{"code": 200}'), {"code": 200})
        self.assertIsNone(transport.close())


if __name__ == "__main__":
    unittest.main()
