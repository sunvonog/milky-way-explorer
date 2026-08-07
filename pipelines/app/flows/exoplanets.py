"""NASA exoplanet catalogue workflows."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.runtime.flow import flow, get_run, get_task, task
from app.runtime.logging import bound_log
from app.sources.nasa_exoplanet_archive import pscomppars_url
from app.sources.snapshot import snapshot_url

SOURCE = "nasa_pscomppars"
SNAPSHOT_FILENAME = "pscomppars.csv"


def _ctx_log(**fields: object):
    run = get_run()
    return bound_log(
        run_id=run.run_id if run else "-",
        flow=run.flow_name if run else "refresh-pscomppars",
        task=get_task() or "-",
        **fields,
    )


@task(name="snapshot_nasa_pscomppars")
def snapshot_nasa_pscomppars() -> Path:
    """Download the selected PSCompPars columns into a new snapshot."""
    settings = get_settings()

    path = snapshot_url(
        pscomppars_url(), SOURCE, settings.raw_root, filename=SNAPSHOT_FILENAME, timeout=120.0
    )

    _ctx_log(
        source=SOURCE,
        path=str(path),
        bytes=path.stat().st_size,
    ).info("snapshotted NASA PSCompPars")

    return path


@flow(name="refresh-pscomppars")
def refresh_pscomppars() -> None:
    """Maintainer-only refresh of the NASA exoplanet catalogue."""
    snapshot_nasa_pscomppars()
