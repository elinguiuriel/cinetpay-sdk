"""End-to-end example showing how an application can use the SDK.

This file is intentionally written as copyable application code rather than as a
test utility. It demonstrates the main classes that a project will use after
installing the SDK from GitHub or from a local checkout.
"""

from __future__ import annotations

from cinetpay_sdk import (
    APIError,
    CinetPayClient,
    NetworkError,
    PaymentRequest,
    TransferRequest,
)


def authenticate_client() -> CinetPayClient:
    """Create a client from environment variables and authenticate it."""
    client = CinetPayClient.from_env()
    token = client.authenticate()
    print("Authenticated:", token.status, "expires_in=", token.expires_in)
    return client


def create_web_payment(client: CinetPayClient) -> None:
    """Initialize a standard web payment and print the redirect URL."""
    payment = client.create_payment(
        PaymentRequest(
            currency="XOF",
            payment_method="OM",
            merchant_transaction_id="ORDER-1001",
            amount=1000,
            lang="fr",
            designation="Paiement exemple",
            client_email="client@example.com",
            client_first_name="Jean",
            client_last_name="Doe",
            client_phone_number="+2250707070700",
            success_url="https://merchant.example/payment/success",
            failed_url="https://merchant.example/payment/failed",
            notify_url="https://merchant.example/payment/notify",
        )
    )

    print("Payment token:", payment.payment_token)
    print("Payment status:", payment.details.status if payment.details else payment.status)

    if payment.should_redirect:
        print("Redirect user to:", payment.payment_url)


def check_payment_status(client: CinetPayClient, identifier: str) -> None:
    """Fetch and display the current status of an existing payment."""
    status = client.get_payment_status(identifier)
    print("Payment status:", status.status)
    print("Payment user:", status.user)


def create_transfer(client: CinetPayClient) -> None:
    """Initialize a transfer and print the resulting transaction id."""
    transfer = client.create_transfer(
        TransferRequest(
            currency="XOF",
            payment_method="OM_CI",
            merchant_transaction_id="TRANSFER-1001",
            amount=100,
            phone_number="+2250707000001",
            reason="Rechargement de compte",
            notify_url="https://merchant.example/transfer/notify",
        )
    )
    print("Transfer status:", transfer.status)
    print("Transfer transaction:", transfer.transaction_id)


def show_balances(client: CinetPayClient) -> None:
    """Print the balance payload returned by CinetPay."""
    balances = client.get_balances()
    print("Balances:", balances.balances)


def main() -> int:
    """Run the example with basic error handling."""
    try:
        client = authenticate_client()
        show_balances(client)
        create_web_payment(client)
        # You would usually call `check_payment_status()` later with a real
        # identifier returned by `create_web_payment()`.
        create_transfer(client)
    except NetworkError as exc:
        print("Network error:", exc)
        return 1
    except APIError as exc:
        print("API error:", exc.code, exc.status, exc.payload)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
