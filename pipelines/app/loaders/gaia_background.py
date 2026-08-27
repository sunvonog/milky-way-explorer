"""Load committed Gaia background batches into a validated staging frame."""

from __future__ import annotations

from pathlib import Path

import polars as pl

SOURCE = "gaia_background"

RAW_SCHEMA = pl.Schema(
    {
        "source_id": pl.Int64,
        "ra": pl.Float64,
        "dec": pl.Float64,
        "l": pl.Float64,
        "b": pl.Float64,
        "parallax": pl.Float64,
        "parallax_over_error": pl.Float64,
        "phot_g_mean_mag": pl.Float64,
        "bp_rp": pl.Float64,
        "ruwe": pl.Float64,
        "distance_gspphot": pl.Float64,
    }
)

RENAME = {
    "source_id": "gaia_source_id",
    "ra": "ra_deg",
    "dec": "dec_deg",
    "l": "galactic_longitude_deg",
    "b": "galactic_latitude_deg",
    "parallax": "parallax_mas",
    "phot_g_mean_mag": "phot_g_mean_magnitude",
    "bp_rp": "bp_rp_color",
    "distance_gspphot": "distance_gspphot_pc",
}


def normalize(frame: pl.DataFrame) -> pl.DataFrame:
    """Normalize Gaia background columns and flag invalid rows."""
    frame = frame.rename(RENAME)

    valid_identity = pl.col("gaia_source_id").is_not_null() & pl.col("gaia_source_id").is_unique()

    valid_coordinates = (
        (pl.col("ra_deg") >= 0.0)
        & (pl.col("ra_deg") < 360.0)
        & pl.col("dec_deg").is_between(-90.0, 90)
        & (pl.col("galactic_longitude_deg") >= 0.0)
        & (pl.col("galactic_longitude_deg") < 360.0)
        & pl.col("galactic_latitude_deg").is_between(-90.0, 90.0)
    )

    return frame.with_columns(
        is_valid=(valid_identity & valid_coordinates).fill_null(False), source=pl.lit(SOURCE)
    ).sort("gaia_source_id")


def load(snapshot: Path) -> pl.DataFrame:
    """Read and normalize every committed Gaia background batch."""
    batches_root = snapshot / "batches"
    batch_paths = sorted(
        path for path in batches_root.glob("gaia-background-*.csv") if path.is_file()
    )

    if not batch_paths:
        raise FileNotFoundError(f"no Gaia background batch files found in: {batches_root}")

    frames = [pl.read_csv(path, schema=RAW_SCHEMA, null_values="") for path in batch_paths]

    return normalize(pl.concat(frames, how="vertical"))
