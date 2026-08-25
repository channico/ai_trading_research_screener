from pathlib import Path

from ai_trading_research_screener import Settings


def test_settings_use_safe_defaults(monkeypatch) -> None:
    monkeypatch.delenv("AITS_ENV", raising=False)
    monkeypatch.delenv("AITS_LOG_LEVEL", raising=False)
    monkeypatch.delenv("AITS_DATA_DIR", raising=False)

    settings = Settings.from_environment()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.data_dir == Path("data")


def test_settings_read_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AITS_ENV", "test")
    monkeypatch.setenv("AITS_LOG_LEVEL", "debug")
    monkeypatch.setenv("AITS_DATA_DIR", str(tmp_path))

    settings = Settings.from_environment()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == tmp_path
