import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest

import app.flows.gaia as gaia_flow
from app.artifacts import (
    EXOPLANET_HOSTS_FILENAME,
    GAIA_HOST_IDS_FILENAME,
    GAIA_HOST_SOURCES_FILENAME,
)
from app.config import REPO_ROOT, override_settings, reset_settings
from app.domain.exoplanets import build_hosts
from app.domain.gaia import GaiaHostBatch
from app.flows.gaia import (
    build_gaia_host_manifest,
)
from app.loaders.pscomppars import load
from app.sources.gaia import GaiaBatchDownload

PSCOMPPARS_SNAPSHOT = REPO_ROOT / "data" / "raw" / "nasa_pscomppars" / "current" / "pscomppars.csv"
GAIA_HOST_SNAPSHOT = REPO_ROOT / "data" / "raw" / "gaia_hosts" / "current"


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


def _write_gaia_manifest(data_root: Path, source_ids: list[int]) -> Path:
    path = data_root / "processed" / GAIA_HOST_IDS_FILENAME

    pl.DataFrame(
        {"gaia_source_id": source_ids},
        schema={"gaia_source_id": pl.Int64},
    ).write_parquet(path)

    return path


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


def test_refresh_gaia_hosts_publishes_all_batches(data_root: Path, monkeypatch: pytest.MonkeyPatch):
    _write_gaia_manifest(data_root, [7, 10, 20, 30, 42])

    monkeypatch.setattr(gaia_flow, "GAIA_HOST_BATCH_SIZE", 2)

    def fake_download(batch: GaiaHostBatch, destination: Path) -> GaiaBatchDownload:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            "source_id\n" + "\n".join(str(source_id) for source_id in batch.source_ids) + "\n",
            encoding="utf-8",
        )

        return GaiaBatchDownload(
            batch_number=batch.batch_number, job_id=f"job-{batch.batch_number}", path=destination
        )

    monkeypatch.setattr(gaia_flow, "download_gaia_host_batch", fake_download)

    current = gaia_flow.refresh_gaia_hosts()

    assert current == data_root / "raw" / "gaia_hosts" / "current"

    batch_paths = sorted((current / "batches").glob("*.csv"))

    assert [path.name for path in batch_paths] == [
        "gaia-host-0001.csv",
        "gaia-host-0002.csv",
        "gaia-host-0003.csv",
    ]

    metadata = json.loads((current / "snapshot.json").read_text(encoding="utf-8"))

    assert metadata["source"] == "gaia_hosts"
    assert metadata["fetched_online"] is True
    assert [entry["path"] for entry in metadata["files"]] == [
        "batches/gaia-host-0001.csv",
        "batches/gaia-host-0002.csv",
        "batches/gaia-host-0003.csv",
    ]


def test_refresh_gaia_hosts_preserves_current_snapshot_when_a_batch_fails(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_gaia_manifest(data_root, [7, 42])

    current = data_root / "raw" / "gaia_hosts" / "current"
    current.mkdir(parents=True)
    marker = current / "existing.csv"
    marker.write_text("existing snapshot", encoding="utf-8")

    monkeypatch.setattr(gaia_flow, "GAIA_HOST_BATCH_SIZE", 1)

    def failing_download(batch: GaiaHostBatch, destination: Path) -> GaiaBatchDownload:
        if batch.batch_number == 2:
            raise RuntimeError("simulated Gaia failure")

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("source_id\n7\n", encoding="utf-8")

        return GaiaBatchDownload(
            batch_number=batch.batch_number, job_id=f"job-{batch.batch_number}", path=destination
        )

    monkeypatch.setattr(gaia_flow, "download_gaia_host_batch", failing_download)

    with pytest.raises(RuntimeError, match="simulated Gaia failure"):
        gaia_flow.refresh_gaia_hosts()

    assert marker.read_text(encoding="utf-8") == "existing snapshot"
    assert list(current.iterdir()) == [marker]


def test_build_gaia_hosts_publishes_source_table(data_root: Path):
    snapshot = data_root / "raw" / "gaia_hosts" / "current"
    shutil.copytree(GAIA_HOST_SNAPSHOT, snapshot)

    path = gaia_flow.build_gaia_hosts()

    assert path == (data_root / "processed" / GAIA_HOST_SOURCES_FILENAME)
    assert path.is_file()

    sources = pl.read_parquet(path)

    method_counts = dict(sources.group_by("distance_method").len().iter_rows())

    assert sources.height == 4396
    assert sources["gaia_source_id"].n_unique() == 4396
    assert sources["distance_pc"].null_count() == 109
    assert method_counts == {"gaia_gspphot": 3887, "inverse_parallax": 400, "unavailable": 109}


def test_build_gaia_hosts_requires_committed_snapshot(data_root: Path):
    with pytest.raises(FileNotFoundError, match="Gaia host snapshot"):
        gaia_flow.build_gaia_hosts()
