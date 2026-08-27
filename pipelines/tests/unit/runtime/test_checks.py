"""Tests for expectation checks."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config import override_settings, reset_settings
from app.runtime.checks import ExpectationError, expect
from app.runtime.flow import flow


@pytest.fixture(autouse=True)
def _clean_settings(tmp_path: Path) -> Iterator[None]:
    reset_settings()
    override_settings(log_dir=tmp_path / "logs", log_level="WARNING", log_color=False)
    yield
    reset_settings()


def test_expect_passes() -> None:
    @flow(name="check-ok")
    def run() -> None:
        assert expect("stars", 605, 605) is True

    run()


def test_expect_warns_when_not_strict() -> None:
    @flow(name="check-warn")
    def run() -> None:
        assert expect("stars", 1, 605) is False

    run()  # must not raise


def test_expect_raises_when_strict() -> None:
    override_settings(strict_checks=True)

    @flow(name="check-strict")
    def run() -> None:
        expect("stars", 1, 605)

    with pytest.raises(ExpectationError, match="stars"):
        run()
