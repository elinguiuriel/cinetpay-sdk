"""Public package surface for the CinetPay Python SDK.

Applications are expected to import from this module rather than from the
individual implementation modules. This keeps the user-facing API explicit and
lets the repository evolve internally without forcing downstream projects to
track file-level refactors.
"""

from .client import CinetPayClient, SANDBOX_BASE_URL
from .exceptions import APIError, AuthenticationError, CinetPayError, NetworkError, ValidationError
from .models import (
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
)

__all__ = [
    "APIError",
    "AccessToken",
    "AuthenticationError",
    "BalanceResponse",
    "CinetPayClient",
    "CinetPayError",
    "NetworkError",
    "NotificationPayload",
    "PaymentDetails",
    "PaymentRequest",
    "PaymentResponse",
    "PaymentStatusResponse",
    "SANDBOX_BASE_URL",
    "TransferRequest",
    "TransferResponse",
    "UserInfo",
    "ValidationError",
]

__version__ = "0.1.0"
