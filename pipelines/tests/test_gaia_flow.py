from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest

from app.config import override_settings, reset_settings
from app.domain.exoplanets import build_hosts
from app.flows.gaia import (
    EXOPLANET_HOSTS_FILENAME,
    GAIA_HOST_IDS_FILENAME,
    build_gaia_host_manifest,
)
from app.loaders.pscomppars import load

REPO_ROOT = Path(__file__).resolve().parents[2]
PSCOMPPARS_SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"


@pytest.fixture
def data_root(tmp_path: Path) -> Iterator[Path]:
    reset_settings()
    override_settings(
        data_root=tmp_path, log_dir=tmp_path / "logs", log_level="WARNING", log_color=False
    )

    processed = tmp_path / "processed"
    processed.mkdir(parents=True)

    staging = load(PSCOMPPARS_SNAPSHOT)
    hosts = build_hosts(staging)
    hosts.write_parquet(processed / EXOPLANET_HOSTS_FILENAME)

    yield tmp_path

    reset_settings()


def test_build_gaia_host_manifest_publishes_distinct_ids(data_root: Path):
    path = build_gaia_host_manifest()

    assert path == data_root / "processed" / GAIA_HOST_IDS_FILENAME
    assert path.is_file()

    host_ids = pl.read_parquet(path)

    assert host_ids.schema == pl.Schema({"gaia_source_id": pl.Int64})
    assert host_ids.height == 4396
    assert host_ids["gaia_source_id"].null_count() == 0
    assert host_ids["gaia_source_id"].n_unique() == host_ids.height
    assert host_ids["gaia_source_id"].is_sorted()
