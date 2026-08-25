"""Pure transformations for the Gaia density background."""

from __future__ import annotations

import polars as pl

DENSITY_COLUMNS = (
    "grid_level",
    "cell_x",
    "cell_y",
    "source_count",
    "weighted_brightness",
    "mean_bp_rp",
)


def build_gaia_density_grid(
    sources: pl.DataFrame, *, grid_size: int, extent_kpc: float
) -> pl.DataFrame:
    """Aggregate Galactocentric sources into a fixed square grid.

    The grid covers ``[-extent_kpc, +extent_kpc)`` on both axes.
    ``weighted_brightness`` is a relative G-band flux proxy,
    ``10 ** (-0.4 * G)``, intended for rendering rather than photometry.
    """
    if grid_size <= 0:
        raise ValueError("grid_size must be positive")

    if extent_kpc <= 0:
        raise ValueError("extent_kpc must be positive")

    x = pl.col("galactocentric_x_kpc")
    y = pl.col("galactocentric_y_kpc")
    magnitude = pl.col("phot_g_mean_magnitude")
    colour = pl.col("bp_rp_color")

    cell_width_kpc = (2.0 * extent_kpc) / grid_size

    valid_position = (
        x.is_not_null()
        & y.is_not_null()
        & x.is_finite()
        & y.is_finite()
        & (x >= -extent_kpc)
        & (x < extent_kpc)
        & (y >= -extent_kpc)
        & (y < extent_kpc)
    )

    relative_brightness = (
        pl.when(magnitude.is_not_null() & magnitude.is_finite())
        .then(pl.lit(10.0).pow(-0.4 * magnitude))
        .otherwise(0.0)
        .alias("_relative_brightness")
    )

    valid_colour = (
        pl.when(colour.is_not_null() & colour.is_finite())
        .then(colour)
        .otherwise(None)
        .alias("_bp_rp")
    )

    return (
        sources.filter(valid_position)
        .with_columns(
            cell_x=((x + extent_kpc) / cell_width_kpc).floor().cast(pl.Int32),
            cell_y=((y + extent_kpc) / cell_width_kpc).floor().cast(pl.Int32),
            _relative_brightness=relative_brightness,
            _bp_rp=valid_colour,
        )
        .group_by("cell_x", "cell_y")
        .agg(
            source_count=pl.len().cast(pl.UInt32),
            weighted_brightness=(pl.col("_relative_brightness").sum().cast(pl.Float32)),
            mean_bp_rp=pl.col("_bp_rp").mean().cast(pl.Float32),
        )
        .with_columns(pl.lit(grid_size, dtype=pl.UInt16).alias("grid_level"))
        .select(*DENSITY_COLUMNS)
        .sort("cell_x", "cell_y")
    )
