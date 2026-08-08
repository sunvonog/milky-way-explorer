import shutil
from pathlib import Path

import polars as pl
import pytest

from app.config import REPO_ROOT, override_settings, reset_settings
from app.flows.exoplanets import (
    OUTPUT_FILENAMES,
    SNAPSHOT_FILENAME,
    SOURCE,
    build_exoplanets,
)
from app.sources.snapshot import snapshot_dir

SOURCE_SNAPSHOT = REPO_ROOT / "data" / "raw" / SOURCE / "current" / SNAPSHOT_FILENAME

EXPECTED_FILENAMES = {
    "planets": "exoplanets.parquet",
    "hosts": "exoplanet_hosts.parquet",
    "systems": "exoplanet_systems.parquet",
    "invalid_rows": "review_invalid_exoplanet_rows.parquet",
    "stellar_conflicts": "review_host_stellar_conflicts.parquet",
    "system_count_mismatches": "review_system_planet_count_mismatches.parquet",
}

EXPECTED_ROWS = {
    "planets": 6336,
    "hosts": 4749,
    "systems": 4749,
    "invalid_rows": 0,
    "stellar_conflicts": 596,
    "system_count_mismatches": 14,
}


@pytest.fixture
def data_root(tmp_path: Path):
    reset_settings()
    override_settings(
        data_root=tmp_path, log_dir=tmp_path / "logs", log_level="WARNING", log_color=False
    )

    destination = snapshot_dir(tmp_path / "raw", SOURCE)
    destination.mkdir(parents=True)

    shutil.copy2(SOURCE_SNAPSHOT, destination / SNAPSHOT_FILENAME)

    yield tmp_path
    reset_settings()


def test_output_filenames_are_stable():
    assert OUTPUT_FILENAMES == EXPECTED_FILENAMES


def test_build_writes_expected_parquet_files(data_root: Path):
    paths = build_exoplanets()

    assert set(paths) == set(OUTPUT_FILENAMES)

    for key, filename in OUTPUT_FILENAMES.items():
        assert paths[key] == data_root / "processed" / filename
        assert paths[key].is_file()

        frame = pl.read_parquet(paths[key])
        assert frame.height == EXPECTED_ROWS[key]


def test_published_foreign_keys_are_valid(data_root: Path):
    paths = build_exoplanets()

    planets = pl.read_parquet(paths["planets"])
    hosts = pl.read_parquet(paths["hosts"])
    systems = pl.read_parquet(paths["systems"])

    missing_hosts = planets.join(hosts.select("host_id"), on="host_id", how="anti")
    missing_systems = planets.join(systems.select("system_id"), on="system_id", how="anti")

    assert missing_hosts.is_empty()
    assert missing_systems.is_empty()
