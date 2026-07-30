"""Bounded DuckDB connections with views over the current build's Parquet.

A fresh in-memory connection per request: no cached handles, so a newly
published build is picked up without a restart, and no long-lived memory growth.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from app.data.paths import require


@contextmanager
def open_views(
    processed_root: Path,
    views: dict[str, str],
    memory_limit: str = "512MB",
) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open a connection exposing ``views`` as {view_name: parquet_filename}.

    Paths come from settings and are validated here; they never originate from a
    request, so interpolating them into CREATE VIEW is not an injection surface.
    User input is always bound as query parameter.
    """
    paths = require(processed_root, *views.values())
    con = duckdb.connect(database=":memory:")
    try:
        con.execute(f"SET memory_limit='{memory_limit}'")
        for view_name, filename in views.items():
            con.execute(
                f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet('{paths[filename]}')"
            )
        yield con
    finally:
        con.close()
