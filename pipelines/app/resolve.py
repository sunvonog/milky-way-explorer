"""Resolve the three naming sources into canonical stars + aliases.

Verified counts against the current snapshot:
    606 canonical stars (0 duplicate name keys)
    154/154 WGSN_Faints matched (strict subset of IAU-CSN)
    151/152 exoplanets hosts matched; 'Mazalaai' unmatched -> review table
    605/606 stars carry HIP or HR for Stage 2 Gaia cross-match
"""

from __future__ import annotations

import polars as pl

from app.names import bayer_aliases, parse_bayer, search_key

# Display-name priority. Lower number wins.
PRIORITY = {
    "iau_proper_name": 1,
    "nasa_host_name": 2,
    "simbad_main": 3,
    "hd": 4,
    "hip": 5,
    "other_catalogue": 6,
    "gaia_dr3": 7,
}


def _key_col(col: str) -> pl.Expr:
    """search_key applied to a polars column via map_elements."""
    return pl.col(col).map_elements(search_key, return_dtype=pl.String)


def build_stars(csn: pl.DataFrame, faints: pl.DataFrame) -> pl.DataFrame:
    """Canonical star table: one row per IAU-named star, enriched from Faints."""
    stars = (
        csn.filter(pl.col("is_valid"))
        .with_columns(
            name_key=_key_col("proper_name"),
            star_id=pl.lit("iau:") + _key_col("proper_name"),
            canonical_display_name=pl.col("proper_name"),
            object_type=pl.lit("star"),
        )
        .select(
            "star_id",
            "name_key",
            "canonical_display_name",
            "object_type",
            "designation",
            "hip",
            "bayer_raw",
            "simbad_spelling",
            "constellation",
        )
    )

    enrich = faints.with_columns(name_key=_key_col("name")).select(
        "name_key",
        "ra_deg",
        "dec_deg",
        "vmag",
        "spectral_type",
        "hd",
        "hr",
        "other_id",
        "distance_ly",
        "bv_color",
        pl.col("hip").alias("hip_faints"),
    )

    stars = stars.join(enrich, on="name_key", how="left")

    # HIP is complementary between sources: take whichever is present.
    stars = stars.with_columns(hip=pl.coalesce([pl.col("hip"), pl.col("hip_faints")])).drop(
        "hip_faints"
    )

    # Gaia enrichment fills these, explicit nulls now, no fabricated values.
    return stars.with_columns(
        gaia_dr3_source_id=pl.lit(None, dtype=pl.Int64),
        distance_value=pl.lit(None, dtype=pl.Float64),
        distance_method=pl.lit("unavailable"),
    )


def build_aliases(stars: pl.DataFrame) -> pl.DataFrame:
    """Long-format alias table: many rows per star, each tagged with its source."""
    frames: list[pl.DataFrame] = []

    def add(
        expr: pl.Expr, catalogue: str, alias_type: str, source: str, official: bool = False
    ) -> None:
        frame = (
            stars.select("star_id", alias=expr)
            .filter(pl.col("alias").is_not_null() & (pl.col("alias") != ""))
            .with_columns(
                catalogue=pl.lit(catalogue),
                alias_type=pl.lit(alias_type),
                priority=pl.lit(PRIORITY[alias_type], dtype=pl.Int32),
                is_official=pl.lit(official),
                source=pl.lit(source),
            )
        )
        frames.append(frame)

    add(pl.col("canonical_display_name"), "IAU", "iau_proper_name", "iau_csn", True)
    add(pl.col("simbad_spelling"), "SIMBAD", "simbad_main", "iau_csn")
    add(pl.col("designation"), "HR", "other_catalogue", "iau_csn")
    add(pl.lit("HIP ") + pl.col("hip"), "HIP", "hip", "iau_csn")
    add(pl.lit("HD ") + pl.col("hd"), "HD", "hd", "wgsn_faints")
    add(pl.col("other_id"), "other", "other_catalogue", "wgsn_faints")

    aliases = pl.concat(frames, how="vertical")

    # Bayer forms: expand each parsed designation into its searchable variants.
    bayer_rows = []
    for row in stars.filter(pl.col("bayer_raw").is_not_null()).iter_rows(named=True):
        parts = parse_bayer(row["bayer_raw"])
        for form in bayer_aliases(parts):
            bayer_rows.append(
                {
                    "star_id": row["star_id"],
                    "alias": form,
                    "catalogue": "Bayer",
                    "alias_type": "other_catalogue",
                    "priority": PRIORITY["other_catalogue"],
                    "is_official": False,
                    "source": "iau_csn",
                }
            )
        # keep the raw form too, even when unparsed (variable stars, oddities)
        bayer_rows.append(
            {
                "star_id": row["star_id"],
                "alias": row["bayer_raw"],
                "catalogue": "Bayer" if parts.kind == "bayer" else parts.kind,
                "alias_type": "other_catalogue",
                "priority": PRIORITY["other_catalogue"],
                "is_official": False,
                "source": "iau_csn",
            }
        )

    if bayer_rows:
        bayer = pl.DataFrame(bayer_rows).with_columns(pl.col("priority").cast(pl.Int32))
        aliases = pl.concat([aliases, bayer], how="vertical")

    return (
        aliases.with_columns(alias_search_key=_key_col("alias"))
        .unique(subset=["star_id", "alias_search_key"])
        .sort("star_id", "priority")
    )


def link_exoplanet_hosts(
    stars: pl.DataFrame, bridge: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Attach host links. Returns (linked_pairs, unmatched_for_review)."""
    bridge = bridge.with_columns(host_key=_key_col("host_name"))
    keys = stars.select("star_id", "name_key")

    linked = bridge.join(keys, left_on="host_key", right_on="name_key", how="inner")
    unmatched = bridge.join(keys, left_on="host_key", right_on="name_key", how="anti").with_columns(
        review_reason=pl.lit("host name not found in canonical stars")
    )
    return linked, unmatched
