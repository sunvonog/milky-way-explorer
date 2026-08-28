"""Load committed Gaia host batches into a validated staging frame."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from app.loaders.batches import load_csv_batches

SOURCE = "gaia_hosts"

RAW_SCHEMA = pl.Schema(
    {
        "source_id": pl.Int64,
        "designation": pl.String,
        "ref_epoch": pl.Float64,
        "ra": pl.Float64,
        "dec": pl.Float64,
        "l": pl.Float64,
        "b": pl.Float64,
        "parallax": pl.Float64,
        "parallax_error": pl.Float64,
        "parallax_over_error": pl.Float64,
        "pm": pl.Float64,
        "pmra": pl.Float64,
        "pmra_error": pl.Float64,
        "pmdec": pl.Float64,
        "pmdec_error": pl.Float64,
        "radial_velocity": pl.Float64,
        "radial_velocity_error": pl.Float64,
        "phot_g_mean_mag": pl.Float64,
        "phot_bp_mean_mag": pl.Float64,
        "phot_rp_mean_mag": pl.Float64,
        "bp_rp": pl.Float64,
        "ruwe": pl.Float64,
        "duplicated_source": pl.Boolean,
        "astrometric_params_solved": pl.Int8,
        "visibility_periods_used": pl.Int16,
        "phot_variable_flag": pl.String,
        "non_single_star": pl.Int16,
        "teff_gspphot": pl.Float64,
        "distance_gspphot": pl.Float64,
        "distance_gspphot_lower": pl.Float64,
        "distance_gspphot_upper": pl.Float64,
    }
)

RENAME = {
    "source_id": "gaia_source_id",
    "designation": "gaia_dr3_designation",
    "ref_epoch": "reference_epoch",
    "ra": "ra_deg",
    "dec": "dec_deg",
    "l": "galactic_longitude_deg",
    "b": "galactic_latitude_deg",
    "parallax": "parallax_mas",
    "parallax_error": "parallax_error_mas",
    "pm": "proper_motion_mas_per_year",
    "pmra": "proper_motion_ra_mas_per_year",
    "pmra_error": "proper_motion_ra_error_mas_per_year",
    "pmdec": "proper_motion_dec_mas_per_year",
    "pmdec_error": "proper_motion_dec_error_mas_per_year",
    "radial_velocity": "radial_velocity_km_per_s",
    "radial_velocity_error": "radial_velocity_error_km_per_s",
    "phot_g_mean_mag": "phot_g_mean_magnitude",
    "phot_bp_mean_mag": "phot_bp_mean_magnitude",
    "phot_rp_mean_mag": "phot_rp_mean_magnitude",
    "bp_rp": "bp_rp_color",
    "teff_gspphot": "temperature_gspphot_k",
    "distance_gspphot": "distance_gspphot_pc",
    "distance_gspphot_lower": "distance_gspphot_lower_pc",
    "distance_gspphot_upper": "distance_gspphot_upper_pc",
}


def normalize(frame: pl.DataFrame) -> pl.DataFrame:
    """Normalize Gaia names and flag invalid rows without dropping them."""
    frame = frame.with_columns(pl.col(pl.String).str.strip_chars()).rename(RENAME)

    expected_designation = pl.concat_str(
        [
            pl.lit("Gaia DR3 "),
            pl.col("gaia_source_id").cast(pl.String),
        ]
    )

    valid_identity = (
        pl.col("gaia_source_id").is_not_null()
        & (pl.col("gaia_dr3_designation") == expected_designation)
        & pl.col("gaia_source_id").is_unique()
    )

    valid_coordinates = pl.col("ra_deg").is_between(0.0, 360.0) & pl.col("dec_deg").is_between(
        -90.0, 90.0
    )

    return frame.with_columns(
        is_valid=(valid_identity & valid_coordinates).fill_null(False), source=pl.lit(SOURCE)
    ).sort("gaia_source_id")


def load(snapshot: Path) -> pl.DataFrame:
    """Read, combine and normalize every committed Gaia batch."""
    frame = load_csv_batches(
        snapshot, filename_pattern="gaia-host-*.csv", schema=RAW_SCHEMA, batch_label="Gaia"
    )
    return normalize(frame)
