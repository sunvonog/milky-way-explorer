from pathlib import Path

import polars as pl
import pytest

from app.artifacts import GAIA_DENSITY_CELLS_FILENAME, GAIA_DENSITY_VISUALIZATION_FILENAME
from app.config import override_settings
from app.domain.density import DENSITY_COLUMNS, DENSITY_VISUALIZATION_COLUMNS
from app.flows.density import build_gaia_density
from app.sources.gaia import GAIA_BACKGROUND_COLUMNS


@pytest.fixture
def data_root(isolated_data_root: Path) -> Path:
    override_settings(
        strict_checks=True, gaia_density_grid_sizes=(2, 4), gaia_density_extent_kpc=20.0
    )
    return isolated_data_root


def _background_row(
    source_id: int,
    *,
    longitude_deg: float,
    ra_deg: float = 10.0,
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "ra": ra_deg,
        "dec": 20.0,
        "l": longitude_deg,
        "b": 0.0,
        "parallax": 5.0,
        "parallax_over_error": 50.0,
        "phot_g_mean_mag": 12.0,
        "bp_rp": 0.8,
        "ruwe": 1.0,
        "distance_gspphot": 200.0,
    }


def _write_background_snapshot(data_root: Path) -> Path:
    snapshot = data_root / "raw" / "gaia_background" / "current"
    batches = snapshot / "batches"
    batches.mkdir(parents=True)

    rows = [
        _background_row(1, longitude_deg=0.0),
        _background_row(2, longitude_deg=90.0),
        # Invalid right ascension: retained by the loader but excluded
        # before coordinate transformation and density aggregation
        _background_row(3, longitude_deg=180.0, ra_deg=400.0),
    ]

    (
        pl.DataFrame(rows)
        .select(GAIA_BACKGROUND_COLUMNS)
        .write_csv(batches / "gaia-background-0001.csv")
    )

    return snapshot


def test_build_gaia_density_publishes_all_configured_grid(data_root: Path) -> None:
    _write_background_snapshot(data_root)

    path = build_gaia_density()

    assert path == (data_root / "processed" / GAIA_DENSITY_CELLS_FILENAME)
    assert path.is_file()

    cells = pl.read_parquet(path)

    assert cells.columns == list(DENSITY_COLUMNS)
    assert cells["grid_level"].unique().sort().to_list() == [2, 4]

    totals = dict(cells.group_by("grid_level").agg(pl.col("source_count").sum()).iter_rows())

    assert totals == {2: 2, 4: 2}

    visualization_path = data_root / "frontend" / GAIA_DENSITY_VISUALIZATION_FILENAME

    assert visualization_path.is_file()

    visualization = pl.read_ipc(visualization_path)

    assert visualization.columns == list(DENSITY_VISUALIZATION_COLUMNS)
    assert visualization["grid_level"].unique().sort().to_list() == [2, 4]
    assert visualization["cell_size_kpc"].unique().sort().to_list() == [10.0, 20.0]


def test_build_gaia_density_requires_committed_snapshot(data_root: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Gaia background snapshot"):
        build_gaia_density()
