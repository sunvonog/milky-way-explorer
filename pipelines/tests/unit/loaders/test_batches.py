from pathlib import Path

import polars as pl
import pytest

from app.loaders.batches import load_csv_batches

SCHEMA = pl.Schema({"source_id": pl.Int64, "value": pl.Float64})


def _write_batch(path: Path, source_id: int, value: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame([{"source_id": source_id, "value": value}], schema=SCHEMA).write_csv(path)


def test_load_csv_batches_combines_files_in_filename_order(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"

    _write_batch(snapshot / "batches" / "demo-002.csv", 2, 20.0)
    _write_batch(snapshot / "batches" / "demo-001.csv", 1, 10.0)
    _write_batch(snapshot / "batches" / "ignored.csv", 99, 99.0)

    frame = load_csv_batches(
        snapshot, filename_pattern="demo-*.csv", schema=SCHEMA, batch_label="demo"
    )

    assert frame.schema == SCHEMA
    assert frame.to_dicts() == [{"source_id": 1, "value": 10.0}, {"source_id": 2, "value": 20.0}]


def test_load_csv_batches_requires_at_least_one_batch(tmp_path: Path) -> None:
    snapshot = tmp_path / "current"
    (snapshot / "batches").mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="no demo batch files"):
        load_csv_batches(snapshot, filename_pattern="demo-*.csv", schema=SCHEMA, batch_label="demo")
