# Initial Stock Universe (AITS-7 / TS-001)

## Purpose

`config/stock_universe.toml` is the version-controlled source for the MVP's manually curated US-listed stock universe. It defines five themes, their benchmarks, and the metadata required to select securities deterministically.

The file is configuration, not a ranking or recommendation. Membership means only that a security is sufficiently liquid for the initial research workflow and has a documented relationship to at least one supported theme.

## Format

The TOML document contains three repeated table types:

- `[[themes]]`: stable theme identifier, display name, and thematic benchmark.
- `[[benchmarks]]`: ticker, name, US listing venue, and active flag.
- `[[stocks]]`: ticker, company name, one or more themes, broad sector, one or more benchmarks, US listing venue, security type, and active flag.

Theme IDs are stable program identifiers. Display names may evolve without breaking saved configuration.

`sector` is an internal broad classification for the screener; it is not represented as an official licensed GICS classification. `security_type` distinguishes common stock, US-listed depositary receipts, and US-listed ordinary shares.

## Selection policy

The initial selection was reviewed on 2026-08-26 using data available through 2026-08-25.

All included stocks had to meet these rules:

1. Listed on Nasdaq or the New York Stock Exchange and present in Nasdaq Trader's current all-issues symbol directory.
2. Marked as a real, non-ETF, non-test security with no adverse Nasdaq financial-status flag where that field applies.
3. At least 500,000 average consolidated shares traded per US trading day during July 2026. The screen divides Nasdaq's July consolidated volume by 22 trading days.
4. A direct, explainable relationship to at least one supported theme.

The volume threshold is an initial reproducible screen, not a permanent liquidity guarantee. Later ingestion work must calculate current price, dollar volume, spread, and freshness before a security is treated as tradable research input.

Primary verification sources:

- [Nasdaq Trader Symbol Directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
- [Nasdaq Trader current Symbol Lookup](https://www.nasdaqtrader.com/Trader.aspx?id=symbollookup)
- [Nasdaq Trader monthly volume statistics by symbol](https://www.nasdaqtrader.com/trader.aspx?ID=marketsharedaily)
- [SEC company ticker and exchange associations](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [Circle Internet Group SEC filing confirming CRCL and its NYSE listing](https://www.sec.gov/Archives/edgar/data/1876042/000187604226000205/crcl-20260629.htm)
- [Space Exploration Technologies SEC filing confirming SPCX and its Nasdaq listing](https://www.sec.gov/Archives/edgar/data/1181412/000162828026043288/spaceexplorationtechnologi.htm)

No downloaded Nasdaq or SEC source dataset is committed to this repository.

## Subjective inclusions and exclusions

- **AI and software:** combines large AI platforms with liquid enterprise software and observability companies. NVIDIA is intentionally shared with semiconductors. Smaller companies with indirect AI branding were excluded.
- **Semiconductors:** covers designers, manufacturers, memory, connectivity, and semiconductor equipment. Liquid US-listed depositary receipts are allowed even when the issuer is not US-domiciled.
- **Crypto-related equities:** includes a liquid exchange, stablecoin infrastructure, brokerage exposure, a bitcoin-treasury company, and listed miners. Spot crypto and crypto ETFs are excluded because this task covers equities.
- **Space:** favors liquid, comparatively direct space infrastructure, launch, satellite, and geospatial exposure. SPCX is included because Space Exploration Technologies became publicly traded in June 2026, but its short public history remains a limitation. Diversified defense primes are excluded because space is not their dominant exposure.
- **Quantum:** includes four liquid pure-play quantum companies plus IBM, Microsoft, and Alphabet because they operate material quantum-computing programs. Quantum-security vendors and less-liquid early-stage names are excluded.
- Cross-theme membership is intentional. It prevents the configuration from pretending that companies such as Microsoft, Alphabet, and NVIDIA have only one relevant exposure.

## Maintenance

This universe is a dated configuration snapshot. A future change should update `as_of_date`, repeat the listing and liquidity checks, document additions/removals here or in a linked decision record, and run the automated validation suite.

Validate the file locally with:

```bash
python -m ai_trading_research_screener.universe config/stock_universe.toml
```
