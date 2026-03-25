from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cinetpay_sdk.client import CinetPayClient
from cinetpay_sdk.exceptions import APIError, AuthenticationError, ValidationError
from cinetpay_sdk.models import PaymentResponse, TransferResponse
from cinetpay_sdk.transport import HttpResponse


class RecordingTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.closed = False

    def request(self, method, url, *, headers=None, json_data=None, timeout=30.0):
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class ClientInternalTests(unittest.TestCase):
    def test_client_validates_required_constructor_arguments(self):
        with self.assertRaisesRegex(ValueError, "api_key is required"):
            CinetPayClient("", "password")
        with self.assertRaisesRegex(ValueError, "api_password is required"):
            CinetPayClient("key", "")

    def test_from_env_validates_presence_and_uses_custom_variables(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Environment variable CINETPAY_API_KEY is missing"):
                CinetPayClient.from_env()

        with patch.dict(os.environ, {"CINETPAY_API_KEY": "key"}, clear=True):
            with self.assertRaisesRegex(ValueError, "Environment variable CINETPAY_API_PASSWORD is missing"):
                CinetPayClient.from_env()

        with patch.dict(
            os.environ,
            {"APP_KEY": "key", "APP_PASSWORD": "password", "APP_BASE_URL": "https://custom.test"},
            clear=True,
        ):
            client = CinetPayClient.from_env(
                api_key_var="APP_KEY",
                api_password_var="APP_PASSWORD",
                base_url_var="APP_BASE_URL",
            )
            self.assertEqual(client.base_url, "https://custom.test")

    def test_context_manager_and_close_delegate_to_transport(self):
        transport = RecordingTransport([])
        client = CinetPayClient("key", "password", transport=transport)

        with client as current:
            self.assertIs(current, client)

        self.assertTrue(transport.closed)

    def test_authenticate_uses_cached_token_when_available(self):
        client = CinetPayClient("key", "password", transport=RecordingTransport([]))
        client._access_token = "cached-token"
        client._token_type = "Bearer"

        token = client.authenticate()

        self.assertEqual(token.access_token, "cached-token")
        self.assertEqual(token.status, "OK")

    def test_authenticate_raises_when_response_has_no_access_token(self):
        transport = RecordingTransport([HttpResponse(status_code=200, json_body={"code": 200, "status": "OK"})])
        client = CinetPayClient("key", "password", transport=transport)

        with self.assertRaises(AuthenticationError):
            client.authenticate(force=True)

    def test_create_methods_accept_plain_mappings(self):
        transport = RecordingTransport(
            [
                HttpResponse(
                    status_code=200,
                    json_body={
                        "code": 200,
                        "status": "OK",
                        "access_token": "token-123",
                        "token_type": "bearer",
                        "expires_in": 86400,
                    },
                ),
                HttpResponse(status_code=200, json_body={"code": 200, "status": "OK", "payment_token": "token"}),
                HttpResponse(status_code=200, json_body={"code": 100, "status": "SUCCESS", "transaction_id": "trf"}),
            ]
        )
        client = CinetPayClient("key", "password", transport=transport)

        payment = client.create_payment(
            {
                "currency": "XOF",
                "payment_method": "OM",
                "merchant_transaction_id": "order-123",
                "amount": 100,
                "lang": "fr",
                "designation": "Test payment",
                "client_email": "client@example.com",
                "client_first_name": "Jane",
                "client_last_name": "Doe",
                "success_url": "https://merchant.test/success",
                "failed_url": "https://merchant.test/failed",
                "notify_url": "https://merchant.test/notify",
            }
        )
        transfer = client.create_transfer(
            {
                "currency": "XOF",
                "payment_method": "OM_CI",
                "merchant_transaction_id": "transfer-123",
                "amount": 100,
                "phone_number": "+2250707000001",
                "reason": "Account top-up",
                "notify_url": "https://merchant.test/notify",
            }
        )

        self.assertIsInstance(payment, PaymentResponse)
        self.assertIsInstance(transfer, TransferResponse)

    def test_status_methods_require_identifiers(self):
        client = CinetPayClient("key", "password", transport=RecordingTransport([]))

        with self.assertRaisesRegex(ValueError, "identifier is required"):
            client.get_payment_status("")
        with self.assertRaisesRegex(ValueError, "transaction_id is required"):
            client.get_transfer_status("")

    def test_get_transfer_status_returns_typed_response(self):
        transport = RecordingTransport(
            [
                HttpResponse(
                    status_code=200,
                    json_body={
                        "code": 200,
                        "status": "OK",
                        "access_token": "token-123",
                        "token_type": "bearer",
                        "expires_in": 86400,
                    },
                ),
                HttpResponse(
                    status_code=200,
                    json_body={
                        "code": 100,
                        "status": "SUCCESS",
                        "merchant_transaction_id": "transfer-123",
                        "transaction_id": "transaction-123",
                        "amount": 100,
                        "fee_amount": 2,
                    },
                ),
            ]
        )
        client = CinetPayClient("key", "password", transport=transport)

        status = client.get_transfer_status("transaction-123")

        self.assertIsInstance(status, TransferResponse)
        self.assertEqual(status.transaction_id, "transaction-123")

    def test_build_error_and_helper_branches(self):
        self.assertEqual(CinetPayClient._format_token_type("custom"), "custom")
        self.assertIsNone(CinetPayClient._coerce_code({"code": "not-an-int"}))

        auth_error = CinetPayClient._build_error({"code": 1002, "status": "INVALID_TOKEN"}, 401)
        self.assertIsInstance(auth_error, AuthenticationError)

        validation_error = CinetPayClient._build_error({"status": "BAD"}, 422)
        self.assertIsInstance(validation_error, ValidationError)

        generic_error = CinetPayClient._build_error({"detail": "blocked"}, 403)
        self.assertIsInstance(generic_error, APIError)
        self.assertEqual(generic_error.message, "blocked")

        title_error = CinetPayClient._build_error({"title": "forbidden"}, 403)
        self.assertEqual(title_error.message, "forbidden")

        status_error = CinetPayClient._build_error({"status": 403}, 403)
        self.assertEqual(status_error.message, "403")

        fallback_error = CinetPayClient._build_error({}, 500)
        self.assertEqual(fallback_error.message, "CinetPay API request failed with HTTP 500")

    def test_request_raises_expected_error_types(self):
        client = CinetPayClient("key", "password", transport=RecordingTransport([HttpResponse(status_code=422, json_body={})]))
        with self.assertRaises(ValidationError):
            client._request("POST", "/v1/payment", auth=False)

        client = CinetPayClient(
            "key",
            "password",
            transport=RecordingTransport([HttpResponse(status_code=200, json_body={"code": 1005, "status": "INVALID_CREDENTIALS"})]),
        )
        with self.assertRaises(AuthenticationError):
            client._request("POST", "/v1/oauth/login", auth=False)


if __name__ == "__main__":
    unittest.main()
