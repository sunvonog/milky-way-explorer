import json
from pathlib import Path

from app.services.builds import BuildInfo, PublishedBuild, read_current_build, resolve_current_build


def _write_manifest(path: Path, build_id: str) -> dict[str, object]:
    manifest: dict[str, object] = {
        "build_id": build_id,
        "created_at": "2026-08-28T12:00:00Z",
        "source_snapshots": {"gaia": "DR3"},
        "row_counts": {"processed/stars.parquet": 605},
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")

    return manifest


def test_read_current_build_missing(tmp_path: Path) -> None:
    assert read_current_build(tmp_path / "builds" / "current.json") is None


def test_read_current_build_valid(tmp_path: Path) -> None:
    pointer = tmp_path / "builds" / "current.json"
    pointer.parent.mkdir(parents=True)
    manifest = {
        "build_id": "2026-07-24T00:00:00Z-abc123",
        "created_at": "2026-07-24T00:00:00Z",
        "source_snapshots": {"gaia": "DR3"},
        "row_counts": {"named_stars": 451},
    }
    pointer.write_text(json.dumps(manifest))

    info = read_current_build(pointer)
    assert info == BuildInfo.model_validate(manifest)


def test_resolve_current_build_returns_versioned_roots(tmp_path: Path) -> None:
    builds_root = tmp_path / "builds"
    build_root = builds_root / "build-001"

    manifest = _write_manifest(build_root / "manifest.json", "build-001")
    _write_manifest(builds_root / "current.json", "build-001")

    published = resolve_current_build(builds_root)

    assert published == PublishedBuild(
        info=BuildInfo.model_validate(manifest), root=build_root.resolve()
    )
    assert published.processed_root == build_root.resolve() / "processed"
    assert published.frontend_root == build_root.resolve() / "frontend"


def test_resolve_current_build_requires_published_directory(tmp_path: Path) -> None:
    builds_root = tmp_path / "builds"
    _write_manifest(builds_root / "current.json", "missing-build")

    assert resolve_current_build(builds_root) is None


def test_resolve_current_build_rejects_unsafe_build_id(tmp_path: Path) -> None:
    builds_root = tmp_path / "builds"
    _write_manifest(builds_root / "current.json", "../escape")

    assert resolve_current_build(builds_root) is None


def test_resolve_current_build_requires_matching_manifest(tmp_path: Path) -> None:
    builds_root = tmp_path / "builds"

    _write_manifest(builds_root / "current.json", "build-001")
    _write_manifest(builds_root / "build-001" / "manifest.json", "different-build")

    assert resolve_current_build(builds_root) is None
