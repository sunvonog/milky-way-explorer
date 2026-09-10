from pathlib import Path

import polars as pl
import pytest

from app.artifacts import GAIA_OVERVIEW_FILENAME
from app.config import override_settings
from app.domain.gaia_overview import GAIA_OVERVIEW_COLUMNS
from app.flows.gaia_overview import build_gaia_overview_artifact


@pytest.mark.parametrize("max_points", [1, 10])
def test_overview_round_trip(isolated_data_root: Path, max_points: int) -> None:
    override_settings(
        gaia_overview_max_points=max_points, gaia_overview_seed=42, gaia_overview_extent_kpc=20.0
    )

    batches = isolated_data_root / "raw" / "gaia_background" / "current" / "batches"
    batches.mkdir(parents=True)

    (batches / "gaia-background-0001.csv").write_text(
        "source_id,ra,dec,l,b,parallax,parallax_over_error,phot_g_mean_mag,bp_rp,ruwe,distance_gspphot\n"
        "3946945413106333696,10,20,0,0,5,50,12,0.8,1,200\n"
        "3946945413106333697,10,20,90,0,5,3,,,1,\n"
        "3946945413106333698,400,20,180,0,5,50,12,0.8,1,200\n"
        "3946945413106333699,10,20,270,0,5,1,12,0.8,1,\n",
        encoding="utf-8",
    )

    path = build_gaia_overview_artifact()
    records = pl.read_ipc(path)

    assert path == isolated_data_root / "frontend" / GAIA_OVERVIEW_FILENAME
    assert records.columns == list(GAIA_OVERVIEW_COLUMNS)
    assert records.height == min(max_points, 2)
    assert records["gaia_source_id"].dtype == pl.Int64
    assert records["gaia_source_id"].n_unique() == records.height

    expected = {
        3946945413106333696: ("baseline", "gaia_gspphot", 200.0, 0.8),
        3946945413106333697: ("exploratory", "inverse_parallax", 200.0, None),
    }

    for row in records.iter_rows(named=True):
        assert (
            row["distance_tier"],
            row["distance_method"],
            row["distance_pc"],
            row["bp_rp_color"],
        ) == expected[row["gaia_source_id"]]

    for column in ("galactocentric_x_kpc", "galactocentric_y_kpc", "galactocentric_z_kpc"):
        assert records[column].dtype == pl.Float64
        assert records[column].null_count() == 0
        assert records[column].is_finite().all()
