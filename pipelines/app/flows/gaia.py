"""Gaia host-enrichment and background-retrieval workflows."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl

from app.artifacts import (
    EXOPLANET_HOSTS_FILENAME,
    GAIA_HOST_IDS_FILENAME,
    GAIA_HOST_SOURCES_FILENAME,
)
from app.config import get_settings
from app.domain.gaia import (
    GaiaBackgroundBatch,
    GaiaHostBatch,
    build_gaia_host_ids,
    plan_gaia_background_batches,
    plan_gaia_host_batches,
)
from app.domain.gaia import build_gaia_host_sources as build_gaia_host_source_records
from app.loaders import gaia as gaia_loader
from app.runtime.checks import expect
from app.runtime.flow import flow, task
from app.sources.gaia import (
    GaiaBatchDownload,
    download_gaia_background_batch,
    download_gaia_host_batch,
)
from app.sources.snapshot import snapshot_dir, snapshot_directory

GAIA_HOST_SOURCE = "gaia_hosts"
GAIA_HOST_ORIGIN = "Gaia DR3 async TAP"
GAIA_HOST_BATCH_SIZE = 500
GAIA_HOST_BATCHES_DIRECTORY = "batches"

GAIA_BACKGROUND_SOURCE = "gaia_background"
GAIA_BACKGROUND_ORIGIN = "Gaia DR3 async TAP random-index subset"
GAIA_BACKGROUND_BATCHES_DIRECTORY = "batches"

EXPECTED_GAIA_HOST_IDS = 4396
EXPECTED_GAIA_HOST_SOURCES = 4396
EXPECTED_UNAVAILABLE_GAIA_DISTANCE = 109


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
def check_gaia_host_ids(host_ids: pl.DataFrame) -> None:
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


@task(name="resolve_gaia_host_ids")
def resolve_gaia_host_ids() -> Path:
    path = get_settings().processed_root / GAIA_HOST_IDS_FILENAME

    if not path.is_file():
        raise FileNotFoundError(f"missing Gaia host-ID manifest: {path}")

    return path


@task(name="load_gaia_host_ids")
def load_gaia_host_ids(path: Path) -> pl.DataFrame:
    return pl.read_parquet(path)


@task(name="plan_gaia_host_downloads")
def plan_gaia_host_downloads(host_ids: pl.DataFrame) -> list[GaiaHostBatch]:
    batches = plan_gaia_host_batches(host_ids, batch_size=GAIA_HOST_BATCH_SIZE)

    if not batches:
        raise ValueError("Gaia host-ID manifest must not be empty")

    return batches


@task(name="plan_gaia_background_downloads")
def plan_gaia_background_downloads() -> list[GaiaBackgroundBatch]:
    settings = get_settings()

    return plan_gaia_background_batches(
        source_count=settings.gaia_background_source_count,
        batch_size=settings.gaia_background_batch_size,
    )


@task(name="download_gaia_host_batch", key="batch_number")
def fetch_gaia_host_batch(
    batch_number: int, source_ids: tuple[int, ...], staging_root: Path
) -> GaiaBatchDownload:
    batch = GaiaHostBatch(batch_number=batch_number, source_ids=source_ids)
    destination = staging_root / GAIA_HOST_BATCHES_DIRECTORY / f"gaia-host-{batch_number:04d}.csv"

    return download_gaia_host_batch(batch, destination)


@task(name="download_gaia_background_batch", key="batch_number")
def fetch_gaia_background_batch(
    batch_number: int, random_index_start: int, random_index_stop: int, staging_root: Path
) -> GaiaBatchDownload:
    batch = GaiaBackgroundBatch(
        batch_number=batch_number,
        random_index_start=random_index_start,
        random_index_stop=random_index_stop,
    )
    destination = (
        staging_root / GAIA_BACKGROUND_BATCHES_DIRECTORY / f"gaia-background-{batch_number:04d}.csv"
    )

    return download_gaia_background_batch(batch, destination)


@flow(name="build-gaia-host-manifest")
def build_gaia_host_manifest() -> Path:
    """Publish the distinct Gaia IDs required for exact host retrieval."""
    hosts_path = resolve_exoplanet_hosts()
    hosts = load_exoplanet_hosts(hosts_path)
    host_ids = extract_gaia_host_ids(hosts)

    check_gaia_host_ids(host_ids)
    return write_gaia_host_ids(host_ids)


@task(name="resolve_gaia_host_snapshot")
def resolve_gaia_host_snapshot() -> Path:
    path = snapshot_dir(get_settings().raw_root, GAIA_HOST_SOURCE)

    if not path.is_dir():
        raise FileNotFoundError(f"missing Gaia host snapshot: {path}")

    return path


@task(name="load_gaia_host_snapshot")
def load_gaia_host_snapshot(path: Path) -> pl.DataFrame:
    return gaia_loader.load(path)


@task(name="build_gaia_host_sources")
def build_gaia_host_source_table(staging: pl.DataFrame) -> pl.DataFrame:
    return build_gaia_host_source_records(staging)


@task(name="check_gaia_host_sources")
def check_gaia_host_sources(sources: pl.DataFrame) -> None:
    expect("gaia_host_sources", sources.height, EXPECTED_GAIA_HOST_SOURCES)

    unavailable = sources.filter(pl.col("distance_method") == "unavailable").height

    expect("gaia_host_sources_without_distance", unavailable, EXPECTED_UNAVAILABLE_GAIA_DISTANCE)


@task(name="write_gaia_host_sources")
def write_gaia_host_sources(sources: pl.DataFrame) -> Path:
    output = get_settings().processed_root / GAIA_HOST_SOURCES_FILENAME

    output.parent.mkdir(parents=True, exist_ok=True)
    sources.write_parquet(output)

    return output


@flow(name="build-gaia-hosts")
def build_gaia_hosts() -> Path:
    """Publish exact Gaia source records from the committed snapshot."""
    snapshot = resolve_gaia_host_snapshot()
    staging = load_gaia_host_snapshot(snapshot)
    sources = build_gaia_host_source_table(staging)

    check_gaia_host_sources(sources)
    return write_gaia_host_sources(sources)


@flow(name="refresh-gaia-hosts")
def refresh_gaia_hosts() -> Path:
    """Download and publish exact Gaia records for known exoplanet hosts."""
    manifest_path = resolve_gaia_host_ids()
    host_ids = load_gaia_host_ids(manifest_path)
    batches = plan_gaia_host_downloads(host_ids)

    settings = get_settings()
    settings.raw_root.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(
        prefix=".gaia-host-refresh-", dir=settings.raw_root
    ) as temporary_directory:
        staging_root = Path(temporary_directory)

        for batch in batches:
            fetch_gaia_host_batch(
                batch_number=batch.batch_number,
                source_ids=batch.source_ids,
                staging_root=staging_root,
            )

        return snapshot_directory(
            staging_root,
            GAIA_HOST_SOURCE,
            settings.raw_root,
            origin=GAIA_HOST_ORIGIN,
            fetched_online=True,
        )


@flow(name="refresh-gaia-background")
def refresh_gaia_background() -> Path:
    """Download and atomically publish a repeatable Gaia background subset."""
    batches = plan_gaia_background_downloads()

    settings = get_settings()
    settings.raw_root.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(
        prefix=".gaia-background-refresh-", dir=settings.raw_root
    ) as temporary_directory:
        staging_root = Path(temporary_directory)

        for batch in batches:
            fetch_gaia_background_batch(
                batch_number=batch.batch_number,
                random_index_start=batch.random_index_start,
                random_index_stop=batch.random_index_stop,
                staging_root=staging_root,
            )

        return snapshot_directory(
            staging_root,
            GAIA_BACKGROUND_SOURCE,
            settings.raw_root,
            origin=GAIA_BACKGROUND_ORIGIN,
            fetched_online=True,
        )
