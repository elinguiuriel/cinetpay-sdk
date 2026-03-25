from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cinetpay_sdk.harness import (
    ScenarioResult,
    ScenarioTransport,
    _assert_expectations,
    _dispatch,
    _read_path,
    load_scenarios,
    main,
    run_repository_harness,
    run_scenario,
)


class HarnessInternalTests(unittest.TestCase):
    def test_scenario_transport_out_of_responses_and_close(self):
        transport = ScenarioTransport([])
        self.assertIsNone(transport.close())
        with self.assertRaisesRegex(AssertionError, "Harness transport ran out of responses"):
            transport.request("GET", "https://example.test")

    def test_load_scenarios_and_missing_directory(self):
        with self.assertRaises(FileNotFoundError):
            load_scenarios(Path("/does/not/exist"))

        with tempfile.TemporaryDirectory() as tmpdir:
            scenario_dir = Path(tmpdir)
            (scenario_dir / "b.json").write_text(json.dumps({"name": "b"}), encoding="utf-8")
            (scenario_dir / "a.json").write_text(json.dumps({"name": "a"}), encoding="utf-8")
            scenarios = load_scenarios(scenario_dir)
            self.assertEqual([item["name"] for item in scenarios], ["a", "b"])

    def test_read_path_dispatch_and_run_repository_harness(self):
        self.assertEqual(_read_path({"a": {"b": 1}}, "a.b"), 1)
        self.assertEqual(_read_path(SimpleNamespace(a=SimpleNamespace(b=2)), "a.b"), 2)

        client = SimpleNamespace(
            create_payment=lambda payload: ("payment", payload),
            get_payment_status=lambda identifier: ("payment-status", identifier),
            create_transfer=lambda payload: ("transfer", payload),
            get_transfer_status=lambda transaction_id: ("transfer-status", transaction_id),
            get_balances=lambda: ("balances", None),
        )
        self.assertEqual(_dispatch(client, {"name": "get_transfer_status", "transaction_id": "abc"}), ("transfer-status", "abc"))
        self.assertEqual(_dispatch(client, {"name": "get_balances"}), ("balances", None))
        with self.assertRaisesRegex(ValueError, "Unsupported harness operation"):
            _dispatch(client, {"name": "unknown"})

        with tempfile.TemporaryDirectory() as tmpdir:
            scenario = {
                "name": "ok",
                "responses": [
                    {
                        "status_code": 200,
                        "json_body": {
                            "code": 200,
                            "status": "OK",
                            "access_token": "token",
                            "token_type": "bearer",
                            "expires_in": 10,
                        },
                    },
                    {"status_code": 200, "json_body": {"code": 200, "status": "OK", "payment_token": "token"}},
                ],
                "operation": {
                    "name": "create_payment",
                    "payload": {
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
                    },
                },
                "expect": {
                    "attrs": {"payment_token": "token"},
                    "call_sequence": [
                        {"method": "POST", "path": "/v1/oauth/login"},
                        {"method": "POST", "path": "/v1/payment", "authorization": "Bearer token"},
                    ],
                },
            }
            scenario_dir = Path(tmpdir)
            (scenario_dir / "ok.json").write_text(json.dumps(scenario), encoding="utf-8")
            results = run_repository_harness(scenario_dir)
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].passed)

    def test_assert_expectations_failure_modes_and_run_scenario(self):
        transport = ScenarioTransport([])
        transport.calls = [{"method": "POST", "url": "https://api.cinetpay.net/v1/payment", "headers": {}, "json_data": None, "timeout": 30.0}]
        result = SimpleNamespace(status="OK")

        with self.assertRaisesRegex(AssertionError, "Expected status='FAILED'"):
            _assert_expectations(result=result, transport=transport, expect={"attrs": {"status": "FAILED"}})

        with self.assertRaisesRegex(AssertionError, "Expected 2 HTTP calls, got 1"):
            _assert_expectations(result=result, transport=transport, expect={"call_sequence": [{}, {}]})

        with self.assertRaisesRegex(AssertionError, "expected method GET"):
            _assert_expectations(
                result=result,
                transport=transport,
                expect={"call_sequence": [{"method": "GET", "path": "/v1/payment"}]},
            )

        with self.assertRaisesRegex(AssertionError, "expected URL"):
            _assert_expectations(
                result=result,
                transport=transport,
                expect={"call_sequence": [{"method": "POST", "path": "/v1/balances"}]},
            )

        with self.assertRaisesRegex(AssertionError, "expected Authorization"):
            _assert_expectations(
                result=result,
                transport=transport,
                expect={"call_sequence": [{"method": "POST", "path": "/v1/payment", "authorization": "Bearer token"}]},
            )

        failed = run_scenario({"name": "broken", "responses": [], "operation": {"name": "unknown"}, "expect": {}})
        self.assertFalse(failed.passed)

    def test_main_reports_pass_and_fail(self):
        with patch("cinetpay_sdk.harness.run_repository_harness", return_value=[ScenarioResult("ok", True, "done")]):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertIn("[PASS] ok: done", stdout.getvalue())

        with patch("cinetpay_sdk.harness.run_repository_harness", return_value=[ScenarioResult("bad", False, "boom")]):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main()
            self.assertEqual(code, 1)
            self.assertIn("[FAIL] bad: boom", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
