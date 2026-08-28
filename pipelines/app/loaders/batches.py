"""Shared loading mechanism for CSV batch snapshots."""

from __future__ import annotations

from pathlib import Path

import polars as pl


def load_csv_batches(
    snapshot: Path, *, filename_pattern: str, schema: pl.Schema, batch_label: str
) -> pl.DataFrame:
    """Read matching snapshot batches in deterministic filename order."""
    batches_root = snapshot / "batches"
    batch_paths = sorted(path for path in batches_root.glob(filename_pattern) if path.is_file())

    if not batch_paths:
        raise FileNotFoundError(f"no {batch_label} batch files found in: {batches_root}")

    frames = [pl.read_csv(path, schema=schema, null_values="") for path in batch_paths]

    return pl.concat(frames, how="vertical")
