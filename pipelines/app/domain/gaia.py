"""Pure transformations supporting Gaia host enrichment."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True, slots=True)
class GaiaHostBatch:
    """One deterministic unit of exact Gaia source retrieval."""

    batch_number: int
    source_ids: tuple[int, ...]


def build_gaia_host_ids(hosts: pl.DataFrame) -> pl.DataFrame:
    """Build the distinct Gaia source-ID manifest for exoplanet hosts."""
    return (
        hosts.select(pl.col("gaia_source_id").cast(pl.Int64))
        .drop_nulls()
        .unique()
        .sort("gaia_source_id")
    )


def plan_gaia_host_batches(host_ids: pl.DataFrame, *, batch_size: int) -> list[GaiaHostBatch]:
    """Split canonical Gaia host IDs into stable, bounded batches."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    source_ids: list[int] = build_gaia_host_ids(host_ids).get_column("gaia_source_id").to_list()

    return [
        GaiaHostBatch(
            batch_number=batch_number, source_ids=tuple(source_ids[start : start + batch_size])
        )
        for batch_number, start in enumerate(
            range(0, len(source_ids), batch_size),
            start=1,
        )
    ]
