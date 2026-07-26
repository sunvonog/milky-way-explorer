"""Load WGSN_Faints (named faint stars, many exoplanet hosts.

Real-data facts (verified against the 154-row snapshot):
    - RA2000 ranges 3.96..358.67 -> ALREADY DEGREES (no hours -> deg conversion!)
    - DE2000 ranges -80.20..79.37 -> already degrees
    - no rows missing Name/RA/DE
    - 'Bayer/other' holds host designations (e.g. WASP-32), NOT Bayer letters,
    so it must NOT be fed into Bayer normalisation; it's a cross identifier.
    - HIP is often written 'HIP 1547' (IAU-CSN stores bare digits); we normalise
      to bare digits at load so coalesce and alias prefixing stay consistent.
    - '_', '-', and '' mean "no value" and are nullified at load.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from app.loaders.base import null_placeholders, strip_catalogue_prefix

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

    # Strip 'HIP ' first so a lone 'HIP ' collapses to '' and then nulls.
    # Placeholders must be null before the Float64 cast.
    df = df.with_columns(hip=strip_catalogue_prefix("hip", "HIP"))
    df = null_placeholders(df).with_columns(
        [pl.col(c).cast(pl.Float64, strict=False) for c in _NUMERIC]
    )

    # flag rows whose coordinates fall outside valid ranges
    df = df.with_columns(
        is_valid=(
            pl.col("ra_deg").is_between(0, 360)
            & pl.col("dec_deg").is_between(-90, 90)
            & pl.col("name").is_not_null()
        ),
        source=pl.lit("wgsn_faints"),
    )
    return df
