"""High-level client for interacting with the CinetPay API.

`CinetPayClient` owns authentication, request orchestration, error mapping, and
conversion from raw API dictionaries into typed repository models. The goal is
to give application code a small surface that looks stable and intention-driven
even if the underlying API uses several response shapes.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import quote

from .exceptions import APIError, AuthenticationError, ValidationError
from .models import (
    AccessToken,
    BalanceResponse,
    NotificationPayload,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusResponse,
    TransferRequest,
    TransferResponse,
)
from .transport import Transport, UrllibTransport

SANDBOX_BASE_URL = "https://api.cinetpay.net"

_AUTH_ERROR_CODES = {1002, 1003, 1005}
_VALIDATION_ERROR_CODES = {1004}
_ERROR_CODES = {-1, 404, 1002, 1003, 1004, 1005, 2011}


class CinetPayClient:
    """Synchronous client for the CinetPay API.

    The client lazily authenticates on the first protected request, stores the
    bearer token in memory, retries once on `EXPIRED_TOKEN`, and exposes typed
    methods for the currently supported CinetPay endpoints.
    """

    def __init__(
        self,
        api_key: str,
        api_password: str,
        *,
        base_url: str = SANDBOX_BASE_URL,
        timeout: float = 30.0,
        transport: Optional[Transport] = None,
    ) -> None:
        """Create a client instance.

        Args:
            api_key: CinetPay account key.
            api_password: CinetPay account password.
            base_url: API base URL. Defaults to the sandbox endpoint.
            timeout: Request timeout in seconds for each HTTP call.
            transport: Optional custom transport implementing the repository
                transport protocol. Mainly useful for tests or advanced runtime
                integration.
        """
        if not api_key:
            raise ValueError("api_key is required")
        if not api_password:
            raise ValueError("api_password is required")

        self.api_key = api_key
        self.api_password = api_password
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or UrllibTransport()
        self._access_token: Optional[str] = None
        self._token_type: str = "Bearer"

    @classmethod
    def from_env(
        cls,
        *,
        api_key_var: str = "CINETPAY_API_KEY",
        api_password_var: str = "CINETPAY_API_PASSWORD",
        base_url_var: str = "CINETPAY_BASE_URL",
        timeout: float = 30.0,
        transport: Optional[Transport] = None,
    ) -> "CinetPayClient":
        """Create a client from environment variables.

        This is the safest default for application code because it keeps secrets
        out of source files and mirrors how the CinetPay documentation recommends
        storing credentials.
        """
        api_key = os.getenv(api_key_var)
        api_password = os.getenv(api_password_var)
        base_url = os.getenv(base_url_var, SANDBOX_BASE_URL)

        if not api_key:
            raise ValueError(f"Environment variable {api_key_var} is missing")
        if not api_password:
            raise ValueError(f"Environment variable {api_password_var} is missing")

        return cls(
            api_key=api_key,
            api_password=api_password,
            base_url=base_url,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> "CinetPayClient":
        """Support usage as a context manager."""
        return self

    def __exit__(self, exc_type: Any, exc: Any, exc_tb: Any) -> None:
        """Close transport resources when leaving a context manager block."""
        self.close()

    def close(self) -> None:
        """Close the underlying transport."""
        self._transport.close()

    def authenticate(self, *, force: bool = False) -> AccessToken:
        """Authenticate against the OAuth login endpoint.

        Args:
            force: When `True`, always request a fresh token even if the client
                already holds one.

        Returns:
            The access token payload returned by CinetPay.
        """
        if self._access_token and not force:
            return AccessToken(
                code=200,
                status="OK",
                access_token=self._access_token,
                token_type=self._token_type,
                expires_in=None,
            )

        payload = self._request(
            "POST",
            "/v1/oauth/login",
            json_data={
                "api_key": self.api_key,
                "api_password": self.api_password,
            },
            auth=False,
            allow_retry=False,
        )
        token = AccessToken.from_dict(payload)
        if not token.access_token:
            raise AuthenticationError(
                "CinetPay did not return an access token",
                code=token.code,
                status=token.status,
                payload=token.raw,
            )

        self._access_token = token.access_token
        self._token_type = self._format_token_type(token.token_type)
        return token

    def create_payment(self, payment: Union[PaymentRequest, Mapping[str, Any]]) -> PaymentResponse:
        """Initialize a payment and return the typed API response.

        The method accepts either a `PaymentRequest` instance or a plain mapping
        that can be converted into one.
        """
        request = payment if isinstance(payment, PaymentRequest) else PaymentRequest(**dict(payment))
        payload = self._request("POST", "/v1/payment", json_data=request.to_payload())
        return PaymentResponse.from_dict(payload)

    def get_payment_status(self, identifier: str) -> PaymentStatusResponse:
        """Fetch the current status of a payment by identifier.

        The repository contract assumes CinetPay accepts a payment token,
        transaction id, or merchant transaction id in this path segment.
        """
        if not identifier:
            raise ValueError("identifier is required")
        payload = self._request("GET", f"/v1/payment/{quote(identifier, safe='')}")
        return PaymentStatusResponse.from_dict(payload)

    def create_transfer(self, transfer: Union[TransferRequest, Mapping[str, Any]]) -> TransferResponse:
        """Create a transfer and return the typed API response."""
        request = transfer if isinstance(transfer, TransferRequest) else TransferRequest(**dict(transfer))
        payload = self._request("POST", "/v1/transfer", json_data=request.to_payload())
        return TransferResponse.from_dict(payload)

    def get_transfer_status(self, transaction_id: str) -> TransferResponse:
        """Fetch the current status of a transfer by transaction id."""
        if not transaction_id:
            raise ValueError("transaction_id is required")
        payload = self._request("GET", f"/v1/transfer/{quote(transaction_id, safe='')}")
        return TransferResponse.from_dict(payload)

    def get_balances(self) -> BalanceResponse:
        """Retrieve the merchant balance payload from CinetPay."""
        payload = self._request("GET", "/v1/balances")
        return BalanceResponse.from_dict(payload)

    @staticmethod
    def parse_notification(payload: Mapping[str, Any]) -> NotificationPayload:
        """Convert a webhook payload into a typed notification model."""
        return NotificationPayload.from_dict(payload)

    @staticmethod
    def validate_notification(payload: Mapping[str, Any], expected_notify_token: str) -> bool:
        """Validate a received notification against a stored `notify_token`."""
        notification = NotificationPayload.from_dict(payload)
        return bool(notification.notify_token and notification.notify_token == expected_notify_token)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: Optional[Dict[str, Any]] = None,
        auth: bool = True,
        allow_retry: bool = True,
    ) -> Dict[str, Any]:
        """Execute one API request and return the decoded response body.

        This internal helper centralizes bearer-token injection, lazy
        authentication, the single automatic retry on `1003 EXPIRED_TOKEN`, and
        repository-specific error mapping.
        """
        if auth and not self._access_token:
            self.authenticate()

        headers = {"Accept": "application/json"}
        if json_data is not None:
            headers["Content-Type"] = "application/json"
        if auth and self._access_token:
            headers["Authorization"] = f"{self._token_type} {self._access_token}"

        response = self._transport.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=headers,
            json_data=json_data,
            timeout=self.timeout,
        )
        payload = dict(response.json_body)
        code = self._coerce_code(payload)

        if code == 1003 and auth and allow_retry:
            # The sandbox contract says an expired token can be recovered by
            # logging in again. Restrict the retry to one round to avoid loops.
            self.authenticate(force=True)
            return self._request(
                method,
                path,
                json_data=json_data,
                auth=auth,
                allow_retry=False,
            )

        if response.status_code >= 400 or code in _ERROR_CODES:
            raise self._build_error(payload, response.status_code)

        return payload

    @staticmethod
    def _format_token_type(token_type: str) -> str:
        """Normalize the token type to the canonical Authorization format."""
        normalized = (token_type or "bearer").strip()
        if normalized.lower() == "bearer":
            return "Bearer"
        return normalized

    @staticmethod
    def _coerce_code(payload: Mapping[str, Any]) -> Optional[int]:
        """Extract the API `code` field as an integer when possible."""
        value = payload.get("code")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_error(payload: Mapping[str, Any], http_status: int) -> APIError:
        """Map a raw failing payload to the most specific SDK exception."""
        code = CinetPayClient._coerce_code(payload)
        status = payload.get("status")
        message = (
            payload.get("message")
            or payload.get("detail")
            or payload.get("title")
            or payload.get("error")
            or (str(status) if status is not None else None)
            or f"CinetPay API request failed with HTTP {http_status}"
        )
        if code in _AUTH_ERROR_CODES:
            return AuthenticationError(
                message,
                code=code,
                status=status,
                http_status=http_status,
                payload=dict(payload),
            )
        if code in _VALIDATION_ERROR_CODES or http_status == 422:
            return ValidationError(
                message,
                code=code,
                status=status,
                http_status=http_status,
                payload=dict(payload),
            )
        return APIError(
            message,
            code=code,
            status=status,
            http_status=http_status,
            payload=dict(payload),
        )
