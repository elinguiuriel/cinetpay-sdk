# Installing And Using The SDK From GitHub

This document explains how to install the SDK directly from the GitHub
repository and how to use its main classes inside a regular Python project.

Repository URL:

- `https://github.com/elinguiuriel/cinetpay-sdk`

Import name inside Python:

- `cinetpay_sdk`

Package name for `pip` direct URL installs:

- `cinetpay-sdk`

## 1. Create A Virtual Environment In Your Project

From your application directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 2. Install Directly From GitHub

Latest branch state:

```bash
pip install "git+https://github.com/elinguiuriel/cinetpay-sdk.git"
```

Specific branch:

```bash
pip install "git+https://github.com/elinguiuriel/cinetpay-sdk.git@main"
```

Specific commit:

```bash
pip install "git+https://github.com/elinguiuriel/cinetpay-sdk.git@d22f0a7"
```

Using `@<commit>` is the safest option for production because your project keeps
using the exact reviewed revision.

## 3. Add It To Your Dependency Files

### `requirements.txt`

```txt
cinetpay-sdk @ git+https://github.com/elinguiuriel/cinetpay-sdk.git@main
```

Then:

```bash
pip install -r requirements.txt
```

### `pyproject.toml`

```toml
[project]
dependencies = [
  "cinetpay-sdk @ git+https://github.com/elinguiuriel/cinetpay-sdk.git@main",
]
```

## 4. Configure Credentials Securely

The SDK reads:

- `CINETPAY_API_KEY`
- `CINETPAY_API_PASSWORD`
- `CINETPAY_BASE_URL` optional

Recommended local setup:

```bash
export CINETPAY_API_KEY='your-account-key'
export CINETPAY_API_PASSWORD='your-account-password'
export CINETPAY_BASE_URL='https://api.cinetpay.net'
```

Or manage them with your secret mechanism or `.env` loader in your application.

For the secure setup details, read:

- `docs/secure-credentials.md`

## 5. Verify The Installation

```bash
python -c "from cinetpay_sdk import CinetPayClient; print(CinetPayClient)"
```

If this prints the class path without error, the installation is correct.

## 6. Use The Main Classes In Python

### Minimal Authentication Example

```python
from cinetpay_sdk import CinetPayClient

client = CinetPayClient.from_env()
token = client.authenticate()

print(token.status)
print(token.expires_in)
```

### Create A Web Payment

```python
from cinetpay_sdk import CinetPayClient, PaymentRequest

client = CinetPayClient.from_env()

payment = client.create_payment(
    PaymentRequest(
        currency="XOF",
        payment_method="OM",
        merchant_transaction_id="ORDER-1001",
        amount=1000,
        lang="fr",
        designation="Paiement abonnement",
        client_email="client@example.com",
        client_first_name="Jean",
        client_last_name="Doe",
        client_phone_number="+2250707070700",
        success_url="https://merchant.example/success",
        failed_url="https://merchant.example/failed",
        notify_url="https://merchant.example/notify",
    )
)

print(payment.payment_token)
print(payment.payment_url)

if payment.should_redirect:
    print("Redirect the user to:", payment.payment_url)
```

### Check Payment Status

```python
status = client.get_payment_status("payment-token-or-transaction-id")
print(status.status)
print(status.user)
```

### Create A Transfer

```python
from cinetpay_sdk import CinetPayClient, TransferRequest

client = CinetPayClient.from_env()

transfer = client.create_transfer(
    TransferRequest(
        currency="XOF",
        payment_method="OM_CI",
        merchant_transaction_id="TRANSFER-1001",
        amount=100,
        phone_number="+2250707000001",
        reason="Rechargement de compte",
        notify_url="https://merchant.example/transfer-notify",
    )
)

print(transfer.status)
print(transfer.transaction_id)
```

### Check Transfer Status

```python
status = client.get_transfer_status("transaction-id")
print(status.status)
print(status.amount)
```

### Read Balances

```python
balances = client.get_balances()
print(balances.status)
print(balances.balances)
```

### Validate A Notification

```python
from cinetpay_sdk import CinetPayClient

payload = {
    "notify_token": "notify-token-from-cinetpay",
    "merchant_transaction_id": "ORDER-1001",
    "transaction_id": "transaction-id",
}

expected_notify_token = "the-token-you-stored-when-initializing-the-payment"

if CinetPayClient.validate_notification(payload, expected_notify_token):
    notification = CinetPayClient.parse_notification(payload)
    print(notification.transaction_id)
```

## 7. Error Handling Pattern

```python
from cinetpay_sdk import APIError, CinetPayClient, NetworkError, PaymentRequest

client = CinetPayClient.from_env()

try:
    payment = client.create_payment(
        PaymentRequest(
            currency="XOF",
            payment_method="OM",
            merchant_transaction_id="ORDER-1001",
            amount=1000,
            lang="fr",
            designation="Paiement test",
            client_email="client@example.com",
            client_first_name="Jean",
            client_last_name="Doe",
            client_phone_number="+2250707070700",
            success_url="https://merchant.example/success",
            failed_url="https://merchant.example/failed",
            notify_url="https://merchant.example/notify",
        )
    )
except NetworkError as exc:
    print("Network error:", exc)
except APIError as exc:
    print("API error:", exc.code, exc.status, exc.payload)
```

## 8. Example File In This Repository

For a longer ready-to-copy example, see:

- `examples/basic_usage.py`

## 9. Important Notes

- The SDK targets Python `>= 3.9`
- The default base URL is the sandbox URL
- The SDK import path is `cinetpay_sdk`, not `cinetpay-sdk`
- The repository currently has no dependency on third-party HTTP libraries
