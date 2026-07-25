"""Load the NameExoWorlds planet <-> host bridge (164 rows, verified clean).

Produces pairs, not stars. 'planet designator' (e.g. 'Andromedae b') is the
future join key to NASA PSCompPars. Host name links back to the star table once
identity resolution runs.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

RENAME = {
    "exoID": "exo_id",
    "IAU-name (exoplanet)": "planet_name",
    "etymology": "planet_etymology",
    "planet designator": "planet_designator",  # join key to NASA later
    "theme": "theme",
    "iAU-name (host star)": "host_name",
    "wgsnCat": "wgsn_cat",
    "star name etymology": "host_etymology",
    "constellation": "constellation",
    "country": "country",
}


def load(raw_path: Path) -> pl.DataFrame:
    df = pl.read_csv(raw_path, infer_schema_length=0).rename(RENAME)
    df = df.with_columns(pl.col(pl.String).str.strip_chars())
    df = df.with_columns(
        is_valid=(
            (pl.col("planet_name") != "")
            & (pl.col("host_name") != "")
            & (pl.col("planet_designator") != "")
        ),
        source=pl.lit("exoplanet_names"),
    )
    return df
