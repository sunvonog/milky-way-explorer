"""Expectation checks with structured logging."""

from __future__ import annotations

from app.config import get_settings
from app.runtime.flow import get_run
from app.runtime.logging import bound_log


class ExpectationError(AssertionError):
    """Raised when a strict expectation check fails."""


def expect(name: str, actual: object, expected: object) -> bool:
    """Log a structured check record. Raise under ``settings.strict_checks``.

    Returns True when the check passes.
    """
    ok = actual == expected
    run = get_run()
    check_log = bound_log(
        run_id=run.run_id if run else "-",
        flow=run.flow_name if run else "-",
        task="check",
        check=name,
        actual=actual,
        expected=expected,
        ok=ok,
    )
    if ok:
        check_log.info("expectation met")
        return True

    check_log.warning("expectation missed")
    if get_settings().strict_checks:
        raise ExpectationError(f"{name}: expected {expected!r}, got {actual!r}")
    return False
