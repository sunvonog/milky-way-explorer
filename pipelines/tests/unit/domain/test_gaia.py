import polars as pl
import pytest
from polars.testing import assert_frame_equal

from app.config import REPO_ROOT
from app.domain.exoplanets import build_hosts
from app.domain.gaia import GaiaHostBatch, build_gaia_host_ids, plan_gaia_host_batches
from app.loaders.pscomppars import load

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
