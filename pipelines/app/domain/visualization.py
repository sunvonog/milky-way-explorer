"""Pure transformation for frontend visualization records."""

from __future__ import annotations

import polars as pl

HOST_VISUALIZATION_COLUMNS = (
    "host_id",
    "host_name",
    "gaia_source_id",
    "planet_count",
    "archive_planet_count",
    "planet_count_matches_archive",
    "is_circumbinary",
    "position_status",
    "distance_pc",
    "distance_method",
    "distance_quality",
    "heliocentric_x_pc",
    "heliocentric_y_pc",
    "heliocentric_z_pc",
    "galactocentric_x_kpc",
    "galactocentric_y_kpc",
    "galactocentric_z_kpc",
    "phot_g_mean_magnitude",
    "bp_rp_color",
)


def build_host_visualization_records(
    hosts: pl.DataFrame, systems: pl.DataFrame, gaia_sources: pl.DataFrame
) -> pl.DataFrame:
    """Combine host identity system counts, and Gaia spatial data."""
    host_fields = hosts.select(
        "host_id",
        "host_name",
        "gaia_source_id",
        "is_circumbinary",
    )

    system_fields = systems.select(
        "host_id", "planet_count", "archive_planet_count", "planet_count_matches_archive"
    )

    gaia_fields = gaia_sources.select(
        "gaia_source_id",
        "distance_pc",
        "distance_method",
        "distance_quality",
        "heliocentric_x_pc",
        "heliocentric_y_pc",
        "heliocentric_z_pc",
        "galactocentric_x_kpc",
        "galactocentric_y_kpc",
        "galactocentric_z_kpc",
        "phot_g_mean_magnitude",
        "bp_rp_color",
    )

    return (
        host_fields.join(system_fields, on="host_id", how="left", validate="1:1")
        .join(gaia_fields, on="gaia_source_id", how="left", validate="m:1", coalesce=True)
        .with_columns(
            position_status=(
                pl.when(pl.col("gaia_source_id").is_null())
                .then(pl.lit("no_exact_gaia_source"))
                .when(pl.col("distance_pc").is_null())
                .then(pl.lit("no_accepted_distance"))
                .otherwise(pl.lit("available"))
            )
        )
        .select(*HOST_VISUALIZATION_COLUMNS)
        .sort("host_id")
    )
