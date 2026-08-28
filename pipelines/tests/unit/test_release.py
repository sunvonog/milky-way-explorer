from pathlib import Path

import pytest

from app.artifacts import (
    GAIA_DENSITY_VISUALIZATION_FILENAME,
)
from app.release import RELEASE_ARTIFACTS, resolve_release_artifacts


def _write_artifact(data_root: Path, relative_path: Path) -> Path:
    path = data_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(relative_path.as_posix(), encoding="utf-8")
    return path


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
