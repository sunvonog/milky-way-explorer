import json
from hashlib import file_digest
from pathlib import Path

import polars as pl

from app.artifacts import GAIA_OVERVIEW_FILENAME, GAIA_OVERVIEW_METADATA_FILENAME
from app.config import Settings, get_settings
from app.domain.gaia import GALACTOCENTRIC_PARAMETER_SET, build_gaia_background_sources
from app.domain.gaia_overview import (
    GAIA_OVERVIEW_COLUMNS,
    GAIA_OVERVIEW_SAMPLING_METHOD,
    GaiaOverviewResult,
    build_gaia_overview,
)
from app.loaders import gaia_background as gaia_background_loader
from app.runtime.flow import flow, task
from app.runtime.logging import bound_log
from app.sources.snapshot import snapshot_dir


@task(name="write_gaia_overview")
def write_gaia_overview(records: pl.DataFrame) -> Path:
    output = get_settings().data_root / "frontend" / GAIA_OVERVIEW_FILENAME
    output.parent.mkdir(parents=True, exist_ok=True)

    records.select(GAIA_OVERVIEW_COLUMNS).write_ipc(output, compression="uncompressed")

    return output


@task(name="write_gaia_overview_metadata")
def write_gaia_overview_metadata(
    artifact: Path,
    *,
    result: GaiaOverviewResult,
    snapshot_sha256: str,
    loaded_count: int,
    settings: Settings,
) -> Path:
    with artifact.open("rb") as file:
        artifact_sha256 = file_digest(file, "sha256").hexdigest()

    metadata = {
        "schema_version": 1,
        "artifact": {
            "filename": artifact.name,
            "sha256": artifact_sha256,
        },
        "source": {"name": gaia_background_loader.SOURCE, "snapshot_sha256": snapshot_sha256},
        "sampling": {
            "method": GAIA_OVERVIEW_SAMPLING_METHOD,
            "seed": settings.gaia_overview_seed,
            "max_points": settings.gaia_overview_max_points,
        },
        "coordinates": {
            "frame": "galactocentric",
            "parameter_set": GALACTOCENTRIC_PARAMETER_SET,
            "unit": "kpc",
            "extent_kpc": settings.gaia_overview_extent_kpc,
        },
        "counts": {
            "loaded": loaded_count,
            "invalid": loaded_count - result.input_count,
            "processed": result.input_count,
            "excluded": result.excluded_count,
            "eligible": result.eligible_count,
            "sampled_out": result.sampled_out_count,
            "selected": result.selected_count,
        },
        "selected_by_tier": dict(result.records.group_by("distance_tier").len().iter_rows()),
    }

    output = artifact.with_name(GAIA_OVERVIEW_METADATA_FILENAME)
    output.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return output


@flow(name="build-gaia-overview")
def build_gaia_overview_artifact() -> Path:
    settings = get_settings()
    snapshot = snapshot_dir(settings.raw_root, gaia_background_loader.SOURCE)

    snapshot_metadata = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8"))

    if snapshot_metadata.get("source") != gaia_background_loader.SOURCE:
        raise ValueError("snapshot metadata does not identify gaia_background")

    snapshot_sha256 = snapshot_metadata.get("sha256")

    if not isinstance(snapshot_sha256, str) or not snapshot_sha256:
        raise ValueError("Gaia background snapshot has no sha256")

    staging = gaia_background_loader.load(snapshot)
    sources = build_gaia_background_sources(staging)

    result = build_gaia_overview(
        sources,
        extent_kpc=settings.gaia_overview_extent_kpc,
        max_points=settings.gaia_overview_max_points,
        seed=settings.gaia_overview_seed,
    )

    bound_log(
        loaded_count=staging.height,
        invalid_source_count=staging.height - result.input_count,
        processed_count=result.input_count,
        eligible_count=result.eligible_count,
        excluded_count=result.excluded_count,
        selected_count=result.selected_count,
        sampled_out_count=result.sampled_out_count,
    ).info("Gaia overview selection complete")

    if result.selected_count == 0:
        raise ValueError("Gaia background produced no eligible overview stars")

    output = write_gaia_overview(result.records)
    write_gaia_overview_metadata(
        output,
        result=result,
        snapshot_sha256=snapshot_sha256,
        loaded_count=staging.height,
        settings=settings,
    )

    return output
