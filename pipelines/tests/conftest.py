"""Shared fixtures for pipeline tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config import override_settings, reset_settings


@pytest.fixture(autouse=True)
def reset_pipeline_settings() -> Iterator[None]:
    """Prevent cached settings and CLI overrides from leaking between tests."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def isolated_data_root(tmp_path: Path) -> Path:
    """Configure pipeline I/O to use temporary test directory."""
    override_settings(
        data_root=tmp_path, log_dir=tmp_path / "logs", log_level="WARNING", log_color=False
    )
    return tmp_path
