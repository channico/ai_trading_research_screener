from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from ai_trading_research_screener.providers import (
    Bar,
    DataState,
    FetchResult,
    MarketDataProvider,
    NewsProvider,
    NewsRecord,
    ProviderError,
    ProviderErrorKind,
    ProviderInfo,
    ProviderPayloadError,
    Quote,
    RateLimit,
    RateLimitError,
    as_eastern,
)
from ai_trading_research_screener.providers.contracts import ContractValidationError
from ai_trading_research_screener.providers.fake import FakeProvider


NOW = datetime(2026, 9, 2, 13, 15, tzinfo=timezone.utc)
EARLIER = NOW - timedelta(minutes=1)


def _quote(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "symbol": "NVDA",
        "market_timestamp": "2026-09-02T13:14:59Z",
        "retrieved_at": "2026-09-02T13:15:00Z",
        "bid": "100.10",
        "ask": "100.12",
        "last": "100.11",
        "volume": 250000,
    }
    raw.update(overrides)
    return raw


def _bar(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "symbol": "NVDA",
        "interval": "1m",
        "market_timestamp": "2026-09-02T13:14:00Z",
        "retrieved_at": "2026-09-02T13:15:00Z",
        "open": "100.00",
        "high": "100.20",
        "low": "99.90",
        "close": "100.10",
        "volume": 5000,
    }
    raw.update(overrides)
    return raw


def _news(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "article_id": "demo-1",
        "headline": "Fictional chip company announces demo event",
        "publisher": "Synthetic Wire",
        "source_url": "https://example.test/demo-1",
        "published_at": "2026-09-02T13:00:00Z",
        "retrieved_at": "2026-09-02T13:15:00Z",
        "symbols": ["NVDA"],
        "sectors": ["Semiconductors"],
    }
    raw.update(overrides)
    return raw


def test_fake_adapter_returns_normalized_quote_bar_and_news_records() -> None:
    provider = FakeProvider(quotes=[_quote()], bars=[_bar()], news=[_news()], now=NOW)

    quote_result = provider.get_quotes(("NVDA",))
    bar_result = provider.get_intraday_bars(("NVDA",), NOW - timedelta(hours=1), NOW, "1m")
    news_result = provider.get_company_news(("NVDA",))

    assert quote_result.items == (
        Quote(
            symbol="NVDA",
            market_timestamp=datetime(2026, 9, 2, 13, 14, 59, tzinfo=timezone.utc),
            retrieved_at=NOW,
            bid=Decimal("100.10"),
            ask=Decimal("100.12"),
            last=Decimal("100.11"),
            volume=250000,
        ),
    )
    assert isinstance(bar_result.items[0], Bar)
    assert isinstance(news_result.items[0], NewsRecord)
    assert quote_result.provider == ProviderInfo("synthetic-demo")


def test_valid_empty_result_is_missing_and_not_a_failure() -> None:
    result = FakeProvider(now=NOW).get_quotes(("NVDA",))

    assert result.items == ()
    assert result.state is DataState.MISSING
    assert result.state_reason == "provider returned no matching records"


@pytest.mark.parametrize("state", [state for state in DataState if state is not DataState.CURRENT])
def test_non_current_states_are_explicit_and_require_reasons(state: DataState) -> None:
    quote = FakeProvider(
        quotes=[_quote(state=state.value, state_reason="synthetic condition")], now=NOW
    ).get_quotes(("NVDA",)).items[0]

    assert quote.state is state
    assert quote.state_reason == "synthetic condition"

    with pytest.raises(ProviderPayloadError, match="non-current data requires a reason"):
        FakeProvider(quotes=[_quote(state=state.value)], now=NOW).get_quotes(("NVDA",))


