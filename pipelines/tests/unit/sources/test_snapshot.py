import hashlib
import json
from pathlib import Path

import pytest

from app.sources.snapshot import snapshot_dir, snapshot_directory, snapshot_local


def test_snapshot_is_single_current_dir_and_overwrites(tmp_path: Path) -> None:
    src = tmp_path / "src.csv"
    src.write_text("name\nSirius\n", encoding="utf-8")
    raw = tmp_path / "raw"

    snapshot_local(src, "demo", raw)
    snapshot_local(src, "demo", raw)  # overwrite must not accumulate

    versions = list((raw / "demo").iterdir())
    assert versions == [snapshot_dir(raw, "demo")]  # exactly one 'current' dir


def test_checksum_matches_bytes(tmp_path: Path) -> None:
    src = tmp_path / "src.csv"
    src.write_bytes(b"hello")
    raw = tmp_path / "raw"
    snapshot_local(src, "demo", raw)

    meta = json.loads((snapshot_dir(raw, "demo") / "snapshot.json").read_text())
    assert meta["sha256"] == hashlib.sha256(b"hello").hexdigest()


def test_directory_snapshot_publishes_nested_files_and_manifest(tmp_path: Path) -> None:
    staged = tmp_path / "staged"
    batches = staged / "batches"
    batches.mkdir(parents=True)

    first = b"source_id\n7\n"
    second = b"source_id\n42\n"

    (batches / "gaia-host-0001.csv").write_bytes(first)
    (batches / "gaia-host-0002.csv").write_bytes(second)

    raw = tmp_path / "raw"

    current = snapshot_directory(
        staged, "gaia_hosts", raw, origin="Gaia DR3 async TAP", fetched_online=True
    )

    assert current == snapshot_dir(raw, "gaia_hosts")
    assert (current / "batches" / "gaia-host-0001.csv").read_bytes() == first
    assert (current / "batches" / "gaia-host-0002.csv").read_bytes() == second

    metadata = json.loads((current / "snapshot.json").read_text())

    assert metadata["source"] == "gaia_hosts"
    assert metadata["origin"] == "Gaia DR3 async TAP"
    assert metadata["fetched_online"] is True
    assert metadata["bytes"] == len(first) + len(second)
    assert len(metadata["sha256"]) == 64
    assert metadata["files"] == [
        {
            "path": "batches/gaia-host-0001.csv",
            "sha256": hashlib.sha256(first).hexdigest(),
            "bytes": len(first),
        },
        {
            "path": "batches/gaia-host-0002.csv",
            "sha256": hashlib.sha256(second).hexdigest(),
            "bytes": len(second),
        },
    ]


def test_directory_snapshot_removes_files_from_previous_version(tmp_path: Path) -> None:
    raw = tmp_path / "raw"

    first = tmp_path / "first"
    first.mkdir()
    (first / "old.csv").write_text("old", encoding="utf-8")

    second = tmp_path / "second"
    second.mkdir()
    (second / "new.csv").write_text("new", encoding="utf-8")

    snapshot_directory(first, "demo", raw, origin="test", fetched_online=False)

    current = snapshot_directory(second, "demo", raw, origin="test", fetched_online=False)

    assert not (current / "old.csv").exists()
    assert (current / "new.csv").is_file()


def test_empty_directory_does_not_replace_current_snapshot(tmp_path: Path) -> None:
    raw = tmp_path / "raw"

    valid = tmp_path / "valid"
    valid.mkdir()
    (valid / "data.csv").write_text("valid", encoding="utf-8")

    current = snapshot_directory(valid, "demo", raw, origin="test", fetched_online=False)

    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(ValueError, match="must contain at least one file"):
        snapshot_directory(empty, "demo", raw, origin="test", fetched_online=False)

    assert (current / "data.csv").read_text(encoding="utf-8") == "valid"
