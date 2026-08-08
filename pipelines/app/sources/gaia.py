"""Gaia Archive query definitions."""

from __future__ import annotations

from app.gaia import GaiaHostBatch

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
