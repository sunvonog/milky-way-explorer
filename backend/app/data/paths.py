"""Resolution and validation of build data file paths."""

from __future__ import annotations

from pathlib import Path

STARS_FILE = "stars.parquet"
ALIAS_FILE = "alias.parquet"
HOST_LINKS_FILE = "exoplanet_host_links.parquet"


class BuildNotPublishedError(FileNotFoundError):
    "Raised when required build files are absent. Callers translate to 503."


def require(processed_root: Path, *filenames: str) -> dict[str, Path]:
    """Resolve and validate the named files, keyed by filename."""
    resolved: dict[str, Path] = {}
    for name in filenames:
        path = (processed_root / name).resolve()
        if not path.is_file():
            raise BuildNotPublishedError(f"missing build file: {path}")
        resolved[name] = path
    return resolved
