"""Pure transformations supporting Gaia host enrichment."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

GAIA_HOST_SOURCE_COLUMNS = (
    "gaia_source_id",
    "gaia_dr3_designation",
    "reference_epoch",
    "ra_deg",
    "dec_deg",
    "galactic_longitude_deg",
    "galactic_latitude_deg",
    "parallax_mas",
    "parallax_error_mas",
    "parallax_over_error",
    "proper_motion_mas_per_year",
    "proper_motion_ra_mas_per_year",
    "proper_motion_ra_error_mas_per_year",
    "proper_motion_dec_mas_per_year",
    "proper_motion_dec_error_mas_per_year",
    "radial_velocity_km_per_s",
    "radial_velocity_error_km_per_s",
    "phot_g_mean_magnitude",
    "phot_bp_mean_magnitude",
    "phot_rp_mean_magnitude",
    "bp_rp_color",
    "ruwe",
    "duplicated_source",
    "astrometric_params_solved",
    "visibility_periods_used",
    "phot_variable_flag",
    "non_single_star",
    "temperature_gspphot_k",
    "distance_gspphot_pc",
    "distance_gspphot_lower_pc",
    "distance_gspphot_upper_pc",
    "distance_pc",
    "distance_lower_pc",
    "distance_upper_pc",
    "distance_method",
    "distance_quality",
    "source",
)


@dataclass(frozen=True, slots=True)
class GaiaHostBatch:
    """One deterministic unit of exact Gaia source retrieval."""

    batch_number: int
    source_ids: tuple[int, ...]


def build_gaia_host_ids(hosts: pl.DataFrame) -> pl.DataFrame:
    """Build the distinct Gaia source-ID manifest for exoplanet hosts."""
    return (
        hosts.select(pl.col("gaia_source_id").cast(pl.Int64))
        .drop_nulls()
        .unique()
        .sort("gaia_source_id")
    )


def plan_gaia_host_batches(host_ids: pl.DataFrame, *, batch_size: int) -> list[GaiaHostBatch]:
    """Split canonical Gaia host IDs into stable, bounded batches."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    source_ids: list[int] = build_gaia_host_ids(host_ids).get_column("gaia_source_id").to_list()

    return [
        GaiaHostBatch(
            batch_number=batch_number, source_ids=tuple(source_ids[start : start + batch_size])
        )
        for batch_number, start in enumerate(
            range(0, len(source_ids), batch_size),
            start=1,
        )
    ]


def add_gaia_distance(frame: pl.DataFrame) -> pl.DataFrame:
    """Select a distance with explicit method and quality provenance."""
    has_gspphot = (
        pl.col("distance_gspphot_pc").is_not_null() & (pl.col("distance_gspphot_pc") > 0)
    ).fill_null(False)

    has_qualified_parallax = (
        (pl.col("parallax_mas") > 0)
        & (pl.col("parallax_over_error") >= 5)
        & (pl.col("ruwe").is_null() | (pl.col("ruwe") < 1.4))
    ).fill_null(False)

    has_parallax_bounds = (
        has_qualified_parallax
        & (pl.col("parallax_error_mas") > 0)
        & (pl.col("parallax_mas") - pl.col("parallax_error_mas") > 0)
    ).fill_null(False)

    return frame.with_columns(
        distance_pc=(
            pl.when(has_gspphot)
            .then(pl.col("distance_gspphot_pc"))
            .when(has_qualified_parallax)
            .then(1000.0 / pl.col("parallax_mas"))
            .otherwise(None)
        ),
        distance_lower_pc=(
            pl.when(has_gspphot)
            .then(pl.col("distance_gspphot_lower_pc"))
            .when(has_parallax_bounds)
            .then(1000.0 / (pl.col("parallax_mas") + pl.col("parallax_error_mas")))
            .otherwise(None)
        ),
        distance_upper_pc=(
            pl.when(has_gspphot)
            .then(pl.col("distance_gspphot_upper_pc"))
            .when(has_parallax_bounds)
            .then(1000.0 / (pl.col("parallax_mas") - pl.col("parallax_error_mas")))
            .otherwise(None)
        ),
        distance_method=(
            pl.when(has_gspphot)
            .then(pl.lit("gaia_gspphot"))
            .when(has_qualified_parallax)
            .then(pl.lit("inverse_parallax"))
            .otherwise(pl.lit("unavailable"))
        ),
        distance_quality=(
            pl.when(has_gspphot)
            .then(pl.lit("positive_gspphot_estimate"))
            .when(has_qualified_parallax)
            .then(pl.lit("snr_ge_5_ruwe_acceptable"))
            .otherwise(pl.lit("unavailable"))
        ),
    )


def build_gaia_host_sources(staging: pl.DataFrame) -> pl.DataFrame:
    """Build one published Gaia source record per valid host source ID."""
    return (
        staging.filter(pl.col("is_valid"))
        .pipe(add_gaia_distance)
        .select(*GAIA_HOST_SOURCE_COLUMNS)
        .sort("gaia_source_id")
    )
