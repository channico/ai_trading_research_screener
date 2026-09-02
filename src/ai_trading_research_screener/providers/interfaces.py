"""Application-facing provider ports. Provider SDK objects stop at adapters."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from .contracts import Bar, FetchResult, NewsRecord, ProviderInfo, Quote


@runtime_checkable
class MarketDataProvider(Protocol):
    @property
    def info(self) -> ProviderInfo: ...

    def get_quotes(self, symbols: tuple[str, ...]) -> FetchResult[Quote]: ...

    def get_intraday_bars(
        self, symbols: tuple[str, ...], start: datetime, end: datetime, interval: str
    ) -> FetchResult[Bar]: ...

    def get_historical_bars(
        self, symbols: tuple[str, ...], start: datetime, end: datetime, interval: str
    ) -> FetchResult[Bar]: ...


@runtime_checkable
class NewsProvider(Protocol):
    @property
    def info(self) -> ProviderInfo: ...

    def get_company_news(
        self, symbols: tuple[str, ...], since: datetime | None = None
    ) -> FetchResult[NewsRecord]: ...

    def get_sector_news(
        self, sectors: tuple[str, ...], since: datetime | None = None
    ) -> FetchResult[NewsRecord]: ...
