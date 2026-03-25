"""Data models used by the CinetPay SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlparse

FINAL_STATUSES = {"SUCCESS", "FAILED"}


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and parsed.netloc)


def _user_from_dict(data: Optional[Mapping[str, Any]]) -> Optional["UserInfo"]:
    if not data:
        return None
    return UserInfo(
        name=data.get("name"),
        email=data.get("email"),
        phone_number=data.get("phone_number"),
    )


def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class UserInfo:
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None


@dataclass(frozen=True)
class AccessToken:
    code: Optional[int]
    status: Optional[str]
    access_token: str
    token_type: str
    expires_in: Optional[int]
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AccessToken":
        return cls(
            code=_as_int(data.get("code")),
            status=data.get("status"),
            access_token=str(data.get("access_token", "")),
            token_type=str(data.get("token_type", "bearer")),
            expires_in=_as_int(data.get("expires_in")),
            raw=dict(data),
        )


@dataclass(frozen=True)
class PaymentDetails:
    code: Optional[int] = None
    status: Optional[str] = None
    message: Optional[str] = None
    must_be_redirected: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]]) -> Optional["PaymentDetails"]:
        if not data:
            return None
        return cls(
            code=_as_int(data.get("code")),
            status=data.get("status"),
            message=data.get("message"),
            must_be_redirected=data.get("must_be_redirected"),
        )

    @property
    def is_final(self) -> bool:
        return bool(self.status in FINAL_STATUSES)


@dataclass(frozen=True)
class PaymentRequest:
    currency: str
    merchant_transaction_id: str
    amount: int
    lang: str
    designation: str
    client_email: str
    client_first_name: str
    client_last_name: str
    success_url: str
    failed_url: str
    notify_url: str
    payment_method: Optional[str] = None
    client_phone_number: Optional[str] = None
    direct_pay: bool = False
    otp_code: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        self._validate()
        payload = {
            "currency": self.currency,
            "payment_method": self.payment_method,
            "merchant_transaction_id": self.merchant_transaction_id,
            "amount": self.amount,
            "lang": self.lang,
            "designation": self.designation,
            "client_email": self.client_email,
            "client_phone_number": self.client_phone_number,
            "client_first_name": self.client_first_name,
            "client_last_name": self.client_last_name,
            "direct_pay": self.direct_pay,
            "otp_code": str(self.otp_code) if self.otp_code is not None else None,
            "success_url": self.success_url,
            "failed_url": self.failed_url,
            "notify_url": self.notify_url,
        }
        return _clean_payload(payload)

    def _validate(self) -> None:
        if not self.currency:
            raise ValueError("currency is required")
        if not self.merchant_transaction_id:
            raise ValueError("merchant_transaction_id is required")
        if len(self.merchant_transaction_id) > 30:
            raise ValueError("merchant_transaction_id must be 30 characters or fewer")
        if self.amount <= 0:
            raise ValueError("amount must be greater than 0")
        if self.lang not in {"fr", "en"}:
            raise ValueError("lang must be 'fr' or 'en'")
        if not self.designation:
            raise ValueError("designation is required")
        if not self.client_email or "@" not in self.client_email:
            raise ValueError("client_email must be a valid email address")
        if not 2 <= len(self.client_first_name) <= 255:
            raise ValueError("client_first_name must contain between 2 and 255 characters")
        if not 2 <= len(self.client_last_name) <= 255:
            raise ValueError("client_last_name must contain between 2 and 255 characters")
        for field_name, url in {
            "success_url": self.success_url,
            "failed_url": self.failed_url,
            "notify_url": self.notify_url,
        }.items():
            if not url:
                raise ValueError(f"{field_name} is required")
            if len(url) > 120:
                raise ValueError(f"{field_name} must be 120 characters or fewer")
            if not _is_valid_url(url):
                raise ValueError(f"{field_name} must be a valid URL")
        if self.direct_pay and not self.client_phone_number:
            raise ValueError("client_phone_number is required when direct_pay=True")
        if self.otp_code is not None:
            otp_code = str(self.otp_code).strip()
            if not otp_code.isdigit():
                raise ValueError("otp_code must contain only digits")
            if not 4 <= len(otp_code) <= 6:
                raise ValueError("otp_code must contain between 4 and 6 digits")


@dataclass(frozen=True)
class PaymentResponse:
    code: Optional[int]
    status: Optional[str]
    payment_token: Optional[str] = None
    notify_token: Optional[str] = None
    transaction_id: Optional[str] = None
    merchant_transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    details: Optional[PaymentDetails] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PaymentResponse":
        return cls(
            code=_as_int(data.get("code")),
            status=data.get("status"),
            payment_token=data.get("payment_token"),
            notify_token=data.get("notify_token"),
            transaction_id=data.get("transaction_id"),
            merchant_transaction_id=data.get("merchant_transaction_id"),
            payment_url=data.get("payment_url"),
            details=PaymentDetails.from_dict(data.get("details")),
            raw=dict(data),
        )

    @property
    def should_redirect(self) -> bool:
        return bool(self.details and self.details.must_be_redirected and self.payment_url)

    @property
    def is_final(self) -> bool:
        if self.details:
            return self.details.is_final
        return bool(self.status in FINAL_STATUSES)


@dataclass(frozen=True)
class PaymentStatusResponse:
    code: Optional[int]
    status: Optional[str]
    merchant_transaction_id: Optional[str] = None
    transaction_id: Optional[str] = None
    user: Optional[UserInfo] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PaymentStatusResponse":
        return cls(
            code=_as_int(data.get("code")),
            status=data.get("status"),
            merchant_transaction_id=data.get("merchant_transaction_id"),
            transaction_id=data.get("transaction_id"),
            user=_user_from_dict(data.get("user")),
            raw=dict(data),
        )

    @property
    def is_final(self) -> bool:
        return bool(self.status in FINAL_STATUSES)


@dataclass(frozen=True)
class TransferRequest:
    currency: str
    payment_method: str
    merchant_transaction_id: str
    amount: int
    phone_number: str
    reason: str
    notify_url: str

    def to_payload(self) -> Dict[str, Any]:
        self._validate()
        return {
            "currency": self.currency,
            "payment_method": self.payment_method,
            "merchant_transaction_id": self.merchant_transaction_id,
            "amount": self.amount,
            "phone_number": self.phone_number,
            "reason": self.reason,
            "notify_url": self.notify_url,
        }

    def _validate(self) -> None:
        if not self.currency:
            raise ValueError("currency is required")
        if not self.payment_method:
            raise ValueError("payment_method is required")
        if not self.merchant_transaction_id:
            raise ValueError("merchant_transaction_id is required")
        if len(self.merchant_transaction_id) > 30:
            raise ValueError("merchant_transaction_id must be 30 characters or fewer")
        if self.amount <= 0:
            raise ValueError("amount must be greater than 0")
        if not self.phone_number:
            raise ValueError("phone_number is required")
        if not self.reason:
            raise ValueError("reason is required")
        if not self.notify_url:
            raise ValueError("notify_url is required")
        if not _is_valid_url(self.notify_url):
            raise ValueError("notify_url must be a valid URL")


@dataclass(frozen=True)
class TransferResponse:
    code: Optional[int]
    status: Optional[str]
    merchant_transaction_id: Optional[str] = None
    transaction_id: Optional[str] = None
    amount: Optional[int] = None
    fee_amount: Optional[int] = None
    user: Optional[UserInfo] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TransferResponse":
        return cls(
            code=_as_int(data.get("code")),
            status=data.get("status"),
            merchant_transaction_id=data.get("merchant_transaction_id"),
            transaction_id=data.get("transaction_id"),
            amount=_as_int(data.get("amount")),
            fee_amount=_as_int(data.get("fee_amount")),
            user=_user_from_dict(data.get("user")),
            raw=dict(data),
        )

    @property
    def is_final(self) -> bool:
        return bool(self.status in FINAL_STATUSES)


@dataclass(frozen=True)
class BalanceResponse:
    code: Optional[int]
    status: Optional[str]
    balances: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BalanceResponse":
        balances = {key: value for key, value in data.items() if key not in {"code", "status"}}
        return cls(
            code=_as_int(data.get("code")),
            status=data.get("status"),
            balances=balances,
            raw=dict(data),
        )


@dataclass(frozen=True)
class NotificationPayload:
    notify_token: str
    merchant_transaction_id: Optional[str] = None
    transaction_id: Optional[str] = None
    user: Optional[UserInfo] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NotificationPayload":
        return cls(
            notify_token=str(data.get("notify_token", "")),
            merchant_transaction_id=data.get("merchant_transaction_id"),
            transaction_id=data.get("transaction_id"),
            user=_user_from_dict(data.get("user")),
            raw=dict(data),
        )
