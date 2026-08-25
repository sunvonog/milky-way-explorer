"""Gaia Archive query definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from app.domain.gaia import GaiaHostBatch

GAIA_SOURCE_TABLE = "gaiadr3.gaia_source"

GAIA_HOST_COLUMNS = (
    # Identity and reference epoch
    "source_id",
    "designation",
    "ref_epoch",
    # Coordinates
    "ra",
    "dec",
    "l",
    "b",
    # Distance inputs
    "parallax",
    "parallax_error",
    "parallax_over_error",
    # Proper motion and radial velocity
    "pm",
    "pmra",
    "pmra_error",
    "pmdec",
    "pmdec_error",
    "radial_velocity",
    "radial_velocity_error",
    # Photometry
    "phot_g_mean_mag",
    "phot_bp_mean_mag",
    "phot_rp_mean_mag",
    "bp_rp",
    # Quality and classification
    "ruwe",
    "duplicated_source",
    "astrometric_params_solved",
    "visibility_periods_used",
    "phot_variable_flag",
    "non_single_star",
    # GSP-Phot estimates
    "teff_gspphot",
    "distance_gspphot",
    "distance_gspphot_lower",
    "distance_gspphot_upper",
)

GAIA_BACKGROUND_COLUMNS = (
    "source_id",
    "ra",
    "dec",
    "l",
    "b",
    "parallax",
    "parallax_over_error",
    "phot_g_mean_mag",
    "bp_rp",
    "ruwe",
    "distance_gspphot",
)


class GaiaArchiveJob(Protocol):
    jobid: str

    def get_phase(self) -> str: ...


class GaiaArchiveClient(Protocol):
    def launch_job_async(
        self,
        query: str,
        *,
        output_file: str,
        output_format: str,
        dump_to_file: bool,
        background: bool,
        verbose: bool,
    ) -> GaiaArchiveJob: ...


@dataclass(frozen=True, slots=True)
class GaiaBatchDownload:
    batch_number: int
    job_id: str
    path: Path


def gaia_host_query(batch: GaiaHostBatch) -> str:
    """Build an ADQL query for one exact Gaia host batch."""
    if not batch.source_ids:
        raise ValueError("Gaia host batch must not be empty")

    columns = ",".join(GAIA_HOST_COLUMNS)
    source_ids = ",".join(str(source_id) for source_id in batch.source_ids)

    return (
        f"SELECT {columns} "
        f"FROM {GAIA_SOURCE_TABLE} "
        f"WHERE source_id IN ({source_ids}) "
        "ORDER BY source_id"
    )


def _default_client() -> GaiaArchiveClient:
    from astroquery.gaia import Gaia

    return cast(GaiaArchiveClient, Gaia)


def download_gaia_host_batch(
    batch: GaiaHostBatch,
    destination: Path,
    *,
    client: GaiaArchiveClient | None = None,
) -> GaiaBatchDownload:
    """Download one exact Gaia host batch using an asynchronous TAP job."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.part")
    error_output = Path(f"{partial}.error")
    partial.unlink(missing_ok=True)
    error_output.unlink(missing_ok=True)

    archive = client or _default_client()

    try:
        job = archive.launch_job_async(
            gaia_host_query(batch),
            output_file=str(partial),
            output_format="csv",
            dump_to_file=True,
            background=False,
            verbose=True,
        )

        phase = job.get_phase()
        if phase != "COMPLETED":
            raise RuntimeError(
                f"Gaia batch {batch.batch_number} job {job.jobid} ended in phase {phase}"
            )

        if not partial.is_file() or partial.stat().st_size == 0:
            raise RuntimeError(
                f"Gaia batch {batch.batch_number} job {job.jobid} did not produce an output file"
            )

        partial.replace(destination)
    except BaseException as exc:
        if error_output.is_file():
            try:
                response = error_output.read_text(encoding="utf-8", errors="replace")
            except OSError:
                response = ""

            response_excerpt = " ".join(response.split())[:2000]

            if response_excerpt:
                exc.add_note(f"Gaia TAP response: {response_excerpt}")
        partial.unlink(missing_ok=True)
        error_output.unlink(missing_ok=True)
        raise

    return GaiaBatchDownload(
        batch_number=batch.batch_number, job_id=str(job.jobid), path=destination
    )
