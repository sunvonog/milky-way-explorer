import polars as pl
import pytest

from app.domain.visualization import (
    HOST_VISUALIZATION_COLUMNS,
    build_host_visualization_records,
)

EXPECTED_COLUMNS = (
    "host_id",
    "host_name",
    "gaia_source_id",
    "planet_count",
    "archive_planet_count",
    "planet_count_matches_archive",
    "is_circumbinary",
    "position_status",
    "distance_pc",
    "distance_method",
    "distance_quality",
    "heliocentric_x_pc",
    "heliocentric_y_pc",
    "heliocentric_z_pc",
    "galactocentric_x_kpc",
    "galactocentric_y_kpc",
    "galactocentric_z_kpc",
    "phot_g_mean_magnitude",
    "bp_rp_color",
)


VisualizationInputs = tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]


@pytest.fixture
def visualization_inputs() -> VisualizationInputs:
    hosts = pl.DataFrame(
        {
            # Deliberately unsorted to test deterministic output.
            "host_id": [
                "nea:host:gamma",
                "nea:host:alpha",
                "nea:host:beta",
            ],
            "host_name": ["Gamma", "Alpha", "Beta"],
            "gaia_source_id": [None, 101, 202],
            "is_circumbinary": [False, False, True],
        },
        schema_overrides={"gaia_source_id": pl.Int64},
    )

    systems = pl.DataFrame(
        {
            "host_id": ["nea:host:beta", "nea:host:gamma", "nea:host:alpha"],
            "planet_count": [1, 4, 2],
            "archive_planet_count": [1, 4, 3],
            "planet_count_matches_archive": [True, True, False],
        }
    )

    gaia_sources = pl.DataFrame(
        {
            "gaia_source_id": [202, 101],
            "distance_pc": [None, 10.0],
            "distance_method": ["unavailable", "inverse_parallax"],
            "distance_quality": [
                "unavailable",
                "snr_ge_5_ruwe_acceptable",
            ],
            "heliocentric_x_pc": [None, 10.0],
            "heliocentric_y_pc": [None, 0.0],
            "heliocentric_z_pc": [None, 0.0],
            "galactocentric_x_kpc": [None, -8.112],
            "galactocentric_y_kpc": [None, 0.0],
            "galactocentric_z_kpc": [None, 0.0208],
            "phot_g_mean_magnitude": [12.0, 7.2],
            "bp_rp_color": [None, 0.8],
        },
        schema_overrides={
            "gaia_source_id": pl.Int64,
            "distance_pc": pl.Float64,
            "heliocentric_x_pc": pl.Float64,
            "heliocentric_y_pc": pl.Float64,
            "heliocentric_z_pc": pl.Float64,
            "galactocentric_x_kpc": pl.Float64,
            "galactocentric_y_kpc": pl.Float64,
            "galactocentric_z_kpc": pl.Float64,
            "phot_g_mean_magnitude": pl.Float64,
            "bp_rp_color": pl.Float64,
        },
    )

    return hosts, systems, gaia_sources


def test_builds_one_visualization_record_per_host(
    visualization_inputs: VisualizationInputs,
) -> None:
    hosts, systems, gaia_sources = visualization_inputs

    records = build_host_visualization_records(hosts, systems, gaia_sources)

    assert HOST_VISUALIZATION_COLUMNS == EXPECTED_COLUMNS
    assert records.columns == list(EXPECTED_COLUMNS)
    assert records["host_id"].to_list() == ["nea:host:alpha", "nea:host:beta", "nea:host:gamma"]


def test_combines_catalogue_and_spatial_fields(visualization_inputs: VisualizationInputs) -> None:
    hosts, systems, gaia_sources = visualization_inputs

    records = build_host_visualization_records(hosts, systems, gaia_sources)

    alpha = records.filter(pl.col("host_id") == "nea:host:alpha").row(0, named=True)

    assert alpha["host_name"] == "Alpha"
    assert alpha["gaia_source_id"] == 101
    assert alpha["planet_count"] == 2
    assert alpha["archive_planet_count"] == 3
    assert alpha["planet_count_matches_archive"] is False
    assert alpha["distance_pc"] == 10.0
    assert alpha["distance_method"] == "inverse_parallax"
    assert alpha["heliocentric_x_pc"] == 10.0
    assert alpha["galactocentric_x_kpc"] == -8.112
    assert alpha["phot_g_mean_magnitude"] == 7.2
    assert alpha["bp_rp_color"] == 0.8


def test_explains_why_hosts_have_no_renderable_position(
    visualization_inputs: VisualizationInputs,
) -> None:
    hosts, systems, gaia_sources = visualization_inputs

    records = build_host_visualization_records(hosts, systems, gaia_sources)

    statuses = records.select("host_id", "position_status").to_dicts()

    assert statuses == [
        {"host_id": "nea:host:alpha", "position_status": "available"},
        {"host_id": "nea:host:beta", "position_status": "no_accepted_distance"},
        {"host_id": "nea:host:gamma", "position_status": "no_exact_gaia_source"},
    ]


def test_retains_unpositioned_hosts_with_null_spatial_fields(
    visualization_inputs: VisualizationInputs,
) -> None:
    hosts, systems, gaia_source = visualization_inputs

    records = build_host_visualization_records(hosts, systems, gaia_source)

    gamma = records.filter(pl.col("host_id") == "nea:host:gamma").row(0, named=True)

    assert gamma["gaia_source_id"] is None
    assert gamma["distance_pc"] is None
    assert gamma["distance_method"] is None
    assert gamma["heliocentric_x_pc"] is None
    assert gamma["galactocentric_x_kpc"] is None
