"""Publish frontend visualization artifacts from processed domain tables."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from app.artifacts import (
    EXOPLANET_HOSTS_FILENAME,
    EXOPLANET_SYSTEMS_FILENAME,
    GAIA_HOST_SOURCES_FILENAME,
    HOST_VISUALIZATION_FILENAME,
)
from app.config import get_settings
from app.domain.visualization import build_host_visualization_records as build_visualization_records
from app.runtime.checks import expect
from app.runtime.flow import flow, task

EXPECTED_POSITION_STATUS_COUNTS = {
    "available": 4287,
    "no_accepted_distance": 109,
    "no_exact_gaia_source": 353,
}


@task(name="resolve_host_visualization_inputs")
def resolve_host_visualization_inputs() -> tuple[Path, Path, Path]:
    """Resolve every processed table required by the visualization"""
    processed = get_settings().processed_root

    paths = (
        processed / EXOPLANET_HOSTS_FILENAME,
        processed / EXOPLANET_SYSTEMS_FILENAME,
        processed / GAIA_HOST_SOURCES_FILENAME,
    )

    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"missing host visualization input: {path}")

    return paths


@task(name="load_host_visualization_inputs")
def load_host_visualization_inputs(
    paths: tuple[Path, Path, Path],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Load the processed host, system, and Gaia source tables."""
    hosts_path, systems_path, gaia_sources_path = paths

    return (
        pl.read_parquet(hosts_path),
        pl.read_parquet(systems_path),
        pl.read_parquet(gaia_sources_path),
    )


@task(name="build_host_visualization_records")
def build_host_visualization_table(
    hosts: pl.DataFrame, systems: pl.DataFrame, gaia_sources: pl.DataFrame
) -> pl.DataFrame:
    """Build the frontend host visualization records."""
    return build_visualization_records(hosts, systems, gaia_sources)


@task(name="check_host_visualization")
def check_host_visualization(records: pl.DataFrame) -> None:
    """Check the expected spatial coverage of the artifact."""
    status_counts = dict(records.group_by("position_status").len().iter_rows())

    expect(
        "host_visualization_position_status_counts", status_counts, EXPECTED_POSITION_STATUS_COUNTS
    )


@task(name="write_host_visualization")
def write_host_visualization(records: pl.DataFrame) -> Path:
    """Publish records as an Arrow IPC file for the frontend."""
    output = get_settings().data_root / "frontend" / HOST_VISUALIZATION_FILENAME

    output.parent.mkdir(parents=True, exist_ok=True)
    records.write_ipc(output, compression="uncompressed")

    return output


@flow(name="build-host-visualization")
def build_host_visualization() -> Path:
    """Publish the frontend exoplanet-host visualization artifact."""
    paths = resolve_host_visualization_inputs()
    hosts, systems, gaia_sources = load_host_visualization_inputs(paths)

    records = build_host_visualization_table(hosts, systems, gaia_sources)
    check_host_visualization(records)
    return write_host_visualization(records)
