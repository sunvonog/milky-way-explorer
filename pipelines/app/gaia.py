"""Pure transformations supporting Gaia host enrichment."""

from __future__ import annotations

import polars as pl


def build_gaia_host_ids(hosts: pl.DataFrame) -> pl.DataFrame:
    """Build the distinct Gaia source-ID manifest for exoplanets hosts."""
    return (
        hosts.select(pl.col("gaia_source_id").cast(pl.Int64))
        .drop_nulls()
        .unique()
        .sort("gaia_source_id")
    )
