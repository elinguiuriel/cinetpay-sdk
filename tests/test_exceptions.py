from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cinetpay_sdk.exceptions import (
    APIError,
    AuthenticationError,
    CinetPayError,
    NetworkError,
    ValidationError,
)


class ExceptionTests(unittest.TestCase):
    def test_base_exception_stores_metadata(self):
        error = CinetPayError(
            "boom",
            code=123,
            status="FAILED",
            http_status=400,
            payload={"hello": "world"},
        )

        self.assertEqual(str(error), "boom")
        self.assertEqual(error.message, "boom")
        self.assertEqual(error.code, 123)
        self.assertEqual(error.status, "FAILED")
        self.assertEqual(error.http_status, 400)
        self.assertEqual(error.payload, {"hello": "world"})

    def test_exception_subclasses_are_constructible(self):
        self.assertIsInstance(APIError("api"), CinetPayError)
        self.assertIsInstance(AuthenticationError("auth"), APIError)
        self.assertIsInstance(ValidationError("validation"), APIError)
        self.assertIsInstance(NetworkError("network"), CinetPayError)


if __name__ == "__main__":
    unittest.main()
