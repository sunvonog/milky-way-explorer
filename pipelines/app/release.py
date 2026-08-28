"""Definition and validation of deployable release artifacts."""

from __future__ import annotations

from pathlib import Path

from app.artifacts import (
    ALIASES_FILENAME,
    GAIA_DENSITY_VISUALIZATION_FILENAME,
    HOST_VISUALIZATION_FILENAME,
    STARS_FILENAME,
)

RELEASE_ARTIFACTS = (
    Path("processed") / STARS_FILENAME,
    Path("processed") / ALIASES_FILENAME,
    Path("frontend") / HOST_VISUALIZATION_FILENAME,
    Path("frontend") / GAIA_DENSITY_VISUALIZATION_FILENAME,
)


def resolve_release_artifacts(data_root: Path) -> dict[Path, Path]:
    """Resolve the fixed deployment allowlist and reject incomplete releases."""
    resolved = {relative_path: data_root / relative_path for relative_path in RELEASE_ARTIFACTS}

    missing = [
        relative_path
        for relative_path, source_path in resolved.items()
        if not source_path.is_file()
    ]

    if missing:
        missing_names = ", ".join(path.as_posix() for path in missing)
        raise FileNotFoundError(f"missing release artifacts: {missing_names}")

    return resolved
