from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
