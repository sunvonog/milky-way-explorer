from app.config import REPO_ROOT
from app.domain.exoplanets import build_hosts
from app.domain.gaia import (
    build_gaia_host_ids,
    build_gaia_host_sources,
    plan_gaia_host_batches,
)
from app.loaders import gaia
from app.loaders.gaia import load as load_gaia
from app.loaders.pscomppars import load

PSCOMPPARS_SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"
GAIA_HOST_SNAPSHOT = REPO_ROOT / "data" / "raw" / "gaia_hosts" / "current"


def test_current_gaia_host_snapshot_contract() -> None:
    frame = gaia.load(GAIA_HOST_SNAPSHOT)

    assert len(list((GAIA_HOST_SNAPSHOT / "batches").glob("gaia-host-*.csv"))) == 9
    assert frame.height == 4396
    assert frame["gaia_source_id"].n_unique() == 4396
    assert int(frame["is_valid"].sum()) == 4396


def test_current_snapshot_has_expected_gaia_host_ids() -> None:
    staging = load(PSCOMPPARS_SNAPSHOT)
    hosts = build_hosts(staging)

    gaia_host_ids = build_gaia_host_ids(hosts)

    assert gaia_host_ids.height == 4396
    assert gaia_host_ids["gaia_source_id"].null_count() == 0
    assert gaia_host_ids["gaia_source_id"].n_unique() == gaia_host_ids.height
    assert gaia_host_ids["gaia_source_id"].is_sorted()


def test_current_snapshot_fits_into_nine_batches() -> None:
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


def test_build_gaia_host_sources_matches_current_snapshot() -> None:
    staging = load_gaia(GAIA_HOST_SNAPSHOT)

    sources = build_gaia_host_sources(staging)

    method_counts = dict(sources.group_by("distance_method").len().iter_rows())

    assert sources.height == 4396
    assert sources["gaia_source_id"].n_unique() == 4396
    assert sources["distance_pc"].null_count() == 109
    assert sources["heliocentric_x_pc"].null_count() == 109
    assert sources["heliocentric_y_pc"].null_count() == 109
    assert sources["heliocentric_z_pc"].null_count() == 109
    assert sources["galactocentric_x_kpc"].null_count() == 109
    assert sources["galactocentric_y_kpc"].null_count() == 109
    assert sources["galactocentric_z_kpc"].null_count() == 109
    assert method_counts == {"gaia_gspphot": 3887, "inverse_parallax": 400, "unavailable": 109}
    assert "is_valid" not in sources.columns
