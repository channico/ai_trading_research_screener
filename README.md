# AI Trading Research Screener

A local Python application for screening liquid US equities and producing evidence-backed research inputs for a trader.

The project is a research and scenario-planning aid. It does not place orders, guarantee predictions, or replace human validation of prices, news, risk, and execution conditions.

## Current scope

AITS-14 establishes the repository and local development environment. AITS-7
defines the initial stock universe, and AITS-9 adds provider-independent data
contracts plus a synthetic demo adapter. Later Jira tasks will implement live
provider validation, deterministic metrics, rankings, evidence collection, and
grounded AI explanations.

Deterministic Python code—not an AI model—will own calculations, timestamps, filters, and ranking. AI output may explain supplied evidence and uncertainty, but must not silently alter calculated results.

## Project structure

```text
.
├── config/
│   └── stock_universe.toml  # Version-controlled themes and securities
├── data/
│   ├── sample/       # Small, redistributable fixtures that may be committed
│   ├── raw/          # Local provider downloads; ignored by Git
│   ├── processed/    # Derived local datasets; ignored by Git
│   └── generated/    # Generated reports and artifacts; ignored by Git
├── docs/             # Implementation-linked technical documentation
├── evals/            # Evaluation datasets and harnesses
├── src/
│   └── ai_trading_research_screener/
└── tests/
```

Private roadmaps, decisions, provider research, risks, and sprint notes belong in the separate `ai_trading_screener_planning` repository. Jira project `AITS` remains authoritative for live status and sprint planning.

## Local setup

Python 3.12 or newer is required. The repository was initially verified with Python 3.14.

```bash
cd /Users/nico/PycharmProjects/ai_trading_research_screener
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

The existing `.venv` may be reused. Never commit `.env` or real API credentials.

## Dependency management

`pyproject.toml` is the dependency source of truth:

- Add packages required by the application to `project.dependencies`.
- Add development-only tools to `project.optional-dependencies.dev`.
- Re-run `python -m pip install -e ".[dev]"` after dependency changes.
- Do not install a package without documenting it in `pyproject.toml`.

The AITS-8 validation plan prefers read-only IBKR market data, Massive Basic
News, and the existing Wall Street Horizon scheduled-event entitlement. Complete
live integrations remain out of scope here, so the example configuration keeps
provider-neutral, empty environment placeholders and never stores credentials.

## Data-provider boundary

Application code consumes the normalized contracts in
`ai_trading_research_screener.providers`; provider SDK objects and credentials
remain inside adapters. See [`docs/provider-contracts.md`](docs/provider-contracts.md)
for responsibilities, timestamp conventions, data states, and current limits.

## Validate the initial universe

The selection policy, format, sources, and subjective choices are documented in [`docs/stock-universe.md`](docs/stock-universe.md).

```bash
python -m ai_trading_research_screener.universe config/stock_universe.toml
```

## Run the tests

```bash
source .venv/bin/activate
python -m pytest
```

## Configuration safety

Copy `.env.example` to `.env` for local values. The example contains no secrets. Keep downloaded/licensed market data in ignored local directories unless redistribution is explicitly permitted.
