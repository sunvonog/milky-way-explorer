import polars as pl
import pytest
from polars.testing import assert_frame_equal

from app.domain.gaia_overview import (
    build_gaia_overview,
    sample_gaia_overview,
    select_gaia_overview_sources,
)


@pytest.mark.parametrize(
    ("x", "y", "z", "tier", "expected"),
    [
        (-2.0, -2.0, 0.0, "baseline", True),
        (-1.999, -1.999, 3.0, "exploratory", True),
        (2.0, 0.0, 0.0, "baseline", False),
        (-2.001, 0.0, 0.0, "baseline", False),
        (0.0, 2.0, 0.0, "baseline", False),
        (0.0, -2.001, 0.0, "baseline", False),
        (None, 0.0, 0.0, "baseline", False),
        (float("nan"), 0.0, 0.0, "baseline", False),
        (0.0, float("inf"), 0.0, "baseline", False),
        (0.0, 0.0, None, "baseline", False),
        (0.0, 0.0, float("inf"), "baseline", False),
        (0.0, 0.0, 0.0, "unavailable", False),
        (0.0, 0.0, 0.0, None, False),
    ],
)
def test_selects_only_eligible_source(
    x: float | None, y: float | None, z: float | None, tier: str | None, expected: bool
) -> None:
    sources = pl.DataFrame(
        {
            "gaia_source_id": [1],
            "galactocentric_x_kpc": [x],
            "galactocentric_y_kpc": [y],
            "galactocentric_z_kpc": [z],
            "distance_tier": [tier],
            "phot_g_mean_magnitude": [None],
            "bp_rp_color": [None],
        },
        schema_overrides={
            "galactocentric_x_kpc": pl.Float64,
            "galactocentric_y_kpc": pl.Float64,
            "galactocentric_z_kpc": pl.Float64,
            "distance_tier": pl.String,
        },
    )

    actual = select_gaia_overview_sources(sources, extent_kpc=2.0)

    assert actual["gaia_source_id"].to_list() == ([1] if expected else [])


def test_sampling_is_repeatable_and_nested() -> None:
    sources = pl.DataFrame(
        {
            "gaia_source_id": [
                9007199254740999,
                9007199254740993,
                9007199254740997,
                9007199254740995,
            ],
            "bp_rp_color": [None, 0.5, 1.0, 1.5],
        },
        schema_overrides={"gaia_source_id": pl.Int64},
    )

    actual = sample_gaia_overview(sources, max_points=3, seed=42)

    assert actual["bp_rp_color"].to_list() == [0.5, 1.0, None]

    reordered = sample_gaia_overview(sources.reverse(), max_points=3, seed=42)
    assert_frame_equal(actual, reordered)

    smaller = sample_gaia_overview(sources, max_points=2, seed=42)
    assert_frame_equal(smaller, actual.head(2))


@pytest.mark.parametrize(("max_points", "expected_ids"), [(2, [5, 1]), (10, [5, 1, 3])])
def test_overview_filters_before_sampling_and_reports_counts(
    max_points: int, expected_ids: list[int]
) -> None:
    sources = pl.DataFrame(
        {
            "gaia_source_id": [1, 2, 3, 4, 5, 6],
            "galactocentric_x_kpc": [0.0, None, 1.0, 3.0, -1.0, 0.0],
            "galactocentric_y_kpc": [0.0] * 6,
            "galactocentric_z_kpc": [0.0] * 6,
            "distance_tier": [
                "baseline",
                "baseline",
                "exploratory",
                "baseline",
                "baseline",
                "unavailable",
            ],
        }
    )

    actual = build_gaia_overview(sources, extent_kpc=2.0, max_points=max_points, seed=42)

    assert actual.records["gaia_source_id"].to_list() == expected_ids
    assert actual.input_count == 6
    assert actual.eligible_count == 3
    assert actual.excluded_count == 3
    assert actual.selected_count == len(expected_ids)
    assert actual.sampled_out_count == 3 - len(expected_ids)
