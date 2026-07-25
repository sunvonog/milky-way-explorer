"""Load the exopla IAU-CSN names file into clean staging frame.

Real-data facts (verified against the 606-row snapshot):
    - headers are wrapped in <span> tags
    - exactly one malformed row: 'Unurgunite' (missing Designation/Constellation/Language)
    - Bayer ID mixes Greek symbols, Latin abbreviations, superscripts -> kept raw here
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from app.loaders.base import clean_headers

RENAME = {
    "proper names": "proper_name",
    "NEC+": "nec_plus",
    "Designation": "designation",
    "HIP": "hip",
    "Bayer ID": "bayer_raw",
    "Simbad spelling": "simbad_spelling",
    "Constellation": "constellation",
    "Origin": "origin",
    "Language": "language",
    "Reference": "reference",
    "Date of Adoption": "adoption_date",
}


def load(raw_path: Path) -> pl.DataFrame:
    df = clean_headers(pl.read_csv(raw_path, infer_schema_length=0)).rename(RENAME)

    # strip whitespace on every string cell (exopla export has stray spaces)
    df = df.with_columns(pl.col(pl.String).str.strip_chars())

    # flag malformed rows; DO NOT drop.
    df = df.with_columns(
        is_valid=(
            (pl.col("proper_name") != "")
            & pl.col("proper_name").is_not_null()
            & (pl.col("constellation") != "")
            & pl.col("constellation").is_not_null()
        ),
        source=pl.lit("iau_csn"),
    )
    return df
