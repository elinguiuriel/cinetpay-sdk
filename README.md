# CinetPay Python SDK

Minimal Python SDK for the new CinetPay API, based on the sandbox
documentation provided for this repository.

Default sandbox base URL: `https://api.cinetpay.net`

## Harness Engineering

This repository follows a harness-first approach inspired by OpenAI's "Harness
engineering" article:

- the repository stores its operational rules in [AGENTS.md](AGENTS.md)
- the external CinetPay contract is summarized in `docs/cinetpay-sandbox-contract.md`
- critical behaviors are encoded as executable scenarios in `harness/scenarios/`
- the architecture is checked mechanically through structural tests
- a short `python scripts/run_quality.py` loop acts as the main repository gate

Main commands:

```bash
python scripts/run_harness.py
python scripts/run_quality.py
```

Repository sources of truth:

- `AGENTS.md`
- `docs/architecture.md`
- `docs/cinetpay-sandbox-contract.md`
- `harness/scenarios/*.json`

## Features

- OAuth authentication through `POST /v1/oauth/login`
- Web payment initialization through `POST /v1/payment`
- Payment status lookup through `GET /v1/payment/{identifier}`
- Transfer creation through `POST /v1/transfer`
- Transfer status lookup through `GET /v1/transfer/{transaction_id}`
- Balance lookup through `GET /v1/balances`
- Simple `notify_token` notification validation
- Automatic token refresh when the API returns `1003 EXPIRED_TOKEN`

## Installation

From the GitHub repository:

```bash
pip install "git+https://github.com/elinguiuriel/cinetpay-sdk.git"
```

From a specific branch:

```bash
pip install "git+https://github.com/elinguiuriel/cinetpay-sdk.git@main"
```

From a specific commit:

```bash
pip install "git+https://github.com/elinguiuriel/cinetpay-sdk.git@<commit-sha>"
```

From a local clone of the repository:

```bash
pip install .
```

For development:

```bash
pip install -e .[dev]
```

Detailed installation and usage guide for a Python project:

- `docs/installing-from-github.md`
- `examples/basic_usage.py`

## Sandbox Tools

The repository includes a CLI for testing the real CinetPay sandbox without
having to write one-off application scripts each time:

```bash
python scripts/sandbox_cli.py env-check
python scripts/sandbox_cli.py auth
python scripts/sandbox_cli.py balances
```

Examples:

```bash
python scripts/sandbox_cli.py payment \
  --amount 100 \
  --payment-method OM \
  --client-phone +2250707070700 \
  --success-url https://example.com/payment/success \
  --failed-url https://example.com/payment/failed \
  --notify-url https://webhook.site/replace-me
```

```bash
python scripts/sandbox_cli.py transfer \
  --amount 100 \
  --payment-method OM_CI \
  --phone-number +2250707000001 \
  --notify-url https://webhook.site/replace-me
```

Detailed documentation:

- `docs/sandbox-testing.md`
- `docs/secure-credentials.md`

Transport note:

- `api.cinetpay.net` currently blocks the default `Python-urllib/x.y`
  signature through Cloudflare `Error 1010`
- the SDK therefore sends a dedicated default `User-Agent` so the standard
  transport works against the sandbox

## SDK Surface

The package primarily exposes:

- `CinetPayClient`
- `PaymentRequest`
- `TransferRequest`
- `PaymentResponse`
- `PaymentStatusResponse`
- `TransferResponse`
- `BalanceResponse`

## Installing In A Python Project

Recommended flow:

1. create a virtual environment for your project
2. install the SDK from GitHub
3. configure `CINETPAY_API_KEY` and `CINETPAY_API_PASSWORD`
4. import `cinetpay_sdk` in your application code

Complete example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "git+https://github.com/elinguiuriel/cinetpay-sdk.git@main"
```

Then:

```bash
export CINETPAY_API_KEY='your-account-key'
export CINETPAY_API_PASSWORD='your-account-password'
export CINETPAY_BASE_URL='https://api.cinetpay.net'
```

Verification:

```bash
python -c "from cinetpay_sdk import CinetPayClient; print(CinetPayClient)"
```

## Quick Example

```python
from cinetpay_sdk import CinetPayClient, PaymentRequest

client = CinetPayClient(
    api_key="your-account-key",
    api_password="your-account-password",
)

payment = client.create_payment(
    PaymentRequest(
        currency="XOF",
        payment_method="OM",
        merchant_transaction_id="ORDER-1001",
        amount=1000,
        lang="fr",
        designation="Subscription payment",
        client_email="client@example.com",
        client_first_name="Jean",
        client_last_name="Doe",
        client_phone_number="+2250707070700",
        success_url="https://merchant.test/payment/success",
        failed_url="https://merchant.test/payment/failed",
        notify_url="https://merchant.test/payment/notify",
    )
)

print(payment.payment_token)
print(payment.payment_url)
print(payment.details.status if payment.details else None)

if payment.should_redirect:
    print("Redirect the user to:", payment.payment_url)
```

## Using The Classes In A Python Program

Minimal authentication example:

```python
from cinetpay_sdk import CinetPayClient

