"""Load WGSN_Faints (named faint stars, many exoplanet hosts.

Real-data facts (verified against the 154-row snapshot):
    - RA2000 ranges 3.96..358.67 -> ALREADY DEGREES (no hours -> deg conversion!)
    - DE2000 ranges -80.20..79.37 -> already degrees
    - no rows missing Name/RA/DE
    - 'Bayer/other' holds host designations (e.g. WASP-32), NOT Bayer letters,
    so it must NOT be fed into Bayer normalisation; it's a cross identifier.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

RENAME = {
    "WGSN-ID": "wgsn_id",
    "Name": "name",
    "HIP": "hip",
    "RA2000": "ra_deg",  # already degrees
    "DE2000": "dec_deg",  # already degrees
    "Vmag": "vmag",
    "type": "spectral_type",
    "HR": "hr",
    "HD": "hd",
    "Bayer/other": "other_id",  # cross-ID, not a Bayer letter
    "constellation": "constellation",
    "distance from Sun/ ly": "distance_ly",
    "B-V color": "bv_color",
    "VmagMax": "vmag_max",
    "VmagMin": "vmag_min",
}

_NUMERIC = ["ra_deg", "dec_deg", "vmag", "distance_ly", "bv_color", "vmag_max", "vmag_min"]


def load(raw_path: Path) -> pl.DataFrame:
    df = pl.read_csv(raw_path, infer_schema_length=0).rename(RENAME)
    df = df.with_columns(pl.col(pl.String).str.strip_chars())

    # empty strings -> null, then cast numerics (Float64 keeps null intact)
    df = df.with_columns(
        [pl.when(pl.col(c) == "").then(None).otherwise(pl.col(c)).alias(c) for c in df.columns]
    ).with_columns([pl.col(c).cast(pl.Float64, strict=False) for c in _NUMERIC])

    # flag rows whose coordinates fall outside valid ranges
    df = df.with_columns(
        is_valid=(
            pl.col("ra_deg").is_between(0, 360)
            & pl.col("dec_deg").is_between(-90, 90)
            & pl.col("name").is_not_null()
            & (pl.col("name") != "")
        ),
        source=pl.lit("wgsn_faints"),
    )
    return df
