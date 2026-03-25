from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cinetpay_sdk import CinetPayClient, PaymentRequest
from cinetpay_sdk.models import NotificationPayload
from cinetpay_sdk.transport import HttpResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, *, headers=None, json_data=None, timeout=30.0):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers or {}),
                "json_data": json_data,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)

    def close(self):
        return None


class CinetPayClientTests(unittest.TestCase):
    def test_authenticate_stores_access_token(self):
        transport = FakeTransport(
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
                )
            ]
        )
        client = CinetPayClient("key", "password", transport=transport)

        token = client.authenticate()

        self.assertEqual(token.access_token, "token-123")
        self.assertEqual(transport.calls[0]["url"], "https://api.cinetpay.net/v1/oauth/login")
        self.assertEqual(client._access_token, "token-123")

    def test_create_payment_auto_authenticates_and_sends_bearer_token(self):
        transport = FakeTransport(
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
                        "code": 200,
                        "status": "OK",
                        "payment_token": "payment-token",
                        "notify_token": "notify-token",
                        "transaction_id": "transaction-123",
                        "merchant_transaction_id": "order-123",
                        "payment_url": "https://secure.cinetpay.net/payment/payment-token",
                        "details": {
                            "code": 2001,
                            "status": "INITIATED",
                            "message": "Please click the link to continue the payment",
                            "must_be_redirected": True,
                        },
                    },
                ),
            ]
        )
        client = CinetPayClient("key", "password", transport=transport)

        payment = client.create_payment(
            PaymentRequest(
                currency="XOF",
                payment_method="OM",
                merchant_transaction_id="order-123",
                amount=1000,
                lang="fr",
                designation="Test payment",
                client_email="test@example.com",
                client_first_name="Jane",
                client_last_name="Doe",
                client_phone_number="+2250707000000",
                success_url="https://merchant.test/success",
                failed_url="https://merchant.test/failed",
                notify_url="https://merchant.test/notify",
            )
        )

        self.assertEqual(payment.payment_token, "payment-token")
        self.assertTrue(payment.should_redirect)
        self.assertEqual(transport.calls[1]["headers"]["Authorization"], "Bearer token-123")

    def test_expired_token_reauthenticates_once(self):
        transport = FakeTransport(
            [
                HttpResponse(
                    status_code=200,
                    json_body={
                        "code": 200,
                        "status": "OK",
                        "access_token": "token-1",
                        "token_type": "bearer",
                        "expires_in": 86400,
                    },
                ),
                HttpResponse(
                    status_code=200,
                    json_body={
                        "code": 1003,
                        "status": "EXPIRED_TOKEN",
                        "message": "The authentication token has expired",
                    },
                ),
                HttpResponse(
                    status_code=200,
                    json_body={
                        "code": 200,
                        "status": "OK",
                        "access_token": "token-2",
                        "token_type": "bearer",
                        "expires_in": 86400,
                    },
                ),
                HttpResponse(
                    status_code=200,
                    json_body={
                        "code": 100,
                        "status": "SUCCESS",
                        "merchant_transaction_id": "order-123",
                        "transaction_id": "transaction-123",
                        "user": {
                            "name": "Doe John",
                            "email": "john.doe@gmail.com",
                            "phone_number": "+2250707000000",
                        },
                    },
                ),
            ]
        )
        client = CinetPayClient("key", "password", transport=transport)

        status = client.get_payment_status("payment-token")

        self.assertEqual(status.status, "SUCCESS")
        self.assertEqual(client._access_token, "token-2")
        self.assertEqual(transport.calls[3]["headers"]["Authorization"], "Bearer token-2")

    def test_notification_helpers(self):
        payload = {
            "notify_token": "notify-token",
            "merchant_transaction_id": "order-123",
            "transaction_id": "transaction-123",
            "user": {
                "name": "Jaqn HGHAR",
                "email": "jaqen@gmail.com",
                "phone_number": "+2250700356615",
            },
        }

        notification = CinetPayClient.parse_notification(payload)

        self.assertIsInstance(notification, NotificationPayload)
        self.assertTrue(CinetPayClient.validate_notification(payload, "notify-token"))
        self.assertFalse(CinetPayClient.validate_notification(payload, "other-token"))

    def test_direct_pay_requires_phone_number(self):
        request = PaymentRequest(
            currency="XOF",
            payment_method="OM",
            merchant_transaction_id="order-123",
            amount=1000,
            lang="fr",
            designation="Test payment",
            client_email="test@example.com",
            client_first_name="Jane",
            client_last_name="Doe",
            success_url="https://merchant.test/success",
            failed_url="https://merchant.test/failed",
            notify_url="https://merchant.test/notify",
            direct_pay=True,
        )

        with self.assertRaises(ValueError):
            request.to_payload()


if __name__ == "__main__":
    unittest.main()
