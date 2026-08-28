"""Definition, validation, and atomic publication of deployable releases."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

import polars as pl
from pydantic import BaseModel

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

RELEASE_SNAPSHOT_SOURCES = (
    "exoplanet_names",
    "gaia_background",
    "gaia_hosts",
    "iau_csn",
    "nasa_pscomppars",
    "wgsn_faints",
)

_BUILD_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ReleaseArtifactMetadata(BaseModel):
    """Integrity and table-size metadata for one published artifact."""

    sha256: str
    bytes: int
    rows: int


class ReleaseManifest(BaseModel):
    """Versioned contract written by the pipeline and consumed by the backend."""

    schema_version: Literal[1] = 1
    build_id: str
    created_at: datetime
    source_snapshots: dict[str, str]
    row_counts: dict[str, int]
    artifacts: dict[str, ReleaseArtifactMetadata]


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


def _validate_build_id(build_id: str) -> None:
    if not _BUILD_ID_PATTERN.fullmatch(build_id):
        raise ValueError(
            "build_id must contain only letters, numbers, dots, underscores, and hyphens"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def _row_count(path: Path) -> int:
    if path.suffix == ".parquet":
        return int(pl.scan_parquet(path).select(pl.len()).collect().item())

    if path.suffix == ".arrow":
        return pl.read_ipc(path).height

    raise ValueError(f"unsupported release artifact: {path}")


def _read_source_snapshots(data_root: Path) -> dict[str, str]:
    snapshots: dict[str, str] = {}

    for source in RELEASE_SNAPSHOT_SOURCES:
        path = data_root / "raw" / source / "current" / "snapshot.json"

        if not path.is_file():
            raise FileNotFoundError(f"missing release source manifest: {path}")

        metadata = json.loads(path.read_text(encoding="utf-8"))

        if metadata.get("source") != source:
            raise ValueError(
                f"source manifest identifies {metadata.get('source')!r}, "
                f"expected {source!r}: {path}"
            )

        checksum = metadata.get("sha256")

        if not isinstance(checksum, str) or not checksum:
            raise ValueError(f"source manifest has no sha256: {path}")

        snapshots[source] = checksum

    return snapshots


def publish_release(
    data_root: Path,
    *,
    build_id: str,
    created_at: datetime,
) -> ReleaseManifest:
    """Stage an immutable build and atomically switch the current pointer.

    Artifact copying and manifest construction happen in a temporary sibling
    directory. The completed directory is renamed into place before
    ``current.json`` is atomically replaced, so readers never observe a pointer
    to a partial build.
    """
    _validate_build_id(build_id)

    artifacts = resolve_release_artifacts(data_root)
    source_snapshots = _read_source_snapshots(data_root)

    builds_root = data_root / "builds"
    builds_root.mkdir(parents=True, exist_ok=True)

    destination = builds_root / build_id

    if destination.exists():
        raise FileExistsError(f"release already exists: {destination}")

    staging = Path(
        tempfile.mkdtemp(
            dir=builds_root,
            prefix=f".{build_id}.staging-",
        )
    )
    pointer_tmp = builds_root / f".current-{uuid.uuid4().hex}.json"
    promoted = False
    pointer_switched = False

    try:
        for relative_path, source_path in artifacts.items():
            target = staging / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)

        artifact_metadata: dict[str, ReleaseArtifactMetadata] = {}
        row_counts: dict[str, int] = {}

        for relative_path in RELEASE_ARTIFACTS:
            path = staging / relative_path
            key = relative_path.as_posix()
            rows = _row_count(path)

            artifact_metadata[key] = ReleaseArtifactMetadata(
                sha256=_sha256(path), bytes=path.stat().st_size, rows=rows
            )
            row_counts[key] = rows

        manifest = ReleaseManifest(
            build_id=build_id,
            created_at=created_at,
            source_snapshots=source_snapshots,
            row_counts=row_counts,
            artifacts=artifact_metadata,
        )
        manifest_json = manifest.model_dump_json(indent=2) + "\n"

        (staging / "manifest.json").write_text(manifest_json, encoding="utf-8")

        staging.replace(destination)
        promoted = True

        pointer_tmp.write_text(manifest_json, encoding="utf-8")
        pointer_tmp.replace(builds_root / "current.json")
        pointer_switched = True

        return manifest

    except BaseException:
        if pointer_tmp.exists():
            pointer_tmp.unlink()

        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

        if promoted and not pointer_switched and destination.exists():
            shutil.rmtree(destination, ignore_errors=True)

        raise
