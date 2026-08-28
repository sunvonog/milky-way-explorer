"""Tests for the flow / task runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.flow import flow, get_run, get_task, task

pytestmark = pytest.mark.usefixtures("isolated_data_root")


def test_task_callable_outside_run() -> None:
    @task(name="standalone")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
    assert get_run() is None


def test_retries_then_succeeds() -> None:
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


def test_failure_propagates_and_records_task() -> None:
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


def test_subflow_joins_parent_run(tmp_path: Path) -> None:
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


def test_run_summary_contains_task_records(tmp_path: Path) -> None:
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


def test_keyed_task_instances_are_distinct() -> None:
    captured: dict[str, object] = {}

    @task(name="fetch", key="source")
    def fetch(source: str) -> str:
        assert get_task() == f"fetch[{source}]"
        return source

    @flow(name="keyed-flow")
    def run() -> None:
        fetch("a")
        fetch("b")
        ctx = get_run()
        assert ctx is not None
        captured["names"] = [t.name for t in ctx.tasks]
        captured["instances"] = [t.instance for t in ctx.tasks]
        captured["keys"] = [t.key for t in ctx.tasks]

    run()
    assert captured["names"] == ["fetch", "fetch"]
    assert captured["instances"] == ["fetch[a]", "fetch[b]"]
    assert captured["keys"] == ["a", "b"]


def test_keyed_task_resolves_keyword_and_default() -> None:
    captured: list[str] = []

    @task(name="fetch", key="source")
    def fetch(source: str = "default") -> str:
        return source

    @flow(name="keyed-kw-flow")
    def run() -> None:
        fetch(source="via_kw")
        fetch()
        ctx = get_run()
        assert ctx is not None
        captured.extend(t.instance for t in ctx.tasks)

    run()
    assert captured == ["fetch[via_kw]", "fetch[default]"]


def test_invalid_task_key_raises_at_decoration() -> None:
    with pytest.raises(ValueError, match="not a parameter"):

        @task(name="bad", key="nope")
        def bad(source: str) -> str:
            return source


def test_task_summary_uses_instance_label(tmp_path: Path) -> None:
    import json

    @task(name="fetch", key="source")
    def fetch(source: str) -> str:
        return source

    @flow(name="summary-keyed-flow")
    def run() -> None:
        fetch("iau_csn")

    run()
    log_files = list((tmp_path / "logs" / "summary-keyed-flow").glob("*.jsonl"))
    assert len(log_files) == 1
    records = [json.loads(line) for line in log_files[0].read_text().splitlines() if line.strip()]
    summaries = [r for r in records if r.get("message") == "task summary"]
    assert len(summaries) == 1
    assert summaries[0]["extra"]["task"] == "fetch[iau_csn]"
    assert summaries[0]["extra"]["task_key"] == "iau_csn"
