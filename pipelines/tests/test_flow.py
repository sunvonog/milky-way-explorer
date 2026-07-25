"""Tests for the flow / task runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import override_settings, reset_settings
from app.runtime.flow import flow, get_run, task


@pytest.fixture(autouse=True)
def _clean_settings(tmp_path: Path):
    reset_settings()
    override_settings(log_dir=tmp_path / "logs", log_level="WARNING", log_color=False)
    yield
    reset_settings()


def test_task_callable_outside_run():
    @task(name="standalone")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
    assert get_run() is None


def test_retries_then_succeeds():
    attempts = {"n": 0}

    @task(name="flaky", retries=2, retry_delay=0.01)
    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("not yet")
        return "ok"

    @flow(name="retry-flow")
    def run() -> str:
        return flaky()

    assert run() == "ok"
    assert attempts["n"] == 3
    ctx = get_run()
    assert ctx is None  # cleaned up after flow exits


def test_failure_propagates_and_records_task():
    captured: dict[str, object] = {}

    @task(name="boom", retries=1, retry_delay=0.01)
    def boom() -> None:
        raise ValueError("explode")

    @flow(name="fail-flow")
    def run() -> None:
        try:
            boom()
        finally:
            ctx = get_run()
            assert ctx is not None
            captured["tasks"] = [(t.name, t.status, t.attempts) for t in ctx.tasks]

    with pytest.raises(ValueError, match="explode"):
        run()

    assert captured["tasks"] == [("boom", "failed", 2)]


def test_subflow_joins_parent_run(tmp_path: Path):
    run_ids: list[str] = []

    @flow(name="child")
    def child() -> None:
        ctx = get_run()
        assert ctx is not None
        run_ids.append(ctx.run_id)
        assert ctx.flow_name == "parent"  # still the outermost run context

    @flow(name="parent")
    def parent() -> None:
        ctx = get_run()
        assert ctx is not None
        run_ids.append(ctx.run_id)
        child()

    parent()
    assert len(run_ids) == 2
    assert run_ids[0] == run_ids[1]

    log_files = list((tmp_path / "logs" / "parent").glob("*.jsonl"))
    assert len(log_files) == 1
    # No separate child log directory for the subflow
    assert not (tmp_path / "logs" / "child").exists() or not list(
        (tmp_path / "logs" / "child").glob("*.jsonl")
    )


def test_run_summary_contains_task_records(tmp_path: Path):
    @task(name="work")
    def work() -> int:
        return 42

    @flow(name="summary-flow")
    def run() -> None:
        assert work() == 42
        ctx = get_run()
        assert ctx is not None
        assert len(ctx.tasks) == 1
        assert ctx.tasks[0].name == "work"
        assert ctx.tasks[0].status == "success"
        assert ctx.tasks[0].attempts == 1
        assert ctx.log_path is not None
        assert Path(ctx.log_path).exists()

    run()
