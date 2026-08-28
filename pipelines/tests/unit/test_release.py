import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from app.artifacts import GAIA_DENSITY_VISUALIZATION_FILENAME
from app.release import (
    RELEASE_ARTIFACTS,
    RELEASE_SNAPSHOT_SOURCES,
    publish_release,
    resolve_release_artifacts,
)


def _write_artifact(data_root: Path, relative_path: Path) -> Path:
    path = data_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)

    frame = pl.DataFrame({"row_index": [1, 2]})

    if path.suffix == ".parquet":
        frame.write_parquet(path)
    elif path.suffix == ".arrow":
        frame.write_ipc(path)
    else:
        raise ValueError(f"unsupported test artifact: {path}")

    return path


def _write_snapshot_manifests(data_root: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}

    for source in RELEASE_SNAPSHOT_SOURCES:
        checksum = hashlib.sha256(source.encode()).hexdigest()
        checksums[source] = checksum

        path = data_root / "raw" / source / "current" / "snapshot.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"source": source, "sha256": checksum}), encoding="utf-8")

    return checksums


def test_resolves_only_allowlist_release_artifacts(tmp_path: Path) -> None:
    expected = {
        relative_path: _write_artifact(tmp_path, relative_path)
        for relative_path in RELEASE_ARTIFACTS
    }

    extra = _write_artifact(tmp_path, Path("processed/review_invalid_exoplanet_rows.parquet"))

    actual = resolve_release_artifacts(tmp_path)

    assert actual == expected
    assert extra not in actual.values()


def test_rejects_incomplete_release(tmp_path: Path) -> None:
    missing = Path("frontend") / GAIA_DENSITY_VISUALIZATION_FILENAME

    for relative_path in RELEASE_ARTIFACTS:
        if relative_path != missing:
            _write_artifact(tmp_path, relative_path)

    with pytest.raises(FileNotFoundError, match="frontend/milky-way-density.arrow"):
        resolve_release_artifacts(tmp_path)


def test_publish_release_writes_versioned_bundle_and_switches_pointer(tmp_path: Path) -> None:
    for relative_path in RELEASE_ARTIFACTS:
        _write_artifact(tmp_path, relative_path)

    extra = _write_artifact(tmp_path, Path("processed/review_invalid_exoplanet_rows.parquet"))
    source_snapshots = _write_snapshot_manifests(tmp_path)
    created_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)

    manifest = publish_release(tmp_path, build_id="build-001", created_at=created_at)

    build_root = tmp_path / "builds" / "build-001"
    pointer = tmp_path / "builds" / "current.json"

    assert manifest.build_id == "build-001"
    assert manifest.created_at == created_at
    assert manifest.source_snapshots == source_snapshots

    published_files = {
        path.relative_to(build_root).as_posix() for path in build_root.rglob("*") if path.is_file()
    }

    assert published_files == {*(path.as_posix() for path in RELEASE_ARTIFACTS), "manifest.json"}
    assert not (build_root / extra.relative_to(tmp_path)).exists()

    expected_rows = {relative_path.as_posix(): 2 for relative_path in RELEASE_ARTIFACTS}
    assert manifest.row_counts == expected_rows

    pointer_payload = json.loads(pointer.read_text(encoding="utf-8"))
    manifest_payload = json.loads((build_root / "manifest.json").read_text(encoding="utf-8"))

    assert pointer_payload == json.loads(manifest.model_dump_json())
    assert manifest_payload == pointer_payload

    for metadata in pointer_payload["artifacts"].values():
        assert metadata["bytes"] > 0
        assert len(metadata["sha256"]) == 64
        assert metadata["rows"] == 2


def test_incomplete_release_does_not_replace_current_pointer(tmp_path: Path) -> None:
    pointer = tmp_path / "builds" / "current.json"
    pointer.parent.mkdir(parents=True)

    previous_pointer = '{"build_id": "stable-build"}\n'
    pointer.write_text(previous_pointer, encoding="utf-8")

    missing = RELEASE_ARTIFACTS[-1]

    for relative_path in RELEASE_ARTIFACTS:
        if relative_path != missing:
            _write_artifact(tmp_path, relative_path)

    _write_snapshot_manifests(tmp_path)

    with pytest.raises(FileNotFoundError):
        publish_release(
            tmp_path, build_id="broken-build", created_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
        )

    assert pointer.read_text(encoding="utf-8") == previous_pointer
    assert not (tmp_path / "builds" / "broken-build").exists()


@pytest.mark.parametrize("build_id", ["", "../escape", "nested/build"])
def test_publish_release_rejects_unsafe_build_ids(tmp_path: Path, build_id: str) -> None:
    for relative_path in RELEASE_ARTIFACTS:
        _write_artifact(tmp_path, relative_path)

    _write_snapshot_manifests(tmp_path)

    with pytest.raises(ValueError, match="build_id"):
        publish_release(
            tmp_path, build_id=build_id, created_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
        )
