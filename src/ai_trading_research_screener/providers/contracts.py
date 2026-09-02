"""Stable internal records shared by provider adapters and application services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Generic, TypeVar
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


UTC = timezone.utc
US_EASTERN = ZoneInfo("America/New_York")
T = TypeVar("T")


class ContractValidationError(ValueError):
    """Raised when a normalized record violates the internal contract."""


class DataState(StrEnum):
    """Freshness or availability state assigned by deterministic adapter code."""

    CURRENT = "current"
    MISSING = "missing"
    DELAYED = "delayed"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class ProviderErrorKind(StrEnum):
    AUTHENTICATION = "authentication"
    MALFORMED_RESPONSE = "malformed_response"
    RATE_LIMITED = "rate_limited"
    TRANSPORT = "transport"
    UNAVAILABLE = "unavailable"


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ContractValidationError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _non_negative(value: Decimal | int | None, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, Decimal) and not value.is_finite():
        raise ContractValidationError(f"{field_name} must be finite")
    if isinstance(value, bool) or value < 0:
        raise ContractValidationError(f"{field_name} must be non-negative")


def _decimal_or_none(value: object, field_name: str) -> Decimal | None:
    if value is not None and not isinstance(value, Decimal):
        raise ContractValidationError(f"{field_name} must be a Decimal")
    return value


def _integer_or_none(value: object, field_name: str) -> int | None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise ContractValidationError(f"{field_name} must be an integer")
    return value


def _validate_state(state: DataState, reason: str | None) -> None:
    if not isinstance(state, DataState):
        raise ContractValidationError("state must be a DataState")
    if state is not DataState.CURRENT and not (
        isinstance(reason, str) and reason.strip()
    ):
        raise ContractValidationError("non-current data requires a reason")


def as_eastern(value: datetime) -> datetime:
    """Render an aware instant in DST-aware US Eastern time."""

    return _utc(value, "timestamp").astimezone(US_EASTERN)


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Non-secret provider identity safe to expose outside an adapter."""

    name: str
    environment: str = "demo"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _non_empty(self.name, "provider name"))
        object.__setattr__(
            self, "environment", _non_empty(self.environment, "provider environment")
        )


@dataclass(frozen=True, slots=True)
class RateLimit:
    """Provider-reported request budget; absent fields mean not reported."""

    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None
    retry_after: timedelta | None = None

    def __post_init__(self) -> None:
        for field_name in ("limit", "remaining"):
            _integer_or_none(getattr(self, field_name), f"rate-limit {field_name}")
        _non_negative(self.limit, "rate-limit limit")
        _non_negative(self.remaining, "rate-limit remaining")
        if self.limit is not None and self.remaining is not None and self.remaining > self.limit:
            raise ContractValidationError("rate-limit remaining cannot exceed limit")
        if self.reset_at is not None:
            object.__setattr__(self, "reset_at", _utc(self.reset_at, "reset_at"))
        if self.retry_after is not None:
            if not isinstance(self.retry_after, timedelta):
                raise ContractValidationError("retry_after must be a timedelta")
            if self.retry_after < timedelta(0):
                raise ContractValidationError("retry_after must be non-negative")


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    market_timestamp: datetime
    retrieved_at: datetime
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal | None = None
    volume: int | None = None
    state: DataState = DataState.CURRENT
    state_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _non_empty(self.symbol, "symbol").upper())
        object.__setattr__(self, "market_timestamp", _utc(self.market_timestamp, "market_timestamp"))
        object.__setattr__(self, "retrieved_at", _utc(self.retrieved_at, "retrieved_at"))
        for field_name in ("bid", "ask", "last"):
            _decimal_or_none(getattr(self, field_name), field_name)
            _non_negative(getattr(self, field_name), field_name)
        _integer_or_none(self.volume, "volume")
        _non_negative(self.volume, "volume")
        if all(value is None for value in (self.bid, self.ask, self.last)):
            raise ContractValidationError("a quote requires bid, ask, or last")
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ContractValidationError("bid cannot exceed ask")
        _validate_state(self.state, self.state_reason)


