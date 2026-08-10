import polars as pl
import pytest
from polars.testing import assert_frame_equal

from app.config import REPO_ROOT
from app.domain.exoplanets import build_hosts
from app.domain.gaia import (
    GaiaHostBatch,
    add_gaia_distance,
    add_heliocentric_coordinates,
    build_gaia_host_ids,
    build_gaia_host_sources,
    plan_gaia_host_batches,
)
from app.loaders.gaia import load as load_gaia
from app.loaders.pscomppars import load

PSCOMPPARS_SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"
GAIA_HOST_SNAPSHOT = REPO_ROOT / "data" / "raw" / "gaia_hosts" / "current"


def test_gaia_host_ids_are_non_null_unique_and_sorted():
    hosts = pl.DataFrame({"gaia_source_id": [42, None, 7, 42]}, schema={"gaia_source_id": pl.Int64})

    actual = build_gaia_host_ids(hosts)

    expected = pl.DataFrame({"gaia_source_id": [7, 42]}, schema={"gaia_source_id": pl.Int64})

    assert_frame_equal(actual, expected)


def test_current_snapshot_has_expected_gaia_host_ids():
    staging = load(PSCOMPPARS_SNAPSHOT)
    hosts = build_hosts(staging)

    gaia_host_ids = build_gaia_host_ids(hosts)

    assert gaia_host_ids.height == 4396
    assert gaia_host_ids["gaia_source_id"].null_count() == 0
    assert gaia_host_ids["gaia_source_id"].n_unique() == gaia_host_ids.height
    assert gaia_host_ids["gaia_source_id"].is_sorted()


def test_gaia_host_batches_are_deterministic():
    host_ids = pl.DataFrame(
        {
            "gaia_source_id": [50, 10, 40, 20, 30],
        },
        schema={"gaia_source_id": pl.Int64},
    )

    batches = plan_gaia_host_batches(host_ids, batch_size=2)

    assert batches == [
        GaiaHostBatch(batch_number=1, source_ids=(10, 20)),
        GaiaHostBatch(batch_number=2, source_ids=(30, 40)),
        GaiaHostBatch(batch_number=3, source_ids=(50,)),
    ]


@pytest.mark.parametrize("batch_size", [0, -1])
def test_gaia_host_batches_reject_invalid_size(batch_size: int) -> None:
    host_ids = pl.DataFrame(
        {"gaia_source_id": [10]},
        schema={"gaia_source_id": pl.Int64},
    )

    with pytest.raises(ValueError, match="batch_size must be positive"):
        plan_gaia_host_batches(host_ids, batch_size=batch_size)


def test_current_snapshot_fits_into_nine_batches():
    staging = load(PSCOMPPARS_SNAPSHOT)
    hosts = build_hosts(staging)
    host_ids = build_gaia_host_ids(hosts)

    batches = plan_gaia_host_batches(host_ids, batch_size=500)

    assert len(batches) == 9
    assert [len(batch.source_ids) for batch in batches] == [
        500,
        500,
        500,
        500,
        500,
        500,
        500,
        500,
        396,
    ]

    flattened = [source_id for batch in batches for source_id in batch.source_ids]

    assert flattened == host_ids["gaia_source_id"].to_list()


def test_gaia_distance_prefers_gspphot_then_inverse_parallax():
    frame = pl.DataFrame(
        {
            "distance_gspphot_pc": [25.0, None, None],
            "distance_gspphot_lower_pc": [20.0, None, None],
            "distance_gspphot_upper_pc": [30.0, None, None],
            "parallax_mas": [10.0, 10.0, 10.0],
            "parallax_error_mas": [1.0, 1.0, 4.0],
            "parallax_over_error": [10.0, 10.0, 2.5],
            "ruwe": [1.0, 1.0, 1.0],
        }
    )

    actual = add_gaia_distance(frame).to_dicts()

    assert actual[0]["distance_pc"] == 25.0
    assert actual[0]["distance_lower_pc"] == 20.0
    assert actual[0]["distance_upper_pc"] == 30.0
    assert actual[0]["distance_method"] == "gaia_gspphot"
    assert actual[0]["distance_quality"] == "positive_gspphot_estimate"

    assert actual[1]["distance_pc"] == pytest.approx(100.0)
    assert actual[1]["distance_lower_pc"] == pytest.approx(1000.0 / 11.0)
    assert actual[1]["distance_upper_pc"] == pytest.approx(1000.0 / 9.0)
    assert actual[1]["distance_method"] == "inverse_parallax"
    assert actual[1]["distance_quality"] == "snr_ge_5_ruwe_acceptable"

    assert actual[2]["distance_pc"] is None
    assert actual[2]["distance_lower_pc"] is None
    assert actual[2]["distance_upper_pc"] is None
    assert actual[2]["distance_method"] == "unavailable"
    assert actual[2]["distance_quality"] == "unavailable"


