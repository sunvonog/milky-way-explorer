"""NASA exoplanet catalogue workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from logly import Logger

from app.artifacts import (
    EXOPLANET_HOSTS_FILENAME,
    EXOPLANET_SYSTEMS_FILENAME,
    EXOPLANETS_FILENAME,
)
from app.config import get_settings
from app.domain.exoplanets import (
    build_hosts,
    build_planets,
    build_systems,
    review_host_stellar_conflicts,
    review_invalid_planet_rows,
    review_system_planet_count_mismatches,
)
from app.loaders import pscomppars
from app.runtime.checks import expect
from app.runtime.flow import flow, get_run, get_task, task
from app.runtime.logging import bound_log
from app.sources.nasa_exoplanet_archive import pscomppars_url
from app.sources.snapshot import snapshot_dir, snapshot_url

SOURCE = "nasa_pscomppars"
SNAPSHOT_FILENAME = "pscomppars.csv"

OUTPUT_FILENAMES = {
    "planets": EXOPLANETS_FILENAME,
    "hosts": EXOPLANET_HOSTS_FILENAME,
    "systems": EXOPLANET_SYSTEMS_FILENAME,
    "invalid_rows": "review_invalid_exoplanet_rows.parquet",
    "stellar_conflicts": "review_host_stellar_conflicts.parquet",
    "system_count_mismatches": "review_system_planet_count_mismatches.parquet",
}

EXPECTED_ROW_COUNTS = {
    "planets": 6336,
    "hosts": 4749,
    "systems": 4749,
    "invalid_rows": 0,
    "stellar_conflicts": 596,
    "system_count_mismatches": 14,
}


@dataclass(frozen=True, slots=True)
class ExoplanetTables:
    planets: pl.DataFrame
    hosts: pl.DataFrame
    systems: pl.DataFrame
    invalid_rows: pl.DataFrame
    stellar_conflicts: pl.DataFrame
    system_count_mismatches: pl.DataFrame

    def as_dict(self) -> dict[str, pl.DataFrame]:
        return {
            "planets": self.planets,
            "hosts": self.hosts,
            "systems": self.systems,
            "invalid_rows": self.invalid_rows,
            "stellar_conflicts": self.stellar_conflicts,
            "system_count_mismatches": self.system_count_mismatches,
        }


def _ctx_log(**fields: object) -> Logger:
    run = get_run()
    return bound_log(
        run_id=run.run_id if run else "-",
        flow=run.flow_name if run else "refresh-pscomppars",
        task=get_task() or "-",
        **fields,
    )


@task(name="snapshot_nasa_pscomppars")
def snapshot_nasa_pscomppars() -> Path:
    """Download the selected PSCompPars columns into a new snapshot."""
    settings = get_settings()

    path = snapshot_url(
        pscomppars_url(), SOURCE, settings.raw_root, filename=SNAPSHOT_FILENAME, timeout=120.0
    )

    _ctx_log(
        source=SOURCE,
        path=str(path),
        bytes=path.stat().st_size,
    ).info("snapshotted NASA PSCompPars")

    return path


@task(name="resolve_pscomppars_snapshot")
def resolve_pscomppars_snapshot() -> Path:
    settings = get_settings()
    path = snapshot_dir(settings.raw_root, SOURCE) / SNAPSHOT_FILENAME

    if not path.is_file():
        raise FileNotFoundError(f"missing PSCompPars snapshot: {path}")

    _ctx_log(
        source=SOURCE,
        path=str(path),
        bytes=path.stat().st_size,
    ).info("resolved NASA PSCompPars snapshot")

    return path


@task(name="load_pscomppars")
def load_pscomppars(path: Path) -> pl.DataFrame:
    staging = pscomppars.load(path)

    _ctx_log(
        rows=staging.height,
        valid=int(staging["is_valid"].sum()),
        invalid=staging.height - int(staging["is_valid"].sum()),
    ).info("loaded NASA PSCompPars staging data")

    return staging


@task(name="build_exoplanet_tables")
def build_exoplanet_tables(staging: pl.DataFrame) -> ExoplanetTables:
    planets = build_planets(staging)
    hosts = build_hosts(staging)
    systems = build_systems(hosts, planets)

    tables = ExoplanetTables(
        planets=planets,
        hosts=hosts,
        systems=systems,
        invalid_rows=review_invalid_planet_rows(staging),
        stellar_conflicts=review_host_stellar_conflicts(staging),
        system_count_mismatches=review_system_planet_count_mismatches(systems),
    )

    _ctx_log(planets=planets.height, hosts=hosts.height, systems=systems.height).info(
        "built exoplanet domain tables"
    )

    return tables


@task(name="check_exoplanet_expectations")
def check_exoplanet_expectations(
    tables: ExoplanetTables,
) -> None:
    for name, frame in tables.as_dict().items():
        expect(
            f"exoplanet_{name}",
            frame.height,
            EXPECTED_ROW_COUNTS[name],
        )


@task(name="write_exoplanet_outputs")
def write_exoplanet_outputs(tables: ExoplanetTables) -> dict[str, Path]:
    output_root = get_settings().processed_root
    output_root.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    for name, frame in tables.as_dict().items():
        path = output_root / OUTPUT_FILENAMES[name]
        frame.write_parquet(path)
        paths[name] = path

        _ctx_log(
            output=name,
            path=str(path),
            rows=frame.height,
            bytes=path.stat().st_size,
        ).info("wrote exoplanet parquet")

    return paths


@flow(name="build-exoplanets")
def build_exoplanets() -> dict[str, Path]:
    """Build and publish PSCompPars domain and review tables."""
    snapshot = resolve_pscomppars_snapshot()
    staging = load_pscomppars(snapshot)
    tables = build_exoplanet_tables(staging)

    check_exoplanet_expectations(tables)
    return write_exoplanet_outputs(tables)


@flow(name="refresh-pscomppars")
def refresh_pscomppars() -> None:
    """Maintainer-only refresh of the NASA exoplanet catalogue."""
    snapshot_nasa_pscomppars()
