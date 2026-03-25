from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cinetpay_sdk import CinetPayClient, PaymentRequest, TransferRequest


def load_env_file(path: Path, *, override: bool = False) -> None:
    """Load a simple `.env` file into the process environment.

    The parser intentionally supports only the subset needed by this repository:
    `KEY=value` lines, optional surrounding quotes, and `#` comments at the
    beginning of a line.
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and (override or key not in os.environ):
            os.environ[key] = value


def mask_secret(value: str) -> str:
    """Return a masked representation suitable for terminal output."""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def build_transaction_id(prefix: str) -> str:
    """Build a unique transaction id short enough for the SDK constraints."""
    millis = int(time.time() * 1000)
    return f"{prefix}-{millis}"[:30]


def ensure_url(name: str, explicit_value: Optional[str], env_var: str) -> str:
    """Resolve a URL from CLI args or the environment."""
    value = explicit_value or os.getenv(env_var)
    if not value:
        raise SystemExit(
            f"Missing {name}. Pass --{name.replace('_', '-')} or define {env_var}."
        )
    return value


def ensure_client() -> CinetPayClient:
    """Create a client from environment variables after optional `.env` loading."""
    load_env_file(ROOT / ".env")
    return CinetPayClient.from_env()


def to_jsonable(value: Any) -> Any:
    """Convert SDK objects to JSON-serializable structures."""
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def print_json(value: Any) -> None:
    """Pretty-print a JSON-serializable object."""
    print(json.dumps(to_jsonable(value), indent=2, ensure_ascii=False))


def command_env_check(_: argparse.Namespace) -> int:
    """Show which sandbox configuration values are available without exposing secrets."""
    load_env_file(ROOT / ".env")
    summary = {
        "CINETPAY_API_KEY": bool(os.getenv("CINETPAY_API_KEY")),
        "CINETPAY_API_PASSWORD": bool(os.getenv("CINETPAY_API_PASSWORD")),
        "CINETPAY_BASE_URL": os.getenv("CINETPAY_BASE_URL", "https://api.cinetpay.net"),
        "CINETPAY_SUCCESS_URL": os.getenv("CINETPAY_SUCCESS_URL"),
        "CINETPAY_FAILED_URL": os.getenv("CINETPAY_FAILED_URL"),
        "CINETPAY_NOTIFY_URL": os.getenv("CINETPAY_NOTIFY_URL"),
        "CINETPAY_TEST_CLIENT_EMAIL": os.getenv("CINETPAY_TEST_CLIENT_EMAIL"),
    }
    masked = {
        "api_key_preview": mask_secret(os.getenv("CINETPAY_API_KEY", "")) if os.getenv("CINETPAY_API_KEY") else None,
        "api_password_preview": (
            mask_secret(os.getenv("CINETPAY_API_PASSWORD", ""))
            if os.getenv("CINETPAY_API_PASSWORD")
            else None
        ),
    }
    print_json({"loaded": summary, "masked": masked})
    return 0


def command_auth(_: argparse.Namespace) -> int:
    """Authenticate against the sandbox and print token metadata."""
    client = ensure_client()
    token = client.authenticate(force=True)
    print_json(
        {
            "code": token.code,
            "status": token.status,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "access_token_preview": mask_secret(token.access_token),
        }
    )
    return 0


def command_balances(_: argparse.Namespace) -> int:
    """Retrieve and print sandbox balances."""
    client = ensure_client()
    print_json(client.get_balances())
    return 0


def command_payment(args: argparse.Namespace) -> int:
    """Create a sandbox payment using CLI args and environment defaults."""
    client = ensure_client()
    payment = client.create_payment(
        PaymentRequest(
            currency=args.currency,
            payment_method=args.payment_method,
            merchant_transaction_id=args.merchant_transaction_id or build_transaction_id("pay"),
            amount=args.amount,
            lang=args.lang,
            designation=args.designation,
            client_email=args.client_email or os.getenv("CINETPAY_TEST_CLIENT_EMAIL", "sandbox@example.com"),
            client_first_name=args.client_first_name,
            client_last_name=args.client_last_name,
            client_phone_number=args.client_phone,
            success_url=ensure_url("success_url", args.success_url, "CINETPAY_SUCCESS_URL"),
            failed_url=ensure_url("failed_url", args.failed_url, "CINETPAY_FAILED_URL"),
            notify_url=ensure_url("notify_url", args.notify_url, "CINETPAY_NOTIFY_URL"),
            direct_pay=args.direct_pay,
            otp_code=args.otp_code,
        )
    )
    print_json(payment)
    return 0


def command_payment_status(args: argparse.Namespace) -> int:
    """Fetch and print the status of an existing payment."""
    client = ensure_client()
    print_json(client.get_payment_status(args.identifier))
    return 0


def command_transfer(args: argparse.Namespace) -> int:
    """Create a sandbox transfer using CLI args and environment defaults."""
    client = ensure_client()
    transfer = client.create_transfer(
        TransferRequest(
            currency=args.currency,
            payment_method=args.payment_method,
            merchant_transaction_id=args.merchant_transaction_id or build_transaction_id("trf"),
            amount=args.amount,
            phone_number=args.phone_number,
            reason=args.reason,
            notify_url=ensure_url("notify_url", args.notify_url, "CINETPAY_NOTIFY_URL"),
        )
    )
    print_json(transfer)
    return 0


def command_transfer_status(args: argparse.Namespace) -> int:
    """Fetch and print the status of an existing transfer."""
    client = ensure_client()
    print_json(client.get_transfer_status(args.transaction_id))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Manual sandbox tools for exercising the CinetPay SDK."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    env_check = subparsers.add_parser("env-check", help="Validate local sandbox environment configuration.")
    env_check.set_defaults(handler=command_env_check)

    auth = subparsers.add_parser("auth", help="Authenticate against the sandbox.")
    auth.set_defaults(handler=command_auth)

    balances = subparsers.add_parser("balances", help="Fetch merchant balances.")
    balances.set_defaults(handler=command_balances)

    payment = subparsers.add_parser("payment", help="Create a sandbox payment.")
    payment.add_argument("--currency", default="XOF")
    payment.add_argument("--payment-method", default="OM")
    payment.add_argument("--merchant-transaction-id")
    payment.add_argument("--amount", type=int, default=100)
    payment.add_argument("--lang", default="fr", choices=["fr", "en"])
    payment.add_argument("--designation", default="Sandbox test payment")
    payment.add_argument("--client-email")
    payment.add_argument("--client-first-name", default="Sandbox")
    payment.add_argument("--client-last-name", default="Tester")
    payment.add_argument("--client-phone", default="+2250707070700")
    payment.add_argument("--success-url")
    payment.add_argument("--failed-url")
    payment.add_argument("--notify-url")
    payment.add_argument("--direct-pay", action="store_true")
    payment.add_argument("--otp-code")
    payment.set_defaults(handler=command_payment)

    payment_status = subparsers.add_parser("payment-status", help="Fetch payment status.")
    payment_status.add_argument("--identifier", required=True)
    payment_status.set_defaults(handler=command_payment_status)

    transfer = subparsers.add_parser("transfer", help="Create a sandbox transfer.")
    transfer.add_argument("--currency", default="XOF")
    transfer.add_argument("--payment-method", default="OM_CI")
    transfer.add_argument("--merchant-transaction-id")
    transfer.add_argument("--amount", type=int, default=100)
    transfer.add_argument("--phone-number", default="+2250707000001")
    transfer.add_argument("--reason", default="Sandbox transfer")
    transfer.add_argument("--notify-url")
    transfer.set_defaults(handler=command_transfer)

    transfer_status = subparsers.add_parser("transfer-status", help="Fetch transfer status.")
    transfer_status.add_argument("--transaction-id", required=True)
    transfer_status.set_defaults(handler=command_transfer_status)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    """CLI entry point for manual sandbox testing."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
