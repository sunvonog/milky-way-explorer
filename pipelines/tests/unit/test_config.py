"""Tests for pydantic Settings and CLI overrides."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import REPO_ROOT, get_settings, override_settings, reset_settings


@pytest.fixture(autouse=True)
def _clean_settings() -> Iterator[None]:
    reset_settings()
    yield
    reset_settings()


def test_defaults_resolve_under_repo_root() -> None:
    settings = get_settings()
    assert settings.data_root == REPO_ROOT / "data"
    assert settings.raw_root == REPO_ROOT / "data" / "raw"
    assert settings.processed_root == REPO_ROOT / "data" / "processed"
    assert settings.logs_root == REPO_ROOT / "data" / "logs"
    assert settings.inputs_dir == REPO_ROOT / "pipelines" / "_inputs"
    assert settings.strict_checks is False


def test_log_dir_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MWE_LOG_DIR", str(tmp_path / "custom-logs"))
    reset_settings()
    settings = get_settings()
    assert settings.logs_root == tmp_path / "custom-logs"


def test_data_root_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MWE_DATA_ROOT", str(tmp_path))
    reset_settings()
    settings = get_settings()
    assert settings.data_root == tmp_path
    assert settings.raw_root == tmp_path / "raw"
    assert settings.logs_root == tmp_path / "logs"


def test_cli_override_settings() -> None:
    updated = override_settings(strict_checks=True, log_level="DEBUG")
    assert updated.strict_checks is True
    assert updated.log_level == "DEBUG"
    assert get_settings().strict_checks is True


def test_cli_override_rejects_unknown_settings() -> None:
    with pytest.raises(TypeError, match="unknown setting override: unknown_setting"):
        override_settings(unknown_setting=True)


def test_cli_override_validates_values_without_mutating_settings() -> None:
    original = get_settings()

    with pytest.raises(ValidationError):
        override_settings(gaia_background_source_count=0)

    assert get_settings() is original
    assert get_settings().gaia_background_source_count > 0


def test_gaia_background_retrieval_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MWE_GAIA_BACKGROUND_SOURCE_COUNT", "20000")
    monkeypatch.setenv("MWE_GAIA_BACKGROUND_BATCH_SIZE", "2500")
    reset_settings()

    settings = get_settings()

    assert settings.gaia_background_source_count == 20_000
    assert settings.gaia_background_batch_size == 2500
