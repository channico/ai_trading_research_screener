# Provider-independent data contracts

Jira AITS-9 defines the boundary between external data sources and deterministic
application code. The contracts live in `ai_trading_research_screener.providers`.
Screening services and future user interfaces consume only these records and
protocols; provider SDK response objects, sessions, authentication, and raw
configuration must stop inside the adapter.

## Responsibilities

- Adapters authenticate, call a provider, parse raw responses, normalize units
  and timestamps, assign a deterministic data state, and translate failures into
  `ProviderError` values. Credentials are read at runtime inside a live adapter
  and are never returned by `ProviderInfo`, persisted by this layer, or committed.
- `MarketDataProvider` supplies normalized quotes plus intraday and historical
  bars. `NewsProvider` supplies company- and sector-filtered news.
- `FetchResult` represents a completed request. An empty item tuple is a valid
  result with `DataState.MISSING`; it is not a provider failure.
- Provider failures raise `ProviderError`. Malformed records raise
  `ProviderPayloadError`; throttling raises `RateLimitError` with optional
  limit/reset metadata. Retry, caching, and production throttling policy belong
  to later work.
- `FakeProvider` is a synthetic adapter for automated tests and local demos. Its
  dictionaries are intentionally fictional and must not contain licensed data.

## Time conventions

Every publication, market, retrieval, and rate-limit-reset timestamp must be
timezone-aware. Records normalize instants to UTC. US market labels and display
times use the IANA `America/New_York` zone through `as_eastern`, so EST/EDT and
daylight-saving transitions are handled by zone rules rather than fixed offsets.
Bar `market_timestamp` is the start of its interval. A retrieval timestamp never
substitutes for publication or market time and cannot make old data fresh.

## Data states

- `current`: usable under the calling workflow's configured freshness policy.
- `missing`: the request succeeded but a record or matching result is absent.
- `delayed`: the provider identifies the data as delayed.
- `stale`: data exists but exceeds the workflow's deterministic age threshold.
- `unavailable`: the source cannot supply the requested datum or entitlement.

Non-current records/results require a reason. Exact freshness thresholds remain
visible application configuration for later tasks; adapters report timestamps
and provider flags but must not silently invent current data.

## MVP limitations

These interfaces do not select a final provider or implement IBKR, Massive, or
Wall Street Horizon. They do not calculate screens, rank candidates, place or
manage orders, retry requests, cache licensed data, or provide a UI. The planned
workflow remains premarket-only across broad US-stock discovery, the 41-stock
core watchlist, and seven ETF benchmarks. Eligibility will apply a configurable
USD 2 minimum; later deterministic screening may return both long and short
candidates and freeze its shortlist at a configurable 09:15 US Eastern default.
Read-only IB Gateway data is released and logout is confirmed before manual
trading in IBKR Desktop. Massive Basic News remains the preferred news-validation
source and Wall Street Horizon the scheduled-event source, subject to separate
live validation. Deterministic code alone owns data validation, timestamps,
filters, and rankings; AI cannot alter them or place orders.
