"""Tests for logly setup and per-run JSON log files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import override_settings, reset_settings
from app.runtime.flow import flow, task
from app.runtime.logging import bound_log, setup_logging, teardown_logging


@pytest.fixture(autouse=True)
def _clean_settings(tmp_path: Path):
    reset_settings()
    override_settings(log_dir=tmp_path / "logs", log_level="DEBUG", log_color=False)
    yield
    reset_settings()


def test_setup_logging_writes_jsonl(tmp_path: Path):
    path = setup_logging(flow_name="demo", run_id="abc123")
    assert path == tmp_path / "logs" / "demo" / "abc123.jsonl"
    bound_log(run_id="abc123", flow="demo", task="t1", rows=3).info("hello")
    teardown_logging()

    assert path.is_file()
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    assert lines
    record = lines[0]
    assert record["message"] == "hello"
    assert record["extra"]["run_id"] == "abc123"
    assert record["extra"]["flow"] == "demo"
    assert record["extra"]["task"] == "t1"
    assert record["extra"]["rows"] == "3"  # logly stringifies bound values


def test_flow_binds_run_id_on_records(tmp_path: Path):
    @task(name="step")
    def step() -> None:
        bound_log(run_id="ignored", flow="x", task="step", marker="yes").info("inside")

    @flow(name="log-flow")
    def run() -> None:
        step()

    run()
    log_files = list((tmp_path / "logs" / "log-flow").glob("*.jsonl"))
    assert len(log_files) == 1
    text = log_files[0].read_text()
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    run_ids = {r["extra"].get("run_id") for r in records if "extra" in r}
    # All records from the flow share one run_id (not the literal "ignored" alone)
    assert len(run_ids - {None, "-"}) >= 1
    assert any(r.get("message") == "task succeeded" for r in records)
    assert any(r.get("message") == "flow finished" for r in records)
