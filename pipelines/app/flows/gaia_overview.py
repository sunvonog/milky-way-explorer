from pathlib import Path

import polars as pl

from app.artifacts import GAIA_OVERVIEW_FILENAME
from app.config import get_settings
from app.domain.gaia import build_gaia_background_sources
from app.domain.gaia_overview import GAIA_OVERVIEW_COLUMNS, build_gaia_overview
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


@flow(name="build-gaia-overview")
def build_gaia_overview_artifact() -> Path:
    settings = get_settings()
    snapshot = snapshot_dir(settings.raw_root, gaia_background_loader.SOURCE)

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

    return write_gaia_overview(result.records)