@dataclass(frozen=True, slots=True)
class Bar:
    symbol: str
    interval: str
    market_timestamp: datetime
    retrieved_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    state: DataState = DataState.CURRENT
    state_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _non_empty(self.symbol, "symbol").upper())
        object.__setattr__(self, "interval", _non_empty(self.interval, "interval"))
        object.__setattr__(self, "market_timestamp", _utc(self.market_timestamp, "market_timestamp"))
        object.__setattr__(self, "retrieved_at", _utc(self.retrieved_at, "retrieved_at"))
        for field_name in ("open", "high", "low", "close"):
            if not isinstance(getattr(self, field_name), Decimal):
                raise ContractValidationError(f"{field_name} must be a Decimal")
            _non_negative(getattr(self, field_name), field_name)
        _integer_or_none(self.volume, "volume")
        _non_negative(self.volume, "volume")
        if self.high < max(self.open, self.close, self.low):
            raise ContractValidationError("high must be the greatest OHLC value")
        if self.low > min(self.open, self.close, self.high):
            raise ContractValidationError("low must be the least OHLC value")
        _validate_state(self.state, self.state_reason)


@dataclass(frozen=True, slots=True)
class NewsRecord:
    article_id: str
    headline: str
    publisher: str
    source_url: str
    published_at: datetime
    retrieved_at: datetime
    symbols: tuple[str, ...] = ()
    sectors: tuple[str, ...] = ()
    summary: str | None = None
    state: DataState = DataState.CURRENT
    state_reason: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("article_id", "headline", "publisher"):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))
        parsed_url = urlparse(self.source_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ContractValidationError("source_url must be an absolute HTTP(S) URL")
        object.__setattr__(self, "published_at", _utc(self.published_at, "published_at"))
        object.__setattr__(self, "retrieved_at", _utc(self.retrieved_at, "retrieved_at"))
        if not all(isinstance(symbol, str) and symbol.strip() for symbol in self.symbols):
            raise ContractValidationError("symbols must be non-empty strings")
        object.__setattr__(self, "symbols", tuple(symbol.upper() for symbol in self.symbols))
        if not all(isinstance(sector, str) and sector.strip() for sector in self.sectors):
            raise ContractValidationError("sectors must be non-empty strings")
        if self.summary is not None and not isinstance(self.summary, str):
            raise ContractValidationError("summary must be a string when present")
        _validate_state(self.state, self.state_reason)


@dataclass(frozen=True, slots=True)
class FetchResult(Generic[T]):
    """A successful provider call, including a valid empty result."""

    provider: ProviderInfo
    retrieved_at: datetime
    items: tuple[T, ...] = ()
    state: DataState = DataState.CURRENT
    state_reason: str | None = None
    rate_limit: RateLimit | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "retrieved_at", _utc(self.retrieved_at, "retrieved_at"))
        object.__setattr__(self, "items", tuple(self.items))
        _validate_state(self.state, self.state_reason)
        if not self.items and self.state is DataState.CURRENT:
            object.__setattr__(self, "state", DataState.MISSING)
            object.__setattr__(self, "state_reason", "provider returned no matching records")


@dataclass(eq=False)
class ProviderError(RuntimeError):
    """Explicit provider failure; never represents a valid empty result."""

    provider: str
    kind: ProviderErrorKind
    message: str
    retryable: bool = False
    rate_limit: RateLimit | None = None

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, f"{self.provider}: {self.message}")


class ProviderPayloadError(ProviderError):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(provider, ProviderErrorKind.MALFORMED_RESPONSE, message, False)


class RateLimitError(ProviderError):
    def __init__(self, provider: str, message: str, rate_limit: RateLimit) -> None:
        super().__init__(provider, ProviderErrorKind.RATE_LIMITED, message, True, rate_limit)
