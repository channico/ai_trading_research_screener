"""Load and validate the version-controlled stock universe."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import date
from pathlib import Path
import tomllib
from typing import Any


EXPECTED_THEME_IDS = {
    "ai_software",
    "semiconductors",
    "crypto_equities",
    "space",
    "quantum",
}
REQUIRED_MARKET_BENCHMARKS = {"SPY", "QQQ", "IWM"}
SUPPORTED_EXCHANGES = {"NASDAQ", "NYSE", "NYSE_ARCA"}
SUPPORTED_SECURITY_TYPES = {"common_stock", "adr", "ordinary_share"}


class UniverseValidationError(ValueError):
    """Raised when the stock-universe configuration violates its contract."""


def load_universe(path: str | Path) -> dict[str, Any]:
    """Read a TOML universe file and return it after deterministic validation."""

    universe_path = Path(path)
    with universe_path.open("rb") as universe_file:
        universe = tomllib.load(universe_file)

    validate_universe(universe)
    return universe


def validate_universe(universe: Mapping[str, Any]) -> None:
    """Validate the AITS-7 schema and acceptance constraints."""

    errors: list[str] = []

    if universe.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    as_of_date = universe.get("as_of_date")
    if not isinstance(as_of_date, str):
        errors.append("as_of_date must be an ISO date string")
    else:
        try:
            date.fromisoformat(as_of_date)
        except ValueError:
            errors.append("as_of_date must use YYYY-MM-DD format")

    minimum_volume = universe.get("minimum_average_daily_share_volume")
    if not isinstance(minimum_volume, int) or isinstance(minimum_volume, bool) or minimum_volume <= 0:
        errors.append("minimum_average_daily_share_volume must be a positive integer")

    themes = _record_list(universe, "themes", errors)
    benchmarks = _record_list(universe, "benchmarks", errors)
    stocks = _record_list(universe, "stocks", errors)

    theme_ids: set[str] = set()
    theme_benchmarks: dict[str, str] = {}
    for index, theme in enumerate(themes):
        label = f"themes[{index}]"
        theme_id = _required_string(theme, "id", label, errors)
        _required_string(theme, "name", label, errors)
        benchmark = _required_string(theme, "benchmark", label, errors)
        if theme_id:
            if theme_id in theme_ids:
                errors.append(f"duplicate theme id: {theme_id}")
            theme_ids.add(theme_id)
            if benchmark:
                theme_benchmarks[theme_id] = benchmark

    if theme_ids != EXPECTED_THEME_IDS:
        errors.append(
            "themes must be exactly: " + ", ".join(sorted(EXPECTED_THEME_IDS))
        )

    benchmark_tickers: set[str] = set()
    for index, benchmark in enumerate(benchmarks):
        label = f"benchmarks[{index}]"
        ticker = _required_string(benchmark, "ticker", label, errors)
        _required_string(benchmark, "name", label, errors)
        exchange = _required_string(benchmark, "exchange", label, errors)
        active = benchmark.get("active")
        if not isinstance(active, bool):
            errors.append(f"{label}.active must be a boolean")
        if ticker:
            if ticker != ticker.upper():
                errors.append(f"{label}.ticker must be uppercase")
            if ticker in benchmark_tickers:
                errors.append(f"duplicate benchmark ticker: {ticker}")
            benchmark_tickers.add(ticker)
        if exchange and exchange not in SUPPORTED_EXCHANGES:
            errors.append(f"{label}.exchange is unsupported: {exchange}")

    missing_market_benchmarks = REQUIRED_MARKET_BENCHMARKS - benchmark_tickers
    if missing_market_benchmarks:
        errors.append(
            "missing required market benchmarks: "
            + ", ".join(sorted(missing_market_benchmarks))
        )

    for theme_id, benchmark in theme_benchmarks.items():
        if benchmark not in benchmark_tickers:
            errors.append(f"theme {theme_id} references unknown benchmark {benchmark}")

    if not 30 <= len(stocks) <= 50:
        errors.append("the initial universe must contain between 30 and 50 stocks")

    stock_tickers: set[str] = set()
    stocks_per_theme = {theme_id: 0 for theme_id in EXPECTED_THEME_IDS}
    for index, stock in enumerate(stocks):
        label = f"stocks[{index}]"
        ticker = _required_string(stock, "ticker", label, errors)
        _required_string(stock, "company_name", label, errors)
        _required_string(stock, "sector", label, errors)
        exchange = _required_string(stock, "exchange", label, errors)
        security_type = _required_string(stock, "security_type", label, errors)
        active = stock.get("active")
        stock_themes = _string_list(stock, "themes", label, errors)
        stock_benchmarks = _string_list(stock, "benchmarks", label, errors)

        if not isinstance(active, bool):
            errors.append(f"{label}.active must be a boolean")
        if ticker:
            if ticker != ticker.upper():
                errors.append(f"{label}.ticker must be uppercase")
            if ticker in stock_tickers:
                errors.append(f"duplicate stock ticker: {ticker}")
            if ticker in benchmark_tickers:
                errors.append(f"stock ticker is also configured as a benchmark: {ticker}")
            stock_tickers.add(ticker)
        if exchange and exchange not in SUPPORTED_EXCHANGES:
            errors.append(f"{label}.exchange is unsupported: {exchange}")
        if security_type and security_type not in SUPPORTED_SECURITY_TYPES:
            errors.append(f"{label}.security_type is unsupported: {security_type}")
        if not stock_themes:
            errors.append(f"{label}.themes must not be empty")
        if not stock_benchmarks:
            errors.append(f"{label}.benchmarks must not be empty")

        for theme_id in stock_themes:
            if theme_id not in theme_ids:
                errors.append(f"{label} references unknown theme {theme_id}")
                continue
            stocks_per_theme[theme_id] += 1
            expected_benchmark = theme_benchmarks.get(theme_id)
            if expected_benchmark and expected_benchmark not in stock_benchmarks:
                errors.append(
                    f"{label} must include benchmark {expected_benchmark} for theme {theme_id}"
                )

        unknown_benchmarks = set(stock_benchmarks) - benchmark_tickers
        if unknown_benchmarks:
            errors.append(
                f"{label} references unknown benchmarks: "
                + ", ".join(sorted(unknown_benchmarks))
            )

    empty_themes = [theme for theme, count in stocks_per_theme.items() if count == 0]
    if empty_themes:
        errors.append("themes without stocks: " + ", ".join(sorted(empty_themes)))

    if errors:
        raise UniverseValidationError("Invalid stock universe:\n- " + "\n- ".join(errors))


def _record_list(
    universe: Mapping[str, Any], key: str, errors: list[str]
) -> list[Mapping[str, Any]]:
    value = universe.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array of tables")
        return []
    if not all(isinstance(record, Mapping) for record in value):
        errors.append(f"every {key} entry must be a table")
        return []
    return value


def _required_string(
    record: Mapping[str, Any], field: str, label: str, errors: list[str]
) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}.{field} must be a non-empty string")
        return ""
    return value


def _string_list(
    record: Mapping[str, Any], field: str, label: str, errors: list[str]
) -> list[str]:
    value = record.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        errors.append(f"{label}.{field} must be an array of non-empty strings")
        return []
    if len(value) != len(set(value)):
        errors.append(f"{label}.{field} must not contain duplicates")
    return value


def main() -> None:
    """Validate a universe file and print a short deterministic summary."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to stock_universe.toml")
    args = parser.parse_args()
    universe = load_universe(args.path)
    print(
        f"Validated {len(universe['stocks'])} stocks across "
        f"{len(universe['themes'])} themes."
    )


if __name__ == "__main__":
    main()
