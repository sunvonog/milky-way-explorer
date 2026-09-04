import polars as pl
import pytest

from app.domain.gaia import (
    GAIA_BACKGROUND_SOURCE_COLUMNS,
    GaiaBackgroundBatch,
    add_gaia_background_distance,
    add_gaia_distance,
    build_gaia_background_sources,
    plan_gaia_background_batches,
)


def test_builds_density_ready_background_sources() -> None:
    staging = pl.DataFrame(
        {
            # Deliberately unsorted; source 4 is invalid and must be omitted.
            "gaia_source_id": [3, 1, 4, 2, 5],
            "galactic_longitude_deg": [0.0, 0.0, 0.0, 90.0, 180.0],
            "galactic_latitude_deg": [0.0, 0.0, 0.0, 0.0, 0.0],
            "distance_gspphot_pc": [None, 25.0, 30.0, None, None],
            "parallax_mas": [10.0, 10.0, 10.0, 10.0, 10],
            "parallax_over_error": [2.5, 10.0, 10.0, 10.0, 1.5],
            "ruwe": [1.0, 1.0, 1.0, 1.0, 1.0],
            "phot_g_mean_magnitude": [13.0, 10.0, 9.0, 11.0, 14.0],
            "bp_rp_color": [1.3, 0.5, 0.2, 0.8, 1.5],
            "is_valid": [True, True, False, True, True],
            "source": ["gaia_background"] * 5,
        },
        schema_overrides={"gaia_source_id": pl.Int64},
    )

    actual: pl.DataFrame = build_gaia_background_sources(staging)

    assert actual.columns == list(GAIA_BACKGROUND_SOURCE_COLUMNS)
    assert actual["gaia_source_id"].to_list() == [1, 2, 3, 5]

    assert actual.select(
        "gaia_source_id", "distance_pc", "distance_method", "distance_quality", "distance_tier"
    ).to_dicts() == [
        {
            "gaia_source_id": 1,
            "distance_pc": 25.0,
            "distance_method": "gaia_gspphot",
            "distance_quality": "positive_gspphot_estimate",
            "distance_tier": "baseline",
        },
        {
            "gaia_source_id": 2,
            "distance_pc": 100.0,
            "distance_method": "inverse_parallax",
            "distance_quality": "snr_ge_5_ruwe_acceptable",
            "distance_tier": "baseline",
        },
        {
            "gaia_source_id": 3,
            "distance_pc": 100,
            "distance_method": "inverse_parallax",
            "distance_quality": "snr_2_to_5_ruwe_acceptable",
            "distance_tier": "exploratory",
        },
        {
            "gaia_source_id": 5,
            "distance_pc": None,
            "distance_method": "unavailable",
            "distance_quality": "unavailable",
            "distance_tier": "unavailable",
        },
    ]

    positioned = actual.filter(pl.col("distance_pc").is_not_null())
    unavailable = actual.filter(pl.col("distance_pc").is_null()).row(0, named=True)

    assert positioned.height == 3

    for column in ("galactocentric_x_kpc", "galactocentric_y_kpc", "galactocentric_z_kpc"):
        assert positioned[column].null_count() == 0
        assert unavailable[column] is None

    assert actual["phot_g_mean_magnitude"].to_list() == [10.0, 11.0, 13.0, 14.0]
    assert actual["bp_rp_color"].to_list() == [0.5, 0.8, 1.3, 1.5]


def test_background_distance_uses_the_shared_ruwe_threshold() -> None:
    staging = pl.DataFrame(
        {
            "gaia_source_id": [1, 2],
            "galactic_longitude_deg": [0.0, 0.0],
            "galactic_latitude_deg": [0.0, 0.0],
            "distance_gspphot_pc": [None, None],
            "parallax_mas": [10.0, 10.0],
            "parallax_over_error": [10.0, 10.0],
            "ruwe": [None, 1.4],
            "phot_g_mean_magnitude": [10.0, 10.0],
            "bp_rp_color": [0.5, 0.5],
            "is_valid": [True, True],
            "source": ["gaia_background", "gaia_background"],
        },
        schema_overrides={
            "gaia_source_id": pl.Int64,
            "ruwe": pl.Float64,
        },
    )

    actual = build_gaia_background_sources(staging)

    assert actual["distance_method"].to_list() == [
        "inverse_parallax",
        "unavailable",
    ]


def test_inverse_parallax_omits_bounds_for_invalid_parallax_error() -> None:
    frame = pl.DataFrame(
        {
            "distance_gspphot_pc": [None],
            "distance_gspphot_lower_pc": [None],
            "distance_gspphot_upper_pc": [None],
            "parallax_mas": [10.0],
            "parallax_error_mas": [-1.0],
            "parallax_over_error": [10.0],
            "ruwe": [1.0],
        }
    )

    actual = add_gaia_distance(frame).row(0, named=True)

    assert actual["distance_pc"] == pytest.approx(100.0)
    assert actual["distance_lower_pc"] is None
    assert actual["distance_upper_pc"] is None


def test_plans_contiguous_background_random_index_batches() -> None:
    actual: list[GaiaBackgroundBatch] = plan_gaia_background_batches(source_count=5, batch_size=2)

    assert actual == [
        GaiaBackgroundBatch(
            batch_number=1,
            random_index_start=0,
            random_index_stop=2,
        ),
        GaiaBackgroundBatch(batch_number=2, random_index_start=2, random_index_stop=4),
        GaiaBackgroundBatch(batch_number=3, random_index_start=4, random_index_stop=5),
    ]


@pytest.mark.parametrize(("source_count", "batch_size"), [(0, 2), (-1, 2), (5, 0), (5, -1)])
def test_background_batch_planner_rejects_invalid_sizes(source_count: int, batch_size: int) -> None:
    with pytest.raises(ValueError):
        plan_gaia_background_batches(source_count=source_count, batch_size=batch_size)


def test_background_distance_assigns_baseline_and_exploratory_tiers() -> None:
    frame = pl.DataFrame(
        {
            "distance_gspphot_pc": [25.0, None, None, None, None],
            "parallax_mas": [10.0, 10.0, 10.0, 10.0, 10.0],
            "parallax_over_error": [1.0, 5.0, 4.999, 2.0, 1.999],
            "ruwe": [1.0, 1.0, 1.0, None, 1.0],
        },
        schema_overrides={"ruwe": pl.Float64},
    )

    actual = add_gaia_background_distance(frame)

    assert actual.select(
        "distance_pc",
        "distance_method",
        "distance_quality",
        "distance_tier",
    ).to_dicts() == [
        {
            "distance_pc": 25.0,
            "distance_method": "gaia_gspphot",
            "distance_quality": "positive_gspphot_estimate",
            "distance_tier": "baseline",
        },
        {
            "distance_pc": 100.0,
            "distance_method": "inverse_parallax",
            "distance_quality": "snr_ge_5_ruwe_acceptable",
            "distance_tier": "baseline",
        },
        {
            "distance_pc": 100.0,
            "distance_method": "inverse_parallax",
            "distance_quality": "snr_2_to_5_ruwe_acceptable",
            "distance_tier": "exploratory",
        },
        {
            "distance_pc": 100.0,
            "distance_method": "inverse_parallax",
            "distance_quality": "snr_2_to_5_ruwe_acceptable",
            "distance_tier": "exploratory",
        },
        {
            "distance_pc": None,
            "distance_method": "unavailable",
            "distance_quality": "unavailable",
            "distance_tier": "unavailable",
        },
    ]
