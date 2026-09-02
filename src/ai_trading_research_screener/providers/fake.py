"""Synthetic provider adapter for tests and local demonstrations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from .contracts import (
    Bar,
    DataState,
    FetchResult,
    NewsRecord,
    ProviderError,
    ProviderInfo,
    ProviderPayloadError,
    Quote,
)


class FakeProvider:
    """Converts synthetic raw dictionaries into the same records as live adapters.

    ``failure`` is test-only fault injection. Any future credential or provider SDK
    configuration belongs in a live adapter's private state, never in these ports.
    """

    def __init__(
        self,
        *,
        quotes: Iterable[Mapping[str, Any]] = (),
        bars: Iterable[Mapping[str, Any]] = (),
        news: Iterable[Mapping[str, Any]] = (),
        failure: ProviderError | None = None,
        now: datetime | None = None,
    ) -> None:
        self._raw_quotes = tuple(quotes)
        self._raw_bars = tuple(bars)
        self._raw_news = tuple(news)
        self._failure = failure
        self._now = now or datetime.now(timezone.utc)
        self._info = ProviderInfo("synthetic-demo")

    @property
    def info(self) -> ProviderInfo:
        return self._info

    def get_quotes(self, symbols: tuple[str, ...]) -> FetchResult[Quote]:
        self._raise_failure()
        wanted = {symbol.upper() for symbol in symbols}
        items = tuple(item for item in map(self._quote, self._raw_quotes) if item.symbol in wanted)
        return self._result(items)

    def get_intraday_bars(
        self, symbols: tuple[str, ...], start: datetime, end: datetime, interval: str
    ) -> FetchResult[Bar]:
        return self._bars(symbols, start, end, interval)

    def get_historical_bars(
        self, symbols: tuple[str, ...], start: datetime, end: datetime, interval: str
    ) -> FetchResult[Bar]:
        return self._bars(symbols, start, end, interval)

    def get_company_news(
        self, symbols: tuple[str, ...], since: datetime | None = None
    ) -> FetchResult[NewsRecord]:
        self._raise_failure()
        wanted = {symbol.upper() for symbol in symbols}
        items = tuple(
            item
            for item in (self._news_record(raw) for raw in self._raw_news)
            if wanted.intersection(item.symbols) and (since is None or item.published_at >= since)
        )
        return self._result(items)

    def get_sector_news(
        self, sectors: tuple[str, ...], since: datetime | None = None
    ) -> FetchResult[NewsRecord]:
        self._raise_failure()
        wanted = {sector.casefold() for sector in sectors}
        items = tuple(
            item
            for item in (self._news_record(raw) for raw in self._raw_news)
            if wanted.intersection(sector.casefold() for sector in item.sectors)
            and (since is None or item.published_at >= since)
        )
        return self._result(items)

    def _bars(
        self, symbols: tuple[str, ...], start: datetime, end: datetime, interval: str
    ) -> FetchResult[Bar]:
        self._raise_failure()
        wanted = {symbol.upper() for symbol in symbols}
        items = tuple(
            item
            for item in (self._bar(raw) for raw in self._raw_bars)
            if item.symbol in wanted
            and item.interval == interval
            and start <= item.market_timestamp < end
        )
        return self._result(items)

    def _result(self, items: tuple[Any, ...]) -> FetchResult[Any]:
        return FetchResult(provider=self.info, retrieved_at=self._now, items=items)

    def _raise_failure(self) -> None:
        if self._failure is not None:
            raise self._failure

    def _quote(self, raw: Mapping[str, Any]) -> Quote:
        try:
            return Quote(
                symbol=_string(raw, "symbol"),
                market_timestamp=_timestamp(raw, "market_timestamp"),
                retrieved_at=_timestamp(raw, "retrieved_at"),
                bid=_decimal_or_none(raw.get("bid")),
                ask=_decimal_or_none(raw.get("ask")),
                last=_decimal_or_none(raw.get("last")),
                volume=_integer_or_none(raw.get("volume")),
                state=_state(raw),
                state_reason=raw.get("state_reason"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderPayloadError(self.info.name, f"invalid quote: {exc}") from exc

    def _bar(self, raw: Mapping[str, Any]) -> Bar:
        try:
            return Bar(
                symbol=_string(raw, "symbol"),
                interval=_string(raw, "interval"),
                market_timestamp=_timestamp(raw, "market_timestamp"),
                retrieved_at=_timestamp(raw, "retrieved_at"),
                open=_decimal(raw, "open"),
                high=_decimal(raw, "high"),
                low=_decimal(raw, "low"),
                close=_decimal(raw, "close"),
                volume=_integer(raw, "volume"),
                state=_state(raw),
                state_reason=raw.get("state_reason"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderPayloadError(self.info.name, f"invalid bar: {exc}") from exc

    def _news_record(self, raw: Mapping[str, Any]) -> NewsRecord:
        try:
            return NewsRecord(
                article_id=_string(raw, "article_id"),
                headline=_string(raw, "headline"),
                publisher=_string(raw, "publisher"),
                source_url=_string(raw, "source_url"),
                published_at=_timestamp(raw, "published_at"),
                retrieved_at=_timestamp(raw, "retrieved_at"),
                symbols=_strings(raw.get("symbols", ()), "symbols"),
                sectors=_strings(raw.get("sectors", ()), "sectors"),
                summary=raw.get("summary"),
                state=_state(raw),
                state_reason=raw.get("state_reason"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderPayloadError(self.info.name, f"invalid news record: {exc}") from exc


def _string(raw: Mapping[str, Any], key: str) -> str:
    value = raw[key]
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


def _timestamp(raw: Mapping[str, Any], key: str) -> datetime:
    value = raw[key]
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{key} must be an RFC 3339 string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _decimal(raw: Mapping[str, Any], key: str) -> Decimal:
    value = _decimal_or_none(raw[key])
    if value is None:
        raise TypeError(f"{key} is required")
    return value


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise TypeError("price must be numeric")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("price must be numeric") from exc


def _integer(raw: Mapping[str, Any], key: str) -> int:
    value = _integer_or_none(raw[key])
    if value is None:
        raise TypeError(f"{key} is required")
    return value


def _integer_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("volume must be an integer")
    return value


def _strings(value: Any, key: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{key} must be a list of strings")
    return tuple(value)


def _state(raw: Mapping[str, Any]) -> DataState:
    return DataState(raw.get("state", DataState.CURRENT))
