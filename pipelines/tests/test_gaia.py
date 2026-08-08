from pathlib import Path

import polars as pl
from polars.testing import assert_frame_equal

from app.exoplanets import build_hosts
from app.gaia import build_gaia_host_ids
from app.loaders.pscomppars import load

REPO_ROOT = Path(__file__).resolve().parents[2]
PSCOMPPARS_SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"


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
