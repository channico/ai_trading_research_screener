from copy import deepcopy
from pathlib import Path

import pytest

from ai_trading_research_screener.universe import (
    EXPECTED_THEME_IDS,
    REQUIRED_MARKET_BENCHMARKS,
    UniverseValidationError,
    load_universe,
    validate_universe,
)


UNIVERSE_PATH = Path(__file__).parents[1] / "config" / "stock_universe.toml"


def test_initial_universe_meets_aits_7_contract() -> None:
    universe = load_universe(UNIVERSE_PATH)

    assert len(universe["stocks"]) == 41
    assert {theme["id"] for theme in universe["themes"]} == EXPECTED_THEME_IDS
    assert REQUIRED_MARKET_BENCHMARKS <= {
        benchmark["ticker"] for benchmark in universe["benchmarks"]
    }
    assert all(stock["active"] for stock in universe["stocks"])


def test_duplicate_ticker_is_rejected() -> None:
    universe = deepcopy(load_universe(UNIVERSE_PATH))
    universe["stocks"].append(deepcopy(universe["stocks"][0]))

    with pytest.raises(UniverseValidationError, match="duplicate stock ticker"):
        validate_universe(universe)


def test_unknown_theme_is_rejected() -> None:
    universe = deepcopy(load_universe(UNIVERSE_PATH))
    universe["stocks"][0]["themes"] = ["unknown_theme"]

    with pytest.raises(UniverseValidationError, match="unknown theme"):
        validate_universe(universe)


def test_missing_theme_benchmark_is_rejected() -> None:
    universe = deepcopy(load_universe(UNIVERSE_PATH))
    universe["stocks"][0]["benchmarks"] = ["SPY"]

    with pytest.raises(UniverseValidationError, match="must include benchmark"):
        validate_universe(universe)