@pytest.mark.parametrize(
    ("payload", "method", "message"),
    [
        ({"quotes": [_quote(ask="not-a-number")]}, "quote", "invalid quote"),
        ({"bars": [_bar(high="99.00")]}, "bar", "invalid bar"),
        ({"news": [_news(source_url="provider-object")]}, "news", "invalid news record"),
    ],
)
def test_malformed_provider_payloads_raise_explicit_errors(
    payload: dict[str, list[dict[str, object]]], method: str, message: str
) -> None:
    provider = FakeProvider(now=NOW, **payload)

    with pytest.raises(ProviderPayloadError, match=message) as raised:
        if method == "quote":
            provider.get_quotes(("NVDA",))
        elif method == "bar":
            provider.get_intraday_bars(("NVDA",), NOW - timedelta(hours=1), NOW, "1m")
        else:
            provider.get_company_news(("NVDA",))

    assert raised.value.kind is ProviderErrorKind.MALFORMED_RESPONSE
    assert raised.value.retryable is False


def test_provider_failure_is_distinct_from_an_empty_result() -> None:
    failure = ProviderError(
        provider="synthetic-demo",
        kind=ProviderErrorKind.TRANSPORT,
        message="simulated disconnect",
        retryable=True,
    )
    provider = FakeProvider(failure=failure, now=NOW)

    with pytest.raises(ProviderError, match="simulated disconnect") as raised:
        provider.get_quotes(("NVDA",))

    assert raised.value.kind is ProviderErrorKind.TRANSPORT
    assert raised.value.retryable is True


def test_rate_limit_failure_preserves_safe_retry_metadata() -> None:
    limit = RateLimit(
        limit=5,
        remaining=0,
        reset_at=NOW + timedelta(minutes=1),
        retry_after=timedelta(seconds=60),
    )
    provider = FakeProvider(
        failure=RateLimitError("synthetic-demo", "request budget exhausted", limit),
        now=NOW,
    )

    with pytest.raises(RateLimitError) as raised:
        provider.get_company_news(("NVDA",))

    assert raised.value.kind is ProviderErrorKind.RATE_LIMITED
    assert raised.value.rate_limit == limit


def test_timestamps_normalize_to_utc_and_render_in_dst_aware_eastern_time() -> None:
    singapore = ZoneInfo("Asia/Singapore")
    quote = Quote(
        symbol="NVDA",
        market_timestamp=datetime(2026, 9, 2, 21, 14, tzinfo=singapore),
        retrieved_at=datetime(2026, 9, 2, 21, 15, tzinfo=singapore),
        last=Decimal("100"),
    )

    assert quote.market_timestamp == datetime(2026, 9, 2, 13, 14, tzinfo=timezone.utc)
    assert as_eastern(quote.market_timestamp).isoformat() == "2026-09-02T09:14:00-04:00"

    with pytest.raises(ContractValidationError, match="timezone-aware"):
        Quote("NVDA", datetime(2026, 9, 2, 9, 14), NOW, last=Decimal("100"))


def test_provider_substitution_keeps_the_application_interface_unchanged() -> None:
    first = FakeProvider(quotes=[_quote(last="100.11")], now=NOW)
    second = FakeProvider(quotes=[_quote(last="101.25")], now=NOW)

    def calculation_input(provider: MarketDataProvider) -> tuple[Decimal | None, ...]:
        return tuple(quote.last for quote in provider.get_quotes(("NVDA",)).items)

    assert calculation_input(first) == (Decimal("100.11"),)
    assert calculation_input(second) == (Decimal("101.25"),)


def test_fake_adapter_satisfies_both_runtime_protocol_shapes() -> None:
    provider = FakeProvider(now=NOW)

    assert isinstance(provider, MarketDataProvider)
    assert isinstance(provider, NewsProvider)


def test_fetch_result_can_preserve_reported_rate_limit_state() -> None:
    limit = RateLimit(limit=100, remaining=99, reset_at=NOW + timedelta(minutes=1))

    result: FetchResult[Quote] = FetchResult(
        provider=ProviderInfo("synthetic-demo"),
        retrieved_at=NOW,
        items=(Quote("NVDA", EARLIER, NOW, last=Decimal("100")),),
        rate_limit=limit,
    )

    assert result.rate_limit == limit
