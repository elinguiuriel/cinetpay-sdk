from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cinetpay_sdk.models import (
    AccessToken,
    BalanceResponse,
    NotificationPayload,
    PaymentDetails,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusResponse,
    TransferRequest,
    TransferResponse,
    UserInfo,
    _as_int,
    _clean_payload,
    _is_valid_url,
    _user_from_dict,
)


def valid_payment_kwargs():
    return {
        "currency": "XOF",
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
        "payment_method": "OM",
    }


def valid_transfer_kwargs():
    return {
        "currency": "XOF",
        "payment_method": "OM_CI",
        "merchant_transaction_id": "transfer-123",
        "amount": 100,
        "phone_number": "+2250707000001",
        "reason": "Account top-up",
        "notify_url": "https://merchant.test/notify",
    }


class ModelHelperTests(unittest.TestCase):
    def test_helper_functions_cover_expected_edge_cases(self):
        self.assertEqual(_as_int("12"), 12)
        self.assertIsNone(_as_int(None))
        self.assertIsNone(_as_int("abc"))
        self.assertTrue(_is_valid_url("https://merchant.test/notify"))
        self.assertFalse(_is_valid_url("not-a-url"))
        self.assertEqual(_clean_payload({"a": 1, "b": None}), {"a": 1})
        self.assertIsNone(_user_from_dict(None))
        self.assertEqual(
            _user_from_dict({"name": "Jane", "email": "jane@example.com", "phone_number": "+225"}),
            UserInfo(name="Jane", email="jane@example.com", phone_number="+225"),
        )

    def test_access_token_defaults_and_notification_payload(self):
        token = AccessToken.from_dict({"access_token": "abc"})
        self.assertEqual(token.token_type, "bearer")
        self.assertEqual(token.access_token, "abc")

        notification = NotificationPayload.from_dict({"notify_token": "token"})
        self.assertEqual(notification.notify_token, "token")
        self.assertIsNone(notification.user)


class PaymentModelTests(unittest.TestCase):
    def test_payment_details_and_response_flags(self):
        self.assertIsNone(PaymentDetails.from_dict(None))

        details = PaymentDetails.from_dict(
            {
                "code": 2010,
                "status": "FAILED",
                "message": "Failed",
                "must_be_redirected": False,
            }
        )
        assert details is not None
        self.assertTrue(details.is_final)

        response = PaymentResponse.from_dict({"code": 100, "status": "SUCCESS"})
        self.assertTrue(response.is_final)
        self.assertFalse(response.should_redirect)

        status = PaymentStatusResponse.from_dict({"code": 200, "status": "PENDING"})
        self.assertFalse(status.is_final)
        self.assertIsNone(status.user)

    def test_payment_request_to_payload_omits_none(self):
        request = PaymentRequest(**valid_payment_kwargs())
        payload = request.to_payload()
        self.assertNotIn("client_phone_number", payload)
        self.assertNotIn("otp_code", payload)

    def test_payment_request_validation_errors(self):
        cases = [
            ({**valid_payment_kwargs(), "currency": ""}, "currency is required"),
            ({**valid_payment_kwargs(), "merchant_transaction_id": ""}, "merchant_transaction_id is required"),
            (
                {**valid_payment_kwargs(), "merchant_transaction_id": "x" * 31},
                "merchant_transaction_id must be 30 characters or fewer",
            ),
            ({**valid_payment_kwargs(), "amount": 0}, "amount must be greater than 0"),
            ({**valid_payment_kwargs(), "lang": "de"}, "lang must be 'fr' or 'en'"),
            ({**valid_payment_kwargs(), "designation": ""}, "designation is required"),
            ({**valid_payment_kwargs(), "client_email": "invalid"}, "client_email must be a valid email address"),
            ({**valid_payment_kwargs(), "client_first_name": "J"}, "client_first_name must contain between 2 and 255 characters"),
            ({**valid_payment_kwargs(), "client_last_name": "D"}, "client_last_name must contain between 2 and 255 characters"),
            ({**valid_payment_kwargs(), "success_url": ""}, "success_url is required"),
            ({**valid_payment_kwargs(), "success_url": "https://merchant.test/" + ("a" * 110)}, "success_url must be 120 characters or fewer"),
            ({**valid_payment_kwargs(), "success_url": "bad-url"}, "success_url must be a valid URL"),
            ({**valid_payment_kwargs(), "direct_pay": True}, "client_phone_number is required when direct_pay=True"),
            ({**valid_payment_kwargs(), "otp_code": "12ab"}, "otp_code must contain only digits"),
            ({**valid_payment_kwargs(), "otp_code": "123"}, "otp_code must contain between 4 and 6 digits"),
        ]

        for kwargs, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    PaymentRequest(**kwargs).to_payload()


class TransferModelTests(unittest.TestCase):
    def test_transfer_response_and_balance_response(self):
        response = TransferResponse.from_dict({"code": 2002, "status": "PENDING"})
        self.assertFalse(response.is_final)

        balance = BalanceResponse.from_dict(
            {"code": 200, "status": "OK", "currency": "XOF", "available_balance": 10}
        )
        self.assertEqual(balance.balances, {"currency": "XOF", "available_balance": 10})

    def test_transfer_request_validation_errors(self):
        cases = [
            ({**valid_transfer_kwargs(), "currency": ""}, "currency is required"),
            ({**valid_transfer_kwargs(), "payment_method": ""}, "payment_method is required"),
            ({**valid_transfer_kwargs(), "merchant_transaction_id": ""}, "merchant_transaction_id is required"),
            (
                {**valid_transfer_kwargs(), "merchant_transaction_id": "x" * 31},
                "merchant_transaction_id must be 30 characters or fewer",
            ),
            ({**valid_transfer_kwargs(), "amount": 0}, "amount must be greater than 0"),
            ({**valid_transfer_kwargs(), "phone_number": ""}, "phone_number is required"),
            ({**valid_transfer_kwargs(), "reason": ""}, "reason is required"),
            ({**valid_transfer_kwargs(), "notify_url": ""}, "notify_url is required"),
            ({**valid_transfer_kwargs(), "notify_url": "bad-url"}, "notify_url must be a valid URL"),
        ]

        for kwargs, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    TransferRequest(**kwargs).to_payload()


if __name__ == "__main__":
    unittest.main()