def test_inverse_parallax_accepts_missing_ruwe_but_rejects_threshold():
    frame = pl.DataFrame(
        {
            "distance_gspphot_pc": [None, None],
            "distance_gspphot_lower_pc": [None, None],
            "distance_gspphot_upper_pc": [None, None],
            "parallax_mas": [10.0, 10.0],
            "parallax_error_mas": [1.0, 1.0],
            "parallax_over_error": [10.0, 10.0],
            "ruwe": [None, 1.4],
        }
    )

    actual = add_gaia_distance(frame)

    assert actual["distance_method"].to_list() == ["inverse_parallax", "unavailable"]


def test_build_gaia_host_sources_matches_current_snapshot():
    staging = load_gaia(GAIA_HOST_SNAPSHOT)

    sources = build_gaia_host_sources(staging)

    method_counts = dict(sources.group_by("distance_method").len().iter_rows())

    assert sources.height == 4396
    assert sources["gaia_source_id"].n_unique() == 4396
    assert sources["distance_pc"].null_count() == 109
    assert sources["heliocentric_x_pc"].null_count() == 109
    assert sources["heliocentric_y_pc"].null_count() == 109
    assert sources["heliocentric_z_pc"].null_count() == 109
    assert method_counts == {"gaia_gspphot": 3887, "inverse_parallax": 400, "unavailable": 109}
    assert "is_valid" not in sources.columns


def test_heliocentric_coordinates_use_sun_as_origin():
    frame = pl.DataFrame(
        {
            "galactic_longitude_deg": [
                0.0,
                90.0,
                0.0,
                180.0,
                0.0,
            ],
            "galactic_latitude_deg": [
                0.0,
                0.0,
                90.0,
                0.0,
                0.0,
            ],
            "distance_pc": [10.0, 10.0, 10.0, 10.0, None],
        }
    )

    rows = add_heliocentric_coordinates(frame).to_dicts()

    assert rows[0]["heliocentric_x_pc"] == pytest.approx(10.0)
    assert rows[0]["heliocentric_y_pc"] == pytest.approx(0.0, abs=1e-12)
    assert rows[0]["heliocentric_z_pc"] == pytest.approx(0.0, abs=1e-12)

    assert rows[1]["heliocentric_x_pc"] == pytest.approx(0.0, abs=1e-12)
    assert rows[1]["heliocentric_y_pc"] == pytest.approx(10.0)
    assert rows[1]["heliocentric_z_pc"] == pytest.approx(0.0, abs=1e-12)

    assert rows[2]["heliocentric_x_pc"] == pytest.approx(0.0, abs=1e-12)
    assert rows[2]["heliocentric_y_pc"] == pytest.approx(0.0, abs=1e-12)
    assert rows[2]["heliocentric_z_pc"] == pytest.approx(10.0)

    assert rows[3]["heliocentric_x_pc"] == pytest.approx(-10.0)
    assert rows[3]["heliocentric_y_pc"] == pytest.approx(0.0, abs=1e-12)
    assert rows[3]["heliocentric_z_pc"] == pytest.approx(0.0, abs=1e-12)

    assert rows[4]["heliocentric_x_pc"] is None
    assert rows[4]["heliocentric_y_pc"] is None
    assert rows[4]["heliocentric_z_pc"] is None
