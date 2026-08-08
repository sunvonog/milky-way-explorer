"""Gaia host-enrichment workflows."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from app.config import get_settings
from app.domain.gaia import build_gaia_host_ids
from app.runtime.checks import expect
from app.runtime.flow import flow, task

EXOPLANET_HOSTS_FILENAME = "exoplanet_hosts.parquet"
GAIA_HOST_IDS_FILENAME = "gaia_host_ids.parquet"
EXPECTED_GAIA_HOST_IDS = 4396


@task(name="resolve_exoplanet_hosts")
def resolve_exoplanet_hosts() -> Path:
    path = get_settings().processed_root / EXOPLANET_HOSTS_FILENAME

    if not path.is_file():
        raise FileNotFoundError(f"missing exoplanet host table: {path}")

    return path


@task(name="load_exoplanet_hosts")
def load_exoplanet_hosts(path: Path) -> pl.DataFrame:
    return pl.read_parquet(path)


@task(name="extract_gaia_host_ids")
def extract_gaia_host_ids(hosts: pl.DataFrame) -> pl.DataFrame:
    return build_gaia_host_ids(hosts)


@task(name="check_gaia_host_ids")
def check_gaia_host_ids(host_ids: pl.DataFrame):
    expect(
        "gaia_host_ids",
        host_ids.height,
        EXPECTED_GAIA_HOST_IDS,
    )


@task(name="write_gaia_host_ids")
def write_gaia_host_ids(host_ids: pl.DataFrame) -> Path:
    output = get_settings().processed_root / GAIA_HOST_IDS_FILENAME
    output.parent.mkdir(parents=True, exist_ok=True)
    host_ids.write_parquet(output)
    return output


@flow(name="build-gaia-host-manifest")
def build_gaia_host_manifest() -> Path:
    """Publish the distinct Gaia IDs required for exact host retrieval."""
    hosts_path = resolve_exoplanet_hosts()
    hosts = load_exoplanet_hosts(hosts_path)
    host_ids = extract_gaia_host_ids(hosts)

    check_gaia_host_ids(host_ids)
    return write_gaia_host_ids(host_ids)
