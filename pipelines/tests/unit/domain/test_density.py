import polars as pl
import pytest

from app.domain.density import (
    DENSITY_COLUMNS,
    DENSITY_VISUALIZATION_COLUMNS,
    build_gaia_density_grid,
    build_gaia_density_visualization_records,
)


def test_aggregates_sources_into_non_empty_cell():
    sources = pl.DataFrame(
        {
            "galactocentric_x_kpc": [-1.8, -1.1, 0.2, 0.7],
            "galactocentric_y_kpc": [-1.2, -1.9, 0.8, 0.1],
            "phot_g_mean_magnitude": [10.0, 11.0, 12.0, None],
            "bp_rp_color": [1.0, None, 0.5, 1.5],
        }
    )

    actual = build_gaia_density_grid(sources, grid_size=4, extent_kpc=2.0)

    assert actual.columns == list(DENSITY_COLUMNS)
    assert actual.select(
        "grid_level",
        "cell_x",
        "cell_y",
        "source_count",
        "mean_bp_rp",
    ).to_dicts() == [
        {"grid_level": 4, "cell_x": 0, "cell_y": 0, "source_count": 2, "mean_bp_rp": 1.0},
        {"grid_level": 4, "cell_x": 2, "cell_y": 2, "source_count": 2, "mean_bp_rp": 1.0},
    ]

    rows = actual.to_dicts()

    assert rows[0]["weighted_brightness"] == pytest.approx(
        10 ** (-0.4 * 10.0) + 10 ** (-0.4 * 11.0), rel=1e-6
    )
    assert rows[1]["weighted_brightness"] == pytest.approx(10 ** (-0.4 * 12.0), rel=1e-6)


def test_uses_half_open_grid_boundaries_and_ignores_unpositioned_sources():
    sources = pl.DataFrame(
        {
            "galactocentric_x_kpc": [-2.0, 1.999, 2.0, -2.001, None, 0.0],
            "galactocentric_y_kpc": [-2.0, 1.999, 0.0, 0.0, 0.0, None],
            "phot_g_mean_magnitude": [10.0] * 6,
            "bp_rp_color": [1.0] * 6,
        },
        schema_overrides={"galactocentric_x_kpc": pl.Float64, "galactocentric_y_kpc": pl.Float64},
    )

    actual = build_gaia_density_grid(sources, grid_size=4, extent_kpc=2.0)

    assert actual.select("cell_x", "cell_y", "source_count").to_dicts() == [
        {"cell_x": 0, "cell_y": 0, "source_count": 1},
        {"cell_x": 3, "cell_y": 3, "source_count": 1},
    ]


def test_publishes_compact_density_schema():
    sources = pl.DataFrame(
        {
            "galactocentric_x_kpc": [0.0],
            "galactocentric_y_kpc": [0.0],
            "phot_g_mean_magnitude": [10.0],
            "bp_rp_color": [None],
        },
        schema_overrides={"bp_rp_color": pl.Float64},
    )

    actual = build_gaia_density_grid(sources, grid_size=512, extent_kpc=20.0)

    assert actual.schema == pl.Schema(
        {
            "grid_level": pl.UInt16,
            "cell_x": pl.Int32,
            "cell_y": pl.Int32,
            "source_count": pl.UInt32,
            "weighted_brightness": pl.Float32,
            "mean_bp_rp": pl.Float32,
        }
    )
    assert actual["mean_bp_rp"].item() is None


@pytest.mark.parametrize("grid_size", [0, -1])
def test_rejects_non_positive_grid_size(grid_size: int):
    with pytest.raises(ValueError, match="grid_size must be positive"):
        build_gaia_density_grid(pl.DataFrame(), grid_size=grid_size, extent_kpc=20.0)


@pytest.mark.parametrize("extent_kpc", [0.0, -1.0])
def test_rejects_non_positive_extent(extent_kpc: float):
    with pytest.raises(ValueError, match="extent_kpc must be positive"):
        build_gaia_density_grid(pl.DataFrame(), grid_size=128, extent_kpc=extent_kpc)


def test_density_visualization_adds_physical_cell_geometry():
    cells = pl.DataFrame(
        {
            "grid_level": [4, 4],
            "cell_x": [0, 2],
            "cell_y": [1, 3],
            "source_count": [10, 20],
            "weighted_brightness": [0.5, 1.0],
            "mean_bp_rp": [0.8, None],
        },
        schema_overrides={
            "grid_level": pl.UInt16,
            "cell_x": pl.Int32,
            "cell_y": pl.Int32,
            "source_count": pl.UInt32,
            "weighted_brightness": pl.Float32,
            "mean_bp_rp": pl.Float32,
        },
    )

    actual: pl.DataFrame = build_gaia_density_visualization_records(cells, extent_kpc=2.0)

    assert actual.columns == list(DENSITY_VISUALIZATION_COLUMNS)

    assert actual.select("cell_center_x_kpc", "cell_center_y_kpc", "cell_size_kpc").to_dicts() == [
        {
            "cell_center_x_kpc": -1.5,
            "cell_center_y_kpc": -0.5,
            "cell_size_kpc": 1.0,
        },
        {"cell_center_x_kpc": 0.5, "cell_center_y_kpc": 1.5, "cell_size_kpc": 1.0},
    ]
