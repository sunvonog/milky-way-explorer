"""NASA Exoplanet Archive TAP query definitions."""

from __future__ import annotations

from urllib.parse import urlencode

TAP_SYNC_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

PSCOMPPARS_COLUMNS = (
    # Identity
    "pl_name",
    "hostname",
    "pl_letter",
    "hd_name",
    "hip_name",
    "tic_id",
    "gaia_dr3_id",
    # Coordinates and system composition
    "ra",
    "dec",
    "sy_dist",
    "sy_snum",
    "sy_pnum",
    "cb_flag",
    # Stellar properties
    "st_teff",
    "st_mass",
    "st_rad",
    "st_lum",
    # Planet properties
    "pl_rade",
    "pl_bmasse",
    "pl_bmassprov",
    "pl_dens",
    "pl_eqt",
    "pl_insol",
    # Orbit
    "pl_orbper",
    "pl_orbsmax",
    "pl_orbeccen",
    "pl_orbincl",
    # Discovery and status
    "discoverymethod",
    "disc_year",
    "disc_facility",
    "pl_controv_flag",
)


def pscomppars_query() -> str:
    """Return the deterministic ADQL query used by this project."""
    columns = ",".join(PSCOMPPARS_COLUMNS)
    return f"SELECT {columns} FROM pscomppars ORDER BY pl_name"


def pscomppars_url() -> str:
    """Build the encoded synchronous TAP request URL."""
    parameters = urlencode(
        {
            "query": pscomppars_query(),
            "format": "csv",
        }
    )
    return f"{TAP_SYNC_URL}?{parameters}"
