import polars as pl
import pytest

from app.config import REPO_ROOT
from app.domain.exoplanets import build_hosts, build_planets, build_systems
from app.domain.gaia import build_gaia_host_sources
from app.domain.visualization import build_host_visualization_records
from app.loaders.gaia import load as load_gaia
from app.loaders.pscomppars import load as load_pscomppars

PSCOMPPARS_SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"
GAIA_HOST_SNAPSHOT = REPO_ROOT / "data" / "raw" / "gaia_hosts" / "current"


@pytest.fixture(scope="module")
def current_snapshot_records() -> pl.DataFrame:
    exoplanet_staging = load_pscomppars(PSCOMPPARS_SNAPSHOT)
    hosts = build_hosts(exoplanet_staging)
    planets = build_planets(exoplanet_staging)
    systems = build_systems(hosts, planets)

    gaia_staging = load_gaia(GAIA_HOST_SNAPSHOT)
    gaia_sources = build_gaia_host_sources(gaia_staging)

    return build_host_visualization_records(hosts, systems, gaia_sources)


def test_current_snapshots_have_expected_visualization_coverage(
    current_snapshot_records: pl.DataFrame,
) -> None:
    records = current_snapshot_records

    status_counts = {
        row["position_status"]: row["len"]
        for row in records.group_by("position_status").len().to_dicts()
    }

    assert records.height == 4749
    assert records["host_id"].n_unique() == records.height
    assert records["host_id"].is_sorted()

    assert status_counts == {
        "available": 4287,
        "no_accepted_distance": 109,
        "no_exact_gaia_source": 353,
    }

    assert records["planet_count"].null_count() == 0
    assert records["archive_planet_count"].null_count() == 0
    assert records["planet_count_matches_archive"].null_count() == 0


def test_only_available_hosts_have_spatial_coordinates(
    current_snapshot_records: pl.DataFrame,
) -> None:
    records = current_snapshot_records

    coordinate_columns = (
        "heliocentric_x_pc",
        "heliocentric_y_pc",
        "heliocentric_z_pc",
        "galactocentric_x_kpc",
        "galactocentric_y_kpc",
        "galactocentric_z_kpc",
    )

    available = records.filter(pl.col("position_status") == "available")
    unavailable = records.filter(pl.col("position_status") != "available")

    assert available.height == 4287
    assert unavailable.height == 462

    for column in coordinate_columns:
        assert available[column].null_count() == 0
        assert unavailable[column].null_count() == unavailable.height
