"""Environment-backed application settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, slots=True)
class Settings:
    """Small provider-neutral configuration used by the initial scaffold."""

    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings from local environment variables and safe defaults."""

        return cls(
            environment=os.getenv("AITS_ENV", "development"),
            log_level=os.getenv("AITS_LOG_LEVEL", "INFO").upper(),
            data_dir=Path(os.getenv("AITS_DATA_DIR", "data")),
        )
