from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "sandbox_cli.py"


def load_module():
    """Load the sandbox CLI module from its script path."""
    spec = importlib.util.spec_from_file_location("sandbox_cli", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class SandboxCliTests(unittest.TestCase):
    def test_load_env_file_reads_simple_key_value_pairs(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "CINETPAY_API_KEY=test-key\n"
                "CINETPAY_API_PASSWORD='test-password'\n"
                "# comment\n",
                encoding="utf-8",
            )

            previous_key = os.environ.pop("CINETPAY_API_KEY", None)
            previous_password = os.environ.pop("CINETPAY_API_PASSWORD", None)
            try:
                module.load_env_file(env_path)
                self.assertEqual(os.environ["CINETPAY_API_KEY"], "test-key")
                self.assertEqual(os.environ["CINETPAY_API_PASSWORD"], "test-password")
            finally:
                os.environ.pop("CINETPAY_API_KEY", None)
                os.environ.pop("CINETPAY_API_PASSWORD", None)
                if previous_key is not None:
                    os.environ["CINETPAY_API_KEY"] = previous_key
                if previous_password is not None:
                    os.environ["CINETPAY_API_PASSWORD"] = previous_password

    def test_mask_secret_masks_short_and_long_values(self):
        module = load_module()
        self.assertEqual(module.mask_secret("abcd"), "****")
        self.assertEqual(module.mask_secret("abcdefgh1234"), "abcd...1234")

    def test_build_transaction_id_respects_sdk_length_limit(self):
        module = load_module()
        value = module.build_transaction_id("payment")
        self.assertLessEqual(len(value), 30)
        self.assertTrue(value.startswith("payment-"))

    def test_parser_supports_env_check_command(self):
        module = load_module()
        parser = module.build_parser()
        args = parser.parse_args(["env-check"])
        self.assertEqual(args.command, "env-check")

    def test_load_env_file_respects_override_and_missing_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("CINETPAY_API_KEY=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"CINETPAY_API_KEY": "existing"}, clear=True):
                module.load_env_file(Path(tmpdir) / "missing.env")
                module.load_env_file(env_path, override=False)
                self.assertEqual(os.environ["CINETPAY_API_KEY"], "existing")

                module.load_env_file(env_path, override=True)
                self.assertEqual(os.environ["CINETPAY_API_KEY"], "from-file")

    def test_ensure_url_and_json_helpers(self):
        module = load_module()

        with patch.dict(os.environ, {"APP_URL": "https://env.test"}, clear=True):
            self.assertEqual(module.ensure_url("notify_url", None, "APP_URL"), "https://env.test")

        self.assertEqual(
            module.ensure_url("notify_url", "https://explicit.test", "APP_URL"),
            "https://explicit.test",
        )

        with self.assertRaises(SystemExit):
            module.ensure_url("notify_url", None, "APP_URL")

        self.assertEqual(module.to_jsonable({"items": (1, 2)}), {"items": [1, 2]})

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            module.print_json({"hello": "world"})
        self.assertIn('"hello": "world"', stdout.getvalue())

    def test_command_handlers_and_main(self):
        module = load_module()
        fake_client = SimpleNamespace(
            authenticate=lambda force=False: SimpleNamespace(
                code=200,
                status="OK",
                token_type="bearer",
                expires_in=100,
                access_token="token-12345678",
            ),
            get_balances=lambda: {"code": 200},
            create_payment=lambda request: request,
            get_payment_status=lambda identifier: {"identifier": identifier},
            create_transfer=lambda request: request,
            get_transfer_status=lambda transaction_id: {"transaction_id": transaction_id},
        )

        with patch.object(module, "ensure_client", return_value=fake_client), patch.object(module, "print_json") as print_json:
            self.assertEqual(module.command_auth(SimpleNamespace()), 0)
            self.assertEqual(module.command_balances(SimpleNamespace()), 0)
            self.assertEqual(module.command_payment_status(SimpleNamespace(identifier="payment-token")), 0)
            self.assertEqual(module.command_transfer_status(SimpleNamespace(transaction_id="transfer-token")), 0)

            with patch.dict(
                os.environ,
                {
                    "CINETPAY_SUCCESS_URL": "https://merchant.test/success",
                    "CINETPAY_FAILED_URL": "https://merchant.test/failed",
                    "CINETPAY_NOTIFY_URL": "https://merchant.test/notify",
                    "CINETPAY_TEST_CLIENT_EMAIL": "sandbox@example.com",
                },
                clear=True,
            ):
                payment_args = SimpleNamespace(
                    currency="XOF",
                    payment_method="OM",
                    merchant_transaction_id=None,
                    amount=100,
                    lang="fr",
                    designation="Sandbox payment",
                    client_email=None,
                    client_first_name="Jane",
                    client_last_name="Doe",
                    client_phone="+2250707070700",
                    success_url=None,
                    failed_url=None,
                    notify_url=None,
                    direct_pay=False,
                    otp_code=None,
                )
                transfer_args = SimpleNamespace(
                    currency="XOF",
                    payment_method="OM_CI",
                    merchant_transaction_id=None,
                    amount=100,
                    phone_number="+2250707000001",
                    reason="Account top-up",
                    notify_url=None,
                )

                self.assertEqual(module.command_payment(payment_args), 0)
                self.assertEqual(module.command_transfer(transfer_args), 0)

            self.assertTrue(print_json.called)

        with patch.object(module, "command_env_check", return_value=0):
            self.assertEqual(module.main(["env-check"]), 0)


if __name__ == "__main__":
    unittest.main()
