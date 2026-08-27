"""Build the processed Gaia density-cell artifact."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from app.artifacts import GAIA_DENSITY_CELLS_FILENAME
from app.config import get_settings
from app.domain.density import build_gaia_density_grid
from app.domain.gaia import build_gaia_background_sources
from app.loaders import gaia_background as gaia_background_loader
from app.runtime.flow import flow, task
from app.sources.snapshot import snapshot_dir


@task(name="resolve_gaia_background_snapshot")
def resolve_gaia_background_snapshot() -> Path:
    path = snapshot_dir(get_settings().raw_root, gaia_background_loader.SOURCE)

    if not path.is_dir():
        raise FileNotFoundError(f"missing Gaia background snapshot: {path}")

    return path


@task(name="load_gaia_background_snapshot")
def load_gaia_background_snapshot(path: Path) -> pl.DataFrame:
    return gaia_background_loader.load(path)


@task(name="build_gaia_background_sources")
def build_gaia_background_source_table(staging: pl.DataFrame) -> pl.DataFrame:
    return build_gaia_background_sources(staging)


@task(name="build_gaia_density_grids")
def build_gaia_density_tables(sources: pl.DataFrame) -> pl.DataFrame:
    settings = get_settings()

    if not settings.gaia_density_grid_sizes:
        raise ValueError("gaia_density_grid_sizes must contain at least one grid size")

    grids = [
        build_gaia_density_grid(
            sources, grid_size=grid_size, extent_kpc=settings.gaia_density_extent_kpc
        )
        for grid_size in settings.gaia_density_grid_sizes
    ]

    cells = pl.concat(grids, how="vertical").sort("grid_level", "cell_x", "cell_y")

    if cells.is_empty():
        raise ValueError("Gaia background produced no density cells")

    return cells


@task(name="write_gaia_density_cells")
def write_gaia_density_cells(cells: pl.DataFrame) -> Path:
    output = get_settings().processed_root / GAIA_DENSITY_CELLS_FILENAME

    output.parent.mkdir(parents=True, exist_ok=True)
    cells.write_parquet(output)

    return output


@flow(name="build-gaia-density")
def build_gaia_density() -> Path:
    """Publish density grids from the committed Gaia background snapshot."""
    snapshot = resolve_gaia_background_snapshot()
    staging = load_gaia_background_snapshot(snapshot)
    sources = build_gaia_background_source_table(staging)
    cells = build_gaia_density_tables(sources)

    return write_gaia_density_cells(cells)