client = CinetPayClient.from_env()
token = client.authenticate()

print(token.status)
print(token.expires_in)
```

For a more complete application-style example:

- `examples/basic_usage.py`

## Authentication

The client authenticates automatically on the first protected request.

You can also force authentication:

```python
token = client.authenticate()
print(token.access_token)
```

You can also load credentials from environment variables:

```python
from cinetpay_sdk import CinetPayClient

client = CinetPayClient.from_env()
```

Variables used:

- `CINETPAY_API_KEY`
- `CINETPAY_API_PASSWORD`
- `CINETPAY_BASE_URL` optional

## Secure Credential Setup

Never hardcode CinetPay credentials in:

- source code
- the `README`
- versioned configuration files
- committed CI workflow files

Recommended local setup:

```bash
cp .env.example .env
chmod 600 .env
```

Then fill in the real values in `.env`. The repository already ignores that
file.

You can then run:

```bash
python scripts/sandbox_cli.py env-check
```

For the full procedure:

- `docs/secure-credentials.md`

## Web Payments

```python
status = client.get_payment_status("payment-token-or-transaction-id")
print(status.status)
```

The provided documentation says the accepted identifier can be:

- `payment_token`
- `transaction_id`
- `merchant_transaction_id`

The SDK simply passes that value into the `GET /v1/payment/{identifier}` URL.

## Direct Pay

The SDK lets you enable `direct_pay=True`. In that case,
`client_phone_number` becomes mandatory.

```python
payment = client.create_payment(
    PaymentRequest(
        currency="XOF",
        payment_method="OM",
        merchant_transaction_id="ORDER-1002",
        amount=500,
        lang="fr",
        designation="Direct payment",
        client_email="client@example.com",
        client_first_name="Jean",
        client_last_name="Doe",
        client_phone_number="+2250707070701",
        success_url="https://merchant.test/success",
        failed_url="https://merchant.test/failed",
        notify_url="https://merchant.test/notify",
        direct_pay=True,
        otp_code="1234",
    )
)

if payment.details:
    print(payment.details.status)
    print(payment.details.message)
```

## Transfers

```python
from cinetpay_sdk import TransferRequest

transfer = client.create_transfer(
    TransferRequest(
        currency="XOF",
        payment_method="OM_CI",
        merchant_transaction_id="TRANSFER-1001",
        amount=100,
        phone_number="+2250707000001",
        reason="Account top-up",
        notify_url="https://merchant.test/transfer/notify",
    )
)

print(transfer.status)
print(transfer.transaction_id)
```

Then:

```python
transfer_status = client.get_transfer_status(transfer.transaction_id)
print(transfer_status.status)
```

## Balances

The exact response shape was not fully documented in the provided material, so
the SDK returns:

- `code`
- `status`
- `balances`: every other key from the response

```python
balances = client.get_balances()
print(balances.status)
print(balances.balances)
```

## Notifications

Example of validating a received `notify_token` in your endpoint:

```python
from cinetpay_sdk import CinetPayClient

payload = {
    "notify_token": "4bbd93ce1824ca005b8df92069a6b56cca005b8",
    "merchant_transaction_id": "63e0fe766f390",
    "transaction_id": "50901a80c84b4edcb4f50ae864bfa7c5",
    "user": {
        "name": "Jaqn HGHAR",
        "email": "jaqen@gmail.com",
        "phone_number": "+2250700356615",
    },
}

if CinetPayClient.validate_notification(payload, expected_notify_token="4bbd93ce1824ca005b8df92069a6b56cca005b8"):
    notification = CinetPayClient.parse_notification(payload)
    payment_status = client.get_payment_status(notification.transaction_id)
```

Recommended server-side flow:

- store the `notify_token` returned during payment initialization
- compare it with the token received in the POST notification
- then confirm the final status with the CinetPay API

## Exceptions

The SDK exposes:

- `CinetPayError`
- `APIError`
- `AuthenticationError`
- `ValidationError`
- `NetworkError`

Example:

```python
from cinetpay_sdk import APIError, CinetPayClient, NetworkError

try:
    balances = client.get_balances()
except NetworkError as exc:
    print("Network error:", exc)
except APIError as exc:
    print("API error:", exc.code, exc.status, exc.payload)
```

## Sandbox Test Numbers

According to the provided documentation:

- Ivory Coast immediate success: `+2250707070700`
- Ivory Coast pending then success: `+2250707070701`
- Ivory Coast immediate failure: `+2250707070703`
- Ivory Coast pending then failure: `+2250707070704`
- Ivory Coast infinite pending: `+2250707070706`
- Transfer sandbox number: `+2250707000001`

## Assumptions In This First Version

- The bearer token is sent in the `Authorization: Bearer <token>` header
- The `GET /v1/payment/{identifier}` endpoint accepts the identifiers described
  in the provided documentation
- Because `GET /v1/balances` was not fully specified in the excerpt, the SDK
  keeps that payload shape flexible

## Local Development

```bash
python scripts/run_quality.py
```

If you only want to run the tests:

```bash
python -m unittest discover -s tests -v
```
