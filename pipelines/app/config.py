"""Pipeline settings, shared MWE_ environment vocabulary with the backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# pipelines/app/config.py -> parents[2] == repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

_cli_overrides: dict[str, object] = {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MWE_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    env: str = "development"
    data_root: Path = Field(default_factory=lambda: REPO_ROOT / "data")
    log_level: str = "INFO"
    log_json: bool = False
    log_color: bool = True
    log_dir: Path | None = None
    log_retention: int = 20
    strict_checks: bool = False

    gaia_background_source_count: int = Field(default=1_000_000, gt=0)
    gaia_background_batch_size: int = Field(default=100_000, gt=0)
    gaia_density_grid_sizes: tuple[int, ...] = (128,)
    gaia_density_extent_kpc: float = Field(default=20.0, gt=0)

    @property
    def raw_root(self) -> Path:
        return self.data_root / "raw"

    @property
    def processed_root(self) -> Path:
        return self.data_root / "processed"

    @property
    def logs_root(self) -> Path:
        return self.log_dir if self.log_dir is not None else self.data_root / "logs"

    @property
    def inputs_dir(self) -> Path:
        return REPO_ROOT / "pipelines" / "_inputs"


def _settings_with_overrides(overrides: dict[str, object]) -> Settings:
    unknown_fields = sorted(
        set(overrides) - set(Settings.model_fields),
    )

    if unknown_fields:
        label = "setting override" if len(unknown_fields) == 1 else "setting overrides"
        raise TypeError(f"unknown {label}: {', '.join(unknown_fields)}")

    base = Settings()

    return Settings.model_validate({**base.model_dump(), **overrides})


@lru_cache
def get_settings() -> Settings:
    return _settings_with_overrides(_cli_overrides)


def override_settings(**kwargs: object) -> Settings:
    """Validate and apply CLI overrides on top of environment settings."""
    candidate = {**_cli_overrides, **kwargs}
    updated = _settings_with_overrides(candidate)

    _cli_overrides.clear()
    _cli_overrides.update(candidate)
    get_settings.cache_clear()

    return updated


def reset_settings() -> None:
    """Clear CLI overrides and the settings cache (tests)."""
    _cli_overrides.clear()
    get_settings.cache_clear()
