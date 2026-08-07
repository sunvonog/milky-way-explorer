"""Maintainer refresh: update the current snapshot for each naming source.

Run occasionally, NOT per build. After running::

    git diff --stat data/raw/       # review what upstream changed
    git add data/raw/ && git commit # vendor the new version

Contributors and CI never run this — they build from committed snapshots.
"""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.runtime.flow import flow, get_run, get_task, task
from app.runtime.logging import bound_log
from app.sources.snapshot import snapshot_local

NAMING_SOURCES: dict[str, str] = {
    "iau_csn": "IAU-Catalog-of-Star-Names.csv",
    "wgsn_faints": "WGSN-Faints.csv",
    "exoplanet_names": "Exoplanet-Name-Catalog.csv",
}

NAMING_ORIGIN = "https://exopla.net"


def _ctx_log(**fields: object):
    run = get_run()
    return bound_log(
        run_id=run.run_id if run else "-",
        flow=run.flow_name if run else "refresh-snapshots",
        task=get_task() or "-",
        **fields,
    )


@task(name="snapshot_from_local", key="source")
def snapshot_from_local(source: str, filename: str) -> Path:
    settings = get_settings()
    source_file = settings.inputs_dir / filename
    path = snapshot_local(source_file, source, settings.raw_root, origin=NAMING_ORIGIN)
    _ctx_log(
        source=source,
        path=str(path),
        input=str(source_file),
    ).info("snapshotted from local input")
    return path


@flow(name="refresh-snapshots")
def refresh_snapshots() -> None:
    """Overwrite data/raw/<source>/current/ from URL or _inputs/ exports."""
    settings = get_settings()
    _ctx_log(
        data_root=str(settings.data_root),
        raw_root=str(settings.raw_root),
        inputs_dir=str(settings.inputs_dir),
    ).info("refresh starting")

    if not settings.inputs_dir.is_dir() and NAMING_SOURCES:
        raise SystemExit(
            f"missing input directory: {settings.inputs_dir}\n"
            "Create it and place the downloaded CSVs there."
        )

    for source, filename in NAMING_SOURCES.items():
        snapshot_from_local(source, filename)

    _ctx_log().info("refresh complete; review git diff --stat data/raw/, then commit")
