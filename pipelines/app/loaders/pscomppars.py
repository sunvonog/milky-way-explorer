"""Load NASA PSCompPars CSV snapshots into validated staging frame."""

from __future__ import annotations

from pathlib import Path

import polars as pl
from polars._typing import SchemaDict

SOURCE = "nasa_pscomppars"
_GAIA_DR3_PATTERN = r"^Gaia DR3 ([0-9]+)$"

RAW_SCHEMA: SchemaDict = {
    "pl_name": pl.String,
    "hostname": pl.String,
    "pl_letter": pl.String,
    "hd_name": pl.String,
    "hip_name": pl.String,
    "tic_id": pl.String,
    "gaia_dr3_id": pl.String,
    "ra": pl.Float64,
    "dec": pl.Float64,
    "sy_dist": pl.Float64,
    "sy_snum": pl.Int16,
    "sy_pnum": pl.Int16,
    "cb_flag": pl.Int8,
    "st_teff": pl.Float64,
    "st_mass": pl.Float64,
    "st_rad": pl.Float64,
    "st_lum": pl.Float64,
    "pl_rade": pl.Float64,
    "pl_bmasse": pl.Float64,
    "pl_bmassprov": pl.String,
    "pl_dens": pl.Float64,
    "pl_eqt": pl.Float64,
    "pl_insol": pl.Float64,
    "pl_orbper": pl.Float64,
    "pl_orbsmax": pl.Float64,
    "pl_orbeccen": pl.Float64,
    "pl_orbincl": pl.Float64,
    "discoverymethod": pl.String,
    "disc_year": pl.Int16,
    "disc_facility": pl.String,
    "pl_controv_flag": pl.Int8,
}

RENAME = {
    "pl_name": "planet_name",
    "hostname": "host_name",
    "pl_letter": "planet_letter",
    "gaia_dr3_id": "gaia_dr3_designation",
    "ra": "ra_deg",
    "dec": "dec_deg",
    "sy_dist": "system_distance_pc",
    "sy_snum": "star_count",
    "sy_pnum": "planet_count",
    "cb_flag": "is_circumbinary",
    "st_teff": "stellar_temperature_k",
    "st_mass": "stellar_mass_solar",
    "st_rad": "stellar_radius_solar",
    "st_lum": "stellar_luminosity_log_solar",
    "pl_rade": "radius_earth",
    "pl_bmasse": "mass_earth",
    "pl_bmassprov": "mass_provenance",
    "pl_dens": "density_g_cm3",
    "pl_eqt": "equilibrium_temperature_k",
    "pl_insol": "insolation_earth",
    "pl_orbper": "orbital_period_days",
    "pl_orbsmax": "semi_major_axis_au",
    "pl_orbeccen": "eccentricity",
    "pl_orbincl": "inclination_deg",
    "discoverymethod": "discovery_method",
    "disc_year": "discovery_year",
    "disc_facility": "discovery_facility",
    "pl_controv_flag": "is_controversial",
}


def normalize(frame: pl.DataFrame) -> pl.DataFrame:
    """Normalize types and names without dropping source rows."""
    frame = frame.with_columns(pl.col(pl.String).str.strip_chars()).rename(RENAME)

    frame = frame.with_columns(
        gaia_source_id=(
            pl.col("gaia_dr3_designation")
            .str.extract(_GAIA_DR3_PATTERN, group_index=1)
            .cast(pl.Int64, strict=False)
        ),
        is_circumbinary=pl.col("is_circumbinary").cast(pl.Boolean),
        is_controversial=pl.col("is_controversial").cast(pl.Boolean),
    )

    valid_identity = (
        pl.col("planet_name").is_not_null()
        & pl.col("host_name").is_not_null()
        & (pl.col("planet_name").str.len_chars() > 0)
        & (pl.col("host_name").str.len_chars() > 0)
    )

    valid_coordinates = pl.col("ra_deg").is_between(0, 360) & pl.col("dec_deg").is_between(-90, 90)

    valid_system = (pl.col("star_count") >= 1) & (pl.col("planet_count") >= 1)

    valid_gaia_id = (
        pl.col("gaia_dr3_designation").is_null() | pl.col("gaia_source_id").is_not_null()
    )

    return frame.with_columns(
        is_valid=(valid_identity & valid_coordinates & valid_system & valid_gaia_id).fill_null(
            False
        ),
        source=pl.lit(SOURCE),
    )


def load(raw_path: Path) -> pl.DataFrame:
    """Read and normalize a committed PSCompPars CSV snapshot."""
    frame = pl.read_csv(raw_path, schema=RAW_SCHEMA, null_values="")
    return normalize(frame)
