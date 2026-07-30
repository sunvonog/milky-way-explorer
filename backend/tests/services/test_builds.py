import json

from app.services.builds import BuildInfo, read_current_build


def test_read_current_build_missing(tmp_path):
    assert read_current_build(tmp_path / "builds" / "current.json") is None


def test_read_current_build_valid(tmp_path):
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
