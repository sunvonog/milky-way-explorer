import json

from app.sources.snapshot import snapshot_dir, snapshot_local


def test_snapshot_is_single_current_dir_and_overwrites(tmp_path):
    src = tmp_path / "src.csv"
    src.write_text("name\nSirius\n", encoding="utf-8")
    raw = tmp_path / "raw"

    snapshot_local(src, "demo", raw)
    snapshot_local(src, "demo", raw)  # overwrite must not accumulate

    versions = list((raw / "demo").iterdir())
    assert versions == [snapshot_dir(raw, "demo")]  # exactly one 'current' dir


def test_checksum_matches_bytes(tmp_path):
    src = tmp_path / "src.csv"
    src.write_bytes(b"hello")
    raw = tmp_path / "raw"
    snapshot_local(src, "demo", raw)
    import hashlib

    meta = json.loads((snapshot_dir(raw, "demo") / "snapshot.json").read_text())
    assert meta["sha256"] == hashlib.sha256(b"hello").hexdigest()
